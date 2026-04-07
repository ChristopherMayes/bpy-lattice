"""
USD (Universal Scene Description) export for bpy_lattice.

Generates .usd/.usda/.usdc files from Lattice data that can be imported
into Blender, NVIDIA Omniverse, or any USD-compatible application.

Key design: Prototype geometry is defined once under ``/Root/Prototypes``
(as Xform prims containing child meshes) and shared by element instances
under ``/Root/Elements`` via USD internal references.

When a *catalogue* directory is supplied, ``.blend`` CAD model files are
converted to ``.usd`` via Blender in headless mode, stored in a
``models/`` directory alongside the output file, and referenced from the
prototypes.  Elements whose ``.blend`` file cannot be found or converted
fall back to procedural geometry.

Usage
-----
::

    from bpy_lattice import Lattice
    lattice = Lattice.from_json("lat.json")

    # Procedural geometry only
    lattice.to_usd("lattice.usda")

    # With CAD models from a catalogue
    lattice.to_usd("lattice.usda", catalogue="/path/to/Catalogue")

"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

from .colors import resolve_color
from .elements import (
    BaseElement,
    BeamElement,
    BeginningEle,
    Bend,
    Fiducial,
    Pipe,
)

if TYPE_CHECKING:
    from .envelopes import Envelope
    from .tracks import Track


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sanitize_usd_name(name: str) -> str:
    """Convert an arbitrary string to a valid USD prim name."""
    result = name.replace(" ", "_").replace("-", "_").replace(".", "_")
    if result and result[0].isdigit():
        result = "_" + result
    result = "".join(c if c.isalnum() or c == "_" else "_" for c in result)
    return result or "_unnamed"


def _get_element_color(ele: BaseElement) -> tuple[float, float, float, float]:
    """Resolve the RGBA colour tuple for an element (class-level ``color``)."""
    color_name = getattr(ele, "color", None)
    if color_name is not None:
        try:
            return resolve_color(color_name)
        except (ValueError, TypeError):
            pass
    return (0.5, 0.5, 0.5, 1.0)


def _color_key(ele: BaseElement) -> str:
    """Return the colour name used for material deduplication."""
    return getattr(ele, "color", "grey")


def _proto_key(ele: BaseElement) -> str:
    """
    Return a hashable key that uniquely identifies the *geometry* of an
    element so that elements sharing the same shape can share a single
    prototype.

    Elements that have a ``cad_model`` are grouped by their model path.
    """
    if ele.cad_model:
        return f"cad__{_sanitize_usd_name(ele.cad_model)}"

    cls = ele.__class__.__name__

    if isinstance(ele, (BeginningEle, Fiducial)):
        return cls

    if not isinstance(ele, BeamElement):
        return cls

    if isinstance(ele, Bend):
        return (
            f"{cls}_L{ele.length:.4f}_W{ele.width:.4f}"
            f"_H{ele.height:.4f}_G{ele.gap:.4f}"
        )

    if isinstance(ele, Pipe):
        ap = ele.aperture
        return f"{cls}_L{ele.length:.4f}" f"_A{ap.x1_limit:.4f}_B{ap.y1_limit:.4f}"

    # General BeamElement – key on outer dimensions
    return f"{cls}_L{ele.length:.4f}_W{ele.width:.4f}_H{ele.height:.4f}"


# ---------------------------------------------------------------------------
# Mesh generators (pure USD, no Blender dependency)
# ---------------------------------------------------------------------------


def _make_box_mesh(
    stage: Usd.Stage,
    path: str,
    length: float,
    width: float,
    height: float,
) -> UsdGeom.Mesh:
    """
    Create a box mesh centred at the origin.

    The box is oriented so that *length* runs along the **Z** axis (the beam
    direction in the physics coordinate system), *width* along **X**, and
    *height* along **Y**.
    """
    mesh = UsdGeom.Mesh.Define(stage, path)

    hl, hw, hh = length / 2, width / 2, height / 2

    points = Vt.Vec3fArray(
        [
            (-hw, -hh, -hl),
            (hw, -hh, -hl),
            (hw, hh, -hl),
            (-hw, hh, -hl),
            (-hw, -hh, hl),
            (hw, -hh, hl),
            (hw, hh, hl),
            (-hw, hh, hl),
        ]
    )

    face_counts = Vt.IntArray([4] * 6)
    face_indices = Vt.IntArray(
        [
            0,
            3,
            2,
            1,  # -Z face
            4,
            5,
            6,
            7,  # +Z face
            0,
            1,
            5,
            4,  # -Y face
            2,
            3,
            7,
            6,  # +Y face
            0,
            4,
            7,
            3,  # -X face
            1,
            2,
            6,
            5,  # +X face
        ]
    )

    mesh.GetPointsAttr().Set(points)
    mesh.GetFaceVertexCountsAttr().Set(face_counts)
    mesh.GetFaceVertexIndicesAttr().Set(face_indices)
    mesh.GetSubdivisionSchemeAttr().Set("none")
    mesh.GetExtentAttr().Set(Vt.Vec3fArray([(-hw, -hh, -hl), (hw, hh, hl)]))
    return mesh


def _make_pipe_mesh(
    stage: Usd.Stage,
    path: str,
    length: float,
    a: float,
    b: float,
    thickness: float = 0.001,
    n_around: int = 24,
) -> UsdGeom.Mesh:
    """Elliptical pipe / beam-tube mesh."""
    mesh = UsdGeom.Mesh.Define(stage, path)

    theta = np.linspace(0, 2 * np.pi, n_around, endpoint=False)
    z_arr = np.array([-length / 2, length / 2])
    n_z = len(z_arr)
    n_t = n_around

    a_out, b_out = a + thickness, b + thickness

    # Vertices: outer ring sections, then inner ring sections
    points: list[tuple[float, float, float]] = []
    for z in z_arr:
        for t in theta:
            points.append(
                (float(a_out * np.cos(t)), float(b_out * np.sin(t)), float(z))
            )
    for z in z_arr:
        for t in theta:
            points.append((float(a * np.cos(t)), float(b * np.sin(t)), float(z)))

    face_counts: list[int] = []
    face_indices: list[int] = []

    # Outer surface
    for i in range(n_z - 1):
        for j in range(n_t):
            j1 = (j + 1) % n_t
            face_indices.extend(
                [i * n_t + j, i * n_t + j1, (i + 1) * n_t + j1, (i + 1) * n_t + j]
            )
            face_counts.append(4)

    # Inner surface (reversed winding)
    off = n_z * n_t
    for i in range(n_z - 1):
        for j in range(n_t):
            j1 = (j + 1) % n_t
            face_indices.extend(
                [
                    off + i * n_t + j,
                    off + (i + 1) * n_t + j,
                    off + (i + 1) * n_t + j1,
                    off + i * n_t + j1,
                ]
            )
            face_counts.append(4)

    # End caps (connect outer ↔ inner at each end)
    for iz in range(n_z):
        for j in range(n_t):
            j1 = (j + 1) % n_t
            out_base = iz * n_t
            in_base = off + iz * n_t
            if iz == 0:
                face_indices.extend(
                    [out_base + j1, out_base + j, in_base + j, in_base + j1]
                )
            else:
                face_indices.extend(
                    [out_base + j, out_base + j1, in_base + j1, in_base + j]
                )
            face_counts.append(4)

    pts_np = np.asarray(points)
    mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in points]))
    mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray(face_counts))
    mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray(face_indices))
    mesh.GetSubdivisionSchemeAttr().Set("none")
    mesh.GetExtentAttr().Set(
        Vt.Vec3fArray(
            [
                Gf.Vec3f(*pts_np.min(axis=0).tolist()),
                Gf.Vec3f(*pts_np.max(axis=0).tolist()),
            ]
        )
    )
    return mesh


# ---------------------------------------------------------------------------
# Prototype geometry creation
# ---------------------------------------------------------------------------


def _create_procedural_prototype(
    stage: Usd.Stage,
    proto_path: str,
    ele: BaseElement,
) -> None:
    """
    Create an ``Xform`` prototype at *proto_path* with child ``Mesh``
    prim(s) for the given element.

    Every prototype is an ``Xform`` whose children carry the actual mesh
    data.  This is critical for Blender compatibility: element prims are
    also ``Xform`` nodes that reference these prototypes, so the child
    meshes propagate correctly through USD composition.
    """
    UsdGeom.Xform.Define(stage, proto_path)

    # Elements with no physical geometry
    if isinstance(ele, (BeginningEle, Fiducial)):
        return

    if not isinstance(ele, BeamElement):
        return

    # Dipole bend → two half-box children
    if isinstance(ele, Bend):
        length = max(ele.length, 1e-6)
        width = max(ele.width, 1e-6)
        height = max(ele.height, 1e-6)
        half_h = (height - ele.gap) / 2
        y_off = ele.gap / 2 + half_h / 2

        top = _make_box_mesh(stage, f"{proto_path}/top", length, width, half_h)
        UsdGeom.Xformable(top.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0, y_off, 0))

        bot = _make_box_mesh(stage, f"{proto_path}/bottom", length, width, half_h)
        UsdGeom.Xformable(bot.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0, -y_off, 0))
        return

    # Pipe → elliptical tube (if aperture limits are set)
    if isinstance(ele, Pipe):
        ap = ele.aperture
        if (ap.x1_limit + ap.x2_limit > 0) and (ap.y1_limit + ap.y2_limit > 0):
            _make_pipe_mesh(
                stage,
                f"{proto_path}/mesh",
                max(ele.length, 1e-6),
                ap.x1_limit,
                ap.y1_limit,
                thickness=ap.thickness or 0.001,
            )
            return

    # Default for any BeamElement: box
    _make_box_mesh(
        stage,
        f"{proto_path}/mesh",
        max(ele.length, 1e-6),
        max(ele.width, 1e-6),
        max(ele.height, 1e-6),
    )


# ---------------------------------------------------------------------------
# Materials & display colour
# ---------------------------------------------------------------------------


def _create_material(
    stage: Usd.Stage,
    mat_path: str,
    rgba: tuple[float, float, float, float],
) -> UsdShade.Material:
    """Create a simple ``UsdPreviewSurface`` material."""
    mat = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, f"{mat_path}/PreviewShader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(rgba[0], rgba[1], rgba[2])
    )
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(rgba[3]))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.5)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def _set_display_color(
    stage: Usd.Stage,
    prim_path: str | Sdf.Path,
    rgba: tuple[float, float, float, float],
) -> None:
    """Set ``displayColor`` (and opacity) on mesh prims recursively."""
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return

    if prim.IsA(UsdGeom.Mesh):
        gprim = UsdGeom.Gprim(prim)
        gprim.GetDisplayColorAttr().Set(
            Vt.Vec3fArray([Gf.Vec3f(rgba[0], rgba[1], rgba[2])])
        )
        if rgba[3] < 1.0:
            gprim.GetDisplayOpacityAttr().Set(Vt.FloatArray([rgba[3]]))

    for child in prim.GetChildren():
        _set_display_color(stage, child.GetPath(), rgba)


def _bind_material_recursive(
    stage: Usd.Stage,
    prim_path: str | Sdf.Path,
    material: UsdShade.Material,
) -> None:
    """Bind *material* to every ``Mesh`` prim at or below *prim_path*."""
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return

    if prim.IsA(UsdGeom.Mesh):
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)

    for child in prim.GetChildren():
        _bind_material_recursive(stage, child.GetPath(), material)


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------


def _apply_element_transform(xform: UsdGeom.Xform, ele: BaseElement) -> None:
    """
    Apply position and rotation matching the Blender convention.

    Blender uses ``rotation_mode = 'ZXY'`` with
    ``rotation_euler = (-phi, theta, psi)`` and
    ``location = (x, y, z)``.
    """
    xform.AddTranslateOp().Set(Gf.Vec3d(ele.x, ele.y, ele.z))
    xform.AddRotateZXYOp().Set(
        Gf.Vec3f(
            math.degrees(-ele.phi),  # X  (negated pitch)
            math.degrees(ele.theta),  # Y  (yaw)
            math.degrees(ele.psi),  # Z  (roll)
        )
    )


# ---------------------------------------------------------------------------
# Blend file → USD conversion
# ---------------------------------------------------------------------------


def _find_blender() -> str | None:
    """Auto-detect the Blender executable."""
    path = shutil.which("blender")
    if path:
        return path
    # macOS application bundle
    mac_path = "/Applications/Blender.app/Contents/MacOS/Blender"
    if Path(mac_path).exists():
        return mac_path
    return None


def _convert_blend_to_usd(
    blend_path: Path,
    usd_path: Path,
    blender_cmd: str,
) -> bool:
    """Convert a ``.blend`` file to ``.usd`` using Blender in headless mode."""
    usd_path.parent.mkdir(parents=True, exist_ok=True)

    # The script groups all root-level objects under a single Xform so the
    # exported USD always has one clean default prim.
    script = f"""\
import bpy

# Parent all root-level objects under a wrapper so USD gets a single root
orphans = [obj for obj in bpy.data.objects if obj.parent is None]
if len(orphans) != 1:
    root = bpy.data.objects.new("model", None)
    bpy.context.scene.collection.objects.link(root)
    for obj in orphans:
        obj.parent = root

bpy.ops.wm.usd_export(filepath=r"{usd_path}")
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        script_file = f.name

    try:
        result = subprocess.run(
            [
                blender_cmd,
                "--background",
                str(blend_path),
                "--python",
                script_file,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        success = result.returncode == 0 and usd_path.exists()
        if not success:
            print(f"  ⛔ Blender conversion failed for {blend_path.name}")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-3:]:
                    print(f"     {line}")
        return success
    except subprocess.TimeoutExpired:
        print(f"  ⛔ Blender conversion timed out for {blend_path.name}")
        return False
    except FileNotFoundError:
        print(f"  ⛔ Blender executable not found: {blender_cmd}")
        return False
    finally:
        Path(script_file).unlink(missing_ok=True)


def _ensure_default_prim(usd_path: Path) -> bool:
    """Ensure the model USD file has a ``defaultPrim`` set."""
    layer = Sdf.Layer.FindOrOpen(str(usd_path))
    if layer is None:
        return False
    if layer.defaultPrim:
        return True
    root_prims = list(layer.rootPrims)
    if root_prims:
        layer.defaultPrim = root_prims[0].name
        layer.Save()
        return True
    return False


_USD_EXTENSIONS = {".usd", ".usda", ".usdc", ".usdz"}


def _is_usd_file(path: str | Path) -> bool:
    """Return *True* if *path* has a USD extension."""
    return Path(path).suffix.lower() in _USD_EXTENSIONS


def _convert_catalogue_models(
    elements: list[BaseElement],
    catalogue: Path,
    models_dir: Path,
    blender_cmd: str | None,
    copy_models: bool = True,
) -> dict[str, Path]:
    """
    Resolve unique CAD models from *catalogue* to USD files.

    * ``.usd`` / ``.usda`` / ``.usdc`` / ``.usdz`` files are used
      directly.  When *copy_models* is ``True`` they are copied into
      *models_dir* for portability; when ``False`` they are referenced
      in place.
    * ``.blend`` files are converted to ``.usd`` via Blender headless
      (always written to *models_dir*).
    * Already-converted / already-copied files in *models_dir* are
      reused.

    Returns
    -------
    dict
        Mapping ``cad_model`` (relative path string) → resolved USD path.
    """
    unique_models: set[str] = set()
    for ele in elements:
        if ele.cad_model:
            unique_models.add(ele.cad_model)

    if not unique_models:
        return {}

    print(f"Resolving {len(unique_models)} unique CAD model(s) " f"from catalogue…")

    converted: dict[str, Path] = {}
    for cad_model in sorted(unique_models):
        src_path = catalogue / cad_model

        if _is_usd_file(cad_model):
            if copy_models:
                # Copy into models_dir for portability
                usd_rel = Path(cad_model)
                usd_path = models_dir / usd_rel

                if usd_path.exists():
                    print(f"  ✅ Already present: {usd_rel}")
                elif src_path.exists():
                    usd_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, usd_path)
                    print(f"  ✅ Copied USD: {usd_rel}")
                elif Path(cad_model).is_absolute() and Path(cad_model).exists():
                    usd_path = Path(cad_model)
                    print(f"  ✅ Using absolute USD: {cad_model}")
                else:
                    print(f"  ⛔ Missing: {src_path}")
                    continue
            else:
                # Reference in place – no copy
                if src_path.exists():
                    usd_path = src_path.resolve()
                    print(f"  ✅ Referencing in place: {cad_model}")
                elif Path(cad_model).is_absolute() and Path(cad_model).exists():
                    usd_path = Path(cad_model)
                    print(f"  ✅ Using absolute USD: {cad_model}")
                else:
                    print(f"  ⛔ Missing: {src_path}")
                    continue

            _ensure_default_prim(usd_path)
            converted[cad_model] = usd_path
            continue

        # .blend file – needs conversion (always to models_dir)
        if not src_path.exists():
            print(f"  ⛔ Missing: {src_path}")
            continue

        usd_rel = Path(cad_model).with_suffix(".usd")
        usd_path = models_dir / usd_rel

        if usd_path.exists():
            print(f"  ✅ Already converted: {usd_rel}")
            converted[cad_model] = usd_path
            continue

        if blender_cmd is None:
            print(
                f"  ⛔ Blender not found – cannot convert {cad_model} "
                f"(will use procedural geometry)"
            )
            continue

        print(f"  🔄 Converting: {cad_model}")
        if _convert_blend_to_usd(src_path, usd_path, blender_cmd):
            _ensure_default_prim(usd_path)
            converted[cad_model] = usd_path
            print(f"  ✅ Done: {usd_rel}")
        else:
            print(f"  ⛔ Failed: {cad_model}  (will use procedural geometry)")

    return converted


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------


def _add_track(
    stage: Usd.Stage,
    parent_path: str,
    track: Track,
) -> UsdGeom.BasisCurves:
    """Add a ``Track`` as a ``BasisCurves`` prim."""
    name = _sanitize_usd_name(track.name or "track")
    curve_path = f"{parent_path}/{name}"

    curves = UsdGeom.BasisCurves.Define(stage, curve_path)

    n = len(track.x)
    points = Vt.Vec3fArray(
        [
            Gf.Vec3f(float(track.x[i]), float(track.y[i]), float(track.z[i]))
            for i in range(n)
        ]
    )

    curves.GetPointsAttr().Set(points)
    curves.GetCurveVertexCountsAttr().Set(Vt.IntArray([n]))
    curves.GetTypeAttr().Set("linear")

    # Width derived from track weight
    w = max(float(track.weight) * 0.01, 0.005)
    curves.GetWidthsAttr().Set(Vt.FloatArray([w] * n))

    # Colour
    if track.color is not None:
        rgba = (
            resolve_color(track.color)
            if isinstance(track.color, str)
            else (tuple(track.color) if len(track.color) >= 4 else (*track.color, 1.0))
        )
        curves.GetDisplayColorAttr().Set(
            Vt.Vec3fArray([Gf.Vec3f(rgba[0], rgba[1], rgba[2])])
        )

    # Extent
    pts_np = np.column_stack([track.x, track.y, track.z])
    ext_min = pts_np.min(axis=0) - w
    ext_max = pts_np.max(axis=0) + w
    curves.GetExtentAttr().Set(
        Vt.Vec3fArray([Gf.Vec3f(*ext_min.tolist()), Gf.Vec3f(*ext_max.tolist())])
    )

    return curves


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------


def _add_envelope(
    stage: Usd.Stage,
    parent_path: str,
    envelope: Envelope,
) -> UsdGeom.Mesh:
    """
    Add an ``Envelope`` as a mesh constructed from its cross-section loops.
    """
    name = _sanitize_usd_name(envelope.name or "envelope")
    mesh_path = f"{parent_path}/{name}"
    mesh = UsdGeom.Mesh.Define(stage, mesh_path)

    all_points: list[tuple[float, float, float]] = []
    face_counts: list[int] = []
    face_indices: list[int] = []

    loops = list(envelope.loops)
    for loop in loops:
        for v in loop.vertices:
            all_points.append((float(v.x), float(v.y), float(v.z)))

    # Build quad faces between consecutive loops
    offset = 0
    for li in range(len(loops) - 1):
        n0 = len(loops[li].vertices)
        n1 = len(loops[li + 1].vertices)
        next_offset = offset + n0
        n = min(n0, n1)
        for j in range(n):
            j1 = (j + 1) % n
            face_indices.extend(
                [offset + j, offset + j1, next_offset + j1, next_offset + j]
            )
            face_counts.append(4)
        offset = next_offset

    pts_np = np.asarray(all_points)
    mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in all_points]))
    mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray(face_counts))
    mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray(face_indices))
    mesh.GetSubdivisionSchemeAttr().Set("none")

    if len(pts_np):
        mesh.GetExtentAttr().Set(
            Vt.Vec3fArray(
                [
                    Gf.Vec3f(*pts_np.min(axis=0).tolist()),
                    Gf.Vec3f(*pts_np.max(axis=0).tolist()),
                ]
            )
        )

    # Colour
    color = (
        resolve_color(envelope.color)
        if isinstance(envelope.color, str)
        else tuple(envelope.color)
    )
    if len(color) == 3:
        color = (*color, 1.0)
    mesh_gprim = UsdGeom.Gprim(mesh.GetPrim())
    mesh_gprim.GetDisplayColorAttr().Set(
        Vt.Vec3fArray([Gf.Vec3f(color[0], color[1], color[2])])
    )
    if color[3] < 1.0:
        mesh_gprim.GetDisplayOpacityAttr().Set(Vt.FloatArray([color[3]]))

    return mesh


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------


def lattice_to_usd(
    elements: list[BaseElement] | None = None,
    tracks: list[Track] | None = None,
    envelopes: list[Envelope] | None = None,
    filepath: str | Path = "lattice.usda",
    *,
    up_axis: str = "Y",
    meters_per_unit: float = 1.0,
    catalogue: str | Path | None = None,
    blender_cmd: str | None = None,
    copy_models: bool = True,
    models_dir: str | Path | None = None,
) -> Usd.Stage:
    """
    Export lattice data to a USD file.

    Parameters
    ----------
    elements : list of BaseElement, optional
        Lattice elements to export.
    tracks : list of Track, optional
        Particle / orbit tracks to export.
    envelopes : list of Envelope, optional
        Beam envelopes to export.
    filepath : str or Path
        Output path.  Use ``.usda`` for human-readable ASCII or
        ``.usd`` / ``.usdc`` for binary (crate) format.
    up_axis : str
        Stage up-axis: ``'Y'`` (USD default) or ``'Z'`` (Blender default).
    meters_per_unit : float
        Scene scale.  ``1.0`` means positions are in metres.
    catalogue : str or Path, optional
        Path to the directory containing CAD model files.  Element
        ``cad_model`` fields are resolved relative to this path.
    blender_cmd : str, optional
        Path to the Blender executable for ``.blend`` → ``.usd``
        conversion.  If *None*, auto-detected from ``PATH`` and common
        install locations.
    copy_models : bool
        If ``True`` (default), USD model files from the catalogue are
        copied into a ``models/`` subdirectory next to the output file
        for portability.  If ``False``, they are referenced in place
        (avoids duplication when the catalogue is always accessible).
    models_dir : str or Path, optional
        Directory for converted / copied CAD model files.  Defaults to
        a ``models/`` subdirectory next to *filepath*.

    Returns
    -------
    Usd.Stage
        The created USD stage (already saved to *filepath*).

    Notes
    -----
    *   Prototype geometry is created once under ``/Root/Prototypes`` as
        ``Xform`` prims containing child ``Mesh`` prims.  Each element
        prim under ``/Root/Elements`` is also an ``Xform`` that
        references a prototype, so the child meshes propagate through
        USD composition.  This is compatible with Blender's USD importer.
    *   ``UsdPreviewSurface`` materials are created per unique colour so
        the file renders correctly in Omniverse, Blender, and other DCC
        tools.
    *   When *catalogue* is supplied, each unique ``.blend`` model is
        converted to ``.usd`` via Blender headless and referenced from
        the prototype.  Conversion results are cached in the ``models/``
        directory so subsequent exports are fast.
    """
    filepath = Path(filepath)
    filepath_str = str(filepath)
    output_dir = filepath.parent

    # Remove existing file – Usd.Stage.CreateNew raises if it exists
    if filepath.exists():
        filepath.unlink()

    stage = Usd.Stage.CreateNew(filepath_str)
    up_token = UsdGeom.Tokens.y if up_axis.upper() == "Y" else UsdGeom.Tokens.z
    UsdGeom.SetStageUpAxis(stage, up_token)
    UsdGeom.SetStageMetersPerUnit(stage, meters_per_unit)

    # Use Scope (not Xform) so Blender doesn't create a parent Empty
    # at the origin that causes relationship-line clutter.
    root_scope = UsdGeom.Scope.Define(stage, "/Root")
    stage.SetDefaultPrim(root_scope.GetPrim())

    # ---- Materials --------------------------------------------------------
    UsdGeom.Scope.Define(stage, "/Root/Materials")
    material_cache: dict[str, UsdShade.Material] = {}

    def _get_or_create_material(color_name: str) -> UsdShade.Material:
        if color_name not in material_cache:
            rgba = resolve_color(color_name)
            mat_usd_name = _sanitize_usd_name(color_name)
            mat = _create_material(stage, f"/Root/Materials/{mat_usd_name}", rgba)
            material_cache[color_name] = mat
        return material_cache[color_name]

    # ---- Resolve / convert CAD models from catalogue ----------------------
    converted_models: dict[str, Path] = {}
    if elements and catalogue is not None:
        catalogue = Path(catalogue)
        if not catalogue.exists():
            print(f"⚠️  Catalogue not found: {catalogue}")
        else:
            if blender_cmd is None:
                blender_cmd = _find_blender()

            models_dir = (
                Path(models_dir) if models_dir is not None else output_dir / "models"
            )
            converted_models = _convert_catalogue_models(
                elements,
                catalogue,
                models_dir,
                blender_cmd,
                copy_models=copy_models,
            )

    # ---- Elements ---------------------------------------------------------
    if elements:
        # Prototypes scope – hidden so prototypes are not rendered standalone
        proto_scope = UsdGeom.Scope.Define(stage, "/Root/Prototypes")
        UsdGeom.Imageable(proto_scope.GetPrim()).MakeInvisible()

        prototype_cache: dict[str, str] = {}  # proto_key → prim path
        collection_created: set[str] = set()
        # Track element name usage per collection to deduplicate.
        # Bmad lattices reuse element names (e.g. QF appears 8 times).
        _name_counts: dict[str, int] = {}

        UsdGeom.Scope.Define(stage, "/Root/Elements")

        for ele in elements:
            cls_name = ele.__class__.__name__
            col_name = f"{cls_name}s"

            # Ensure the class collection exists
            if col_name not in collection_created:
                UsdGeom.Scope.Define(stage, f"/Root/Elements/{col_name}")
                collection_created.add(col_name)

            # Create prototype if needed
            key = _proto_key(ele)
            if key not in prototype_cache:
                proto_usd_name = _sanitize_usd_name(key)
                proto_path = f"/Root/Prototypes/{proto_usd_name}"

                used_cad = False

                # Try converted CAD model first
                if ele.cad_model and ele.cad_model in converted_models:
                    model_usd_path = converted_models[ele.cad_model]
                    UsdGeom.Xform.Define(stage, proto_path)
                    proto_prim = stage.GetPrimAtPath(proto_path)

                    # Relative path so output is portable
                    rel_model = os.path.relpath(model_usd_path, output_dir)
                    proto_prim.GetReferences().AddReference(assetPath=str(rel_model))
                    used_cad = True

                if not used_cad:
                    # Procedural geometry fallback
                    _create_procedural_prototype(stage, proto_path, ele)

                    # Display colour + material (CAD models keep their own)
                    rgba = _get_element_color(ele)
                    _set_display_color(stage, proto_path, rgba)

                    cname = _color_key(ele)
                    mat = _get_or_create_material(cname)
                    _bind_material_recursive(stage, proto_path, mat)

                prototype_cache[key] = proto_path

            proto_path = prototype_cache[key]

            # Create element instance as an Xform referencing the prototype.
            # Deduplicate names — Bmad reuses names across instances.
            ele_usd_name = _sanitize_usd_name(ele.name)
            scope_key = f"{col_name}/{ele_usd_name}"
            count = _name_counts.get(scope_key, 0)
            _name_counts[scope_key] = count + 1
            if count > 0:
                ele_usd_name = f"{ele_usd_name}_{count}"
            ele_path = f"/Root/Elements/{col_name}/{ele_usd_name}"

            xform = UsdGeom.Xform.Define(stage, ele_path)
            prim = xform.GetPrim()

            # Reference shared prototype geometry
            prim.GetReferences().AddInternalReference(Sdf.Path(proto_path))

            # Transform (position + orientation)
            _apply_element_transform(xform, ele)

            # Metadata
            prim.SetCustomDataByKey("element_name", ele.name)
            prim.SetCustomDataByKey("element_class", cls_name)
            if ele.cad_model:
                prim.SetCustomDataByKey("cad_model", ele.cad_model)
            if ele.description:
                prim.SetCustomDataByKey("description", ele.description)

    # ---- Tracks -----------------------------------------------------------
    if tracks:
        UsdGeom.Scope.Define(stage, "/Root/Tracks")
        for track in tracks:
            _add_track(stage, "/Root/Tracks", track)

    # ---- Envelopes --------------------------------------------------------
    if envelopes:
        UsdGeom.Scope.Define(stage, "/Root/Envelopes")
        for envelope in envelopes:
            _add_envelope(stage, "/Root/Envelopes", envelope)

    # ---- Save -------------------------------------------------------------
    stage.GetRootLayer().Save()
    print(f"USD file saved: {filepath}")
    return stage
