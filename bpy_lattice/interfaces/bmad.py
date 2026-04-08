from __future__ import annotations

import argparse
import logging
import pathlib
import typing
from enum import StrEnum
from typing import Literal
import numpy as np
from ..envelopes import Envelope, EnvelopeLoop

from ..elements import (
    Aperture,
    Bend,
    get_element_class,
    save_elements_to_json,
)
from ..types import ApertureShape

from ..tracks import Track

if typing.TYPE_CHECKING:
    from pytao import Tao

#
#
# apertures will be separated from elements:
# quad with aperture ->
#     Quadrupole
#     Pipe with parent


# Note that these shou
class EleKey(StrEnum):
    AB_MULTIPOLE = "ab_multipole"
    AC_KICKER = "ac_kicker"
    BEAMBEAM = "beambeam"
    BEGINNING_ELE = "beginning_ele"
    CONVERTER = "converter"
    CRAB_CAVITY = "crab_cavity"
    CUSTOM = "custom"
    DRIFT = "drift"
    E_GUN = "e_gun"
    ECOLLIMATOR = "ecollimator"
    ELSEPARATOR = "elseparator"
    EM_FIELD = "em_field"
    FEEDBACK = "feedback"
    FIDUCIAL = "fiducial"
    FLOOR_SHIFT = "floor_shift"
    FOIL = "foil"
    FORK = "fork"
    GKICKER = "gkicker"
    GROUP = "group"
    HKICKER = "hkicker"
    HYBRID = "hybrid"
    INSTRUMENT = "instrument"
    KICKER = "kicker"
    LCAVITY = "lcavity"
    MARKER = "marker"
    MASK = "mask"
    MATCH = "match"
    MIRROR = "mirror"
    MONITOR = "monitor"
    MULTIPOLE = "multipole"
    NULL_ELE = "null_ele"
    OCTUPOLE = "octupole"
    OVERLAY = "overlay"
    PATCH = "patch"
    PHOTON_FORK = "photon_fork"
    PIPE = "pipe"
    QUADRUPOLE = "quadrupole"
    RCOLLIMATOR = "rcollimator"
    RF_BEND = "rf_bend"
    RFCAVITY = "rfcavity"
    SAD_MULT = "sad_mult"
    SBEND = "sbend"
    SEXTUPOLE = "sextupole"
    SOL_QUAD = "sol_quad"
    SOLENOID = "solenoid"
    TAYLOR = "taylor"
    THICK_MULTIPOLE = "thick_multipole"
    UNDULATOR = "undulator"
    VKICKER = "vkicker"
    WIGGLER = "wiggler"


# Mapping Enum to Class Names
EleKey_TO_CLASSNAME = {
    EleKey.AB_MULTIPOLE: "Multipole",
    EleKey.AC_KICKER: "ACKicker",
    EleKey.BEAMBEAM: "BeamBeam",
    EleKey.BEGINNING_ELE: "BeginningEle",
    EleKey.CONVERTER: "Converter",
    EleKey.CRAB_CAVITY: "CrabCavity",
    EleKey.DRIFT: "Pipe",
    EleKey.E_GUN: "EGun",
    EleKey.ECOLLIMATOR: "Collimator",
    EleKey.ELSEPARATOR: "Instrument",  # TODO
    EleKey.EM_FIELD: "Instrument",  # TODO
    EleKey.FIDUCIAL: "Fiducial",
    EleKey.FLOOR_SHIFT: "FloorShift",
    EleKey.FOIL: "Foil",
    EleKey.FORK: "Fork",
    EleKey.GKICKER: "Kicker",  # TODO
    EleKey.HKICKER: "Kicker",
    EleKey.INSTRUMENT: "Instrument",
    EleKey.KICKER: "Kicker",
    EleKey.LCAVITY: "LCavity",
    EleKey.MARKER: "Marker",
    EleKey.MASK: "Collimator",
    EleKey.MATCH: "Match",
    EleKey.MIRROR: "Mirror",
    EleKey.MONITOR: "Instrument",
    EleKey.MULTIPOLE: "Multipole",
    EleKey.NULL_ELE: "NullEle",
    EleKey.OCTUPOLE: "Octupole",
    EleKey.PATCH: "Patch",
    EleKey.PIPE: "Pipe",
    EleKey.QUADRUPOLE: "Quadrupole",
    EleKey.RCOLLIMATOR: "Collimator",
    EleKey.RFCAVITY: "RFCavity",
    EleKey.SAD_MULT: "Instrument",  # TODO
    EleKey.SBEND: "Bend",
    EleKey.SEXTUPOLE: "Sextupole",
    EleKey.SOLENOID: "Solenoid",
    EleKey.SOL_QUAD: "Instrument",  # TODO
    EleKey.TAYLOR: "Taylor",
    EleKey.THICK_MULTIPOLE: "Multipole",
    EleKey.UNDULATOR: "Undulator",
    EleKey.VKICKER: "Kicker",
    EleKey.WIGGLER: "Undulator",
}


def element_class_from_key(key: EleKey):
    key = EleKey(key)
    if key not in EleKey_TO_CLASSNAME:
        raise NotImplementedError(key)
    return get_element_class(EleKey_TO_CLASSNAME[key])


def get_rvec_wmat(tao, ele_id):
    floor = tao.ele_floor(ele_id)
    rvec = floor["Reference"][0:3]
    wmat = floor["Reference-W"].reshape(3, 3, order="F")
    return rvec, wmat


def get_global_orbit(tao, ele_id):
    """
    returns position and momentum vectors in global coordinates


    Returns
    -------
    position: ndarray
        array with [x, y, z] in m
    momentum: ndarray
        momentum with [px, py, pz] in eV/c
    """

    orbit = tao.ele_orbit(ele_id)
    rvec, wmat = get_rvec_wmat(tao, ele_id)

    x, y = orbit["x"], orbit["y"]
    p0c = orbit["p0c"]
    px, py, delta = orbit["px"], orbit["py"], orbit["pz"]  # Bmad coordinates
    # Momenta in eV/c
    pz = np.sqrt((1 + delta) ** 2 - px**2 - py**2) * p0c
    px = px * p0c
    py = py * p0c

    xvec = np.array([x, y, 0])  # z=0 by definition
    pvec = np.array([px, py, pz])

    position = wmat @ xvec + rvec
    momentum = wmat @ pvec

    return position, momentum


def get_ele_data(tao, ele_id):
    """
    Get normalized element data dict from Tao
    """
    info = tao.ele_head(ele_id)
    info.update(tao.ele_gen_attribs(ele_id))
    # info.update(tao.ele_methods)

    # Convert to lower case
    info = {k.lower(): v for k, v in info.items()}
    ix_ele = info["ix_ele"]
    # use EleKey
    key = EleKey(info["key"].lower())
    info["key"] = key

    # Get global floor
    if key == EleKey.MIRROR:
        # Average the floor position vectors
        # Use Reference because of a bug:
        # https://github.com/bmad-sim/bmad-ecosystem/issues/1266
        r = tao.ele_floor(ix_ele, where="end")["Reference"]
        r0 = tao.ele_floor(ix_ele - 1, where="end")["Reference"]  # Previous element
        r = (r + r0) / 2
    else:
        floor = tao.ele_floor(ele_id, where="center")
        # Handle for multipass floor
        if (
            "Actual" not in floor
        ):  # TODO: Actual is better, but if gives the wrong orientation
            r = floor["Actual-Slave1"]
        else:
            r = floor["Actual"]
    x, y, z, theta, phi, psi = r
    info["floor_x"] = x
    info["floor_y"] = y
    info["floor_z"] = z
    info["floor_theta"] = theta
    info["floor_phi"] = phi
    info["floor_psi"] = psi

    # Normalize kicker attributes
    if key == EleKey.HKICKER:
        info["hkick"] = info.pop("kick")
        info["bl_hkick"] = info.pop("bl_kick")
    elif key == EleKey.VKICKER:
        info["vkick"] = info.pop("kick")
        info["bl_vkick"] = info.pop("bl_kick")

    # TODO
    # elif key == EleKey.GKICKER:
    #    print(info)
    #    raise NotImplementedError(key)

    ix_universe = info["universe"]
    ix_branch = info[f"{ix_universe}^ix_branch"]
    branch1 = tao.branch1(ix_uni=ix_universe, ix_branch=ix_branch)
    info["metadata"] = {
        "ix_universe": ix_universe,
        "ix_branch": ix_branch,
        "branch": branch1["name"],
    }
    return info


def get_basic_element_kwargs_from_tao_data(data):
    """
    Sets basic element data from tao data.
    """
    descrip = data.get("descrip", "")
    cad_model = descrip.split("3DMODEL=")[-1].split(",")[0]  # Extract before the comma
    if cad_model:
        description = descrip.replace(cad_model, "")
    else:
        description = descrip

    return dict(
        name=str(data["name"]),
        type=str(data.get("type", "")),
        x=float(data["floor_x"]),
        y=float(data["floor_y"]),
        z=float(data["floor_z"]),
        theta=float(data["floor_theta"]),
        phi=float(data["floor_phi"]),
        psi=float(data["floor_psi"]),
        description=description,
        cad_model=cad_model,
        metadata=data.get("metadata", {}),
    )


def get_aperture_from_tao_data(data):
    """
    Sets Pipe specfic data from tao data
    """

    return Aperture(
        shape=ApertureShape(data["aperture_type"].lower()),
        x1_limit=float(data["x1_limit"]),
        x2_limit=float(data["x2_limit"]),
        y1_limit=float(data["y1_limit"]),
        y2_limit=float(data["y2_limit"]),
        thickness=0.0,  # Not available in Tao
        material="",  # Not available in Tao
    )


def bpy_element_from_tao(tao, ele_id):
    """

    Create elements from a single Tao element.

    Multiple elements are created


    Parameters
    ----------
    tao : pytao.Tao
        running instance of tao

    ele_id : int or str
        Element ID to look up in Tao.
        For Mirror elements, the previous element is used for the floor calc.

    Returns
    -------


    """
    data = get_ele_data(tao, ele_id)
    return bpy_element_from_tao_data(data)


def get_length_from_element(key: EleKey, data):
    if key in (EleKey.BEGINNING_ELE, EleKey.FIDUCIAL, EleKey.MASK):
        return None

    # zero-length elements
    if key in (EleKey.GKICKER, EleKey.MASK):
        return 1e-6
    if "l" not in data:
        raise AttributeError(f"'l' missing from {key}")

    return data["l"]


def bpy_element_from_tao_data(data):
    # Cast to proper EleKey
    key = EleKey(data["key"])

    # Skip
    if key in (EleKey.OVERLAY,):
        return None

    ele_cls = element_class_from_key(key)
    basic_kw = get_basic_element_kwargs_from_tao_data(data)

    length = get_length_from_element(key, data)

    if length is None:
        return ele_cls(**basic_kw)

    aperture = get_aperture_from_tao_data(data)

    if ele_cls is Bend:
        return ele_cls(
            **basic_kw,
            length=length,
            aperture=aperture,
            curvature=float(data["g"]),
            edge_angle1=float(data["e1"]),
            edge_angle2=float(data["e2"]),
            tilt=float(data["ref_tilt"]),
        )

    return ele_cls(
        **basic_kw,
        length=length,
        aperture=aperture,
    )


def bpy_elements_from_tao(
    tao: Tao,
    ele_ids: list[str] | None = None,
    add_bend_pipes: bool = True,
) -> list:
    """
    Convert Tao elements into Blender (bpy) elements.

    Parameters
    ----------
    tao : Tao
        The Tao object.
    ele_ids : list of int or str, optional
        A list of element IDs to convert. If not provided, all unique elements
        will be retrieved using the "-no_slaves" flag.
    add_bend_pipes : bool, default=True
        A flag to include additional adjustments for bend pipes.

    Returns
    -------
    list
        A list of Blender (bpy) elements corresponding to the input element IDs.
    """
    if ele_ids is None:
        ele_ids = tao.lat_list("*", "ele.ix_ele", flags="-no_slaves")

    eles = []
    for ele_id in ele_ids:
        ele = bpy_element_from_tao(tao, ele_id)

        if ele is None:
            continue

        eles.append(ele)

    return eles


def write_bpy_lattice_json(tao, outfile, ele_ids=None):
    """
    This writes the `.layout_table` JSON file that the
    bmad_to_blender Fortran program creates for bpy_lattice

    Notes
    -----
    This is intended to replace the functionality of:
    https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/interface/blender_interface_mod.f90

    Parameters
    ----------
    tao : PyTao.tao
        running instance of tao
    outfile : str
        File to write to
    ele_ids : list of str or int, optional
        List of elements to extract
        Default: None => will match all unique elements of the lattice (i.e., without slaves)
    """
    eles = bpy_elements_from_tao(tao, ele_ids=ele_ids)
    save_elements_to_json(eles, outfile)


def floor_orbit_track_from_tao(
    tao,
    match="*",
    remove_duplicates=True,
    name="orbit",
    weight=0.01,
    color="blue",
):
    """
    Return a Track of the orbit in global coordinates
    """

    xs = tao.lat_list(match, "orbit.floor.x")
    ys = tao.lat_list(match, "orbit.floor.y")
    zs = tao.lat_list(match, "orbit.floor.z")

    # Filter
    if remove_duplicates:
        ss = tao.lat_list(match, "ele.s")
        uix = np.unique(ss, return_index=True)[1]
        xs = xs[uix]
        ys = ys[uix]
        zs = zs[uix]
    return Track(x=xs, y=ys, z=zs, name=name, weight=weight, color=color)


def bmad_to_blender_entrypoint():
    """
    Entry point for generating a lattice JSON from a Bmad lattice file.

    This function parses command-line arguments to specify the lattice file,
    output file, element list, and verbosity level. It initializes an instance
    of PyTao, processes the lattice data, and writes the output JSON.
    """
    try:
        import pytao
    except ImportError:
        raise RuntimeError(
            "pytao is required to use this entrypoint. Install it with `python -m pip install pytao`"
        )

    parser = argparse.ArgumentParser(
        description="Generate a lattice JSON from Tao using advanced element filtering.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("lattice_file", type=str, help="Lattice file path")
    parser.add_argument(
        "outfile",
        type=str,
        nargs="?",
        help="Output JSON file path (default: based on lattice file)",
    )
    parser.add_argument(
        "-e",
        "--elements",
        type=str,
        action="append",
        default=None,
        help=(
            "Selectors for lattice elements, for example: \n"
            "- All elements from universe index: '1'\n"
            "- All elements from branch index: '1@2' (universe 1, branch 2)\n"
            "- One element by ID: '1@0>>10' (universe 1, branch 0, element 10)\n"
            "- Leave blank to retrieve all elements in the superuniverse.\n"
            "\n"
            "May be specified multiple times to include multiple universes, elements, etc.\n"
            "Be sure to use quotes for '>' characters!"
        ),
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Configure logging
    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    lattice_file = pathlib.Path(args.lattice_file)
    if lattice_file.suffix.lower() == ".init":
        logger.info("Initializing Tao with: -init %s", args.lattice_file)
        tao = pytao.Tao(init_file=args.lattice_file, noplot=True)
    else:
        logger.info("Initializing Tao with lattice file: %s", args.lattice_file)
        tao = pytao.Tao(lattice_file=args.lattice_file, noplot=True)

    if args.outfile is None:
        if lattice_file.suffix.lower() == ".bmad":
            outfile = lattice_file.with_suffix(".json")
        elif lattice_file.name.lower() == "tao.init":
            outfile = "tao.json"
        else:
            outfile = f"{args.lattice_file}.json"
    else:
        outfile = args.outfile

    logger.info("Writing lattice JSON to: %s", outfile)
    ele_ids = tao.unique_ele_ids(*args.elements or [])
    write_bpy_lattice_json(tao, outfile, ele_ids=ele_ids)
    logger.info("Lattice JSON generation completed successfully.")


def bmad_to_usd_entrypoint():
    """
    Entry point for exporting a Bmad lattice to a USD file.

    Parses command-line arguments for the lattice file, output USD path,
    catalogue directory, and other options, then writes the USD file.
    """
    try:
        import pytao
    except ImportError:
        raise RuntimeError(
            "pytao is required to use this entrypoint. Install it with `python -m pip install pytao`"
        )

    from ..lattice import Lattice

    parser = argparse.ArgumentParser(
        description="Export a Bmad lattice to USD (Universal Scene Description)."
    )

    parser.add_argument("lattice_file", type=str, help="Bmad lattice file path")
    parser.add_argument(
        "outfile",
        type=str,
        nargs="?",
        help="Output USD file path (default: based on lattice file, .usda)",
    )
    parser.add_argument(
        "--catalogue",
        type=str,
        default=None,
        help="Path to the CAD-model catalogue directory",
    )
    parser.add_argument(
        "--up-axis",
        type=str,
        default="Y",
        choices=["Y", "Z"],
        help="Stage up-axis: Y (Omniverse default) or Z (Blender default)",
    )
    parser.add_argument(
        "--no-copy-models",
        action="store_true",
        help="Reference catalogue USD models in place instead of copying",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=None,
        help="Directory for converted/copied CAD models (default: models/ next to output)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Set up logging
    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    # Determine output file name if not provided
    if args.outfile is None:
        if args.lattice_file.endswith(".bmad"):
            outfile = args.lattice_file.replace(".bmad", ".usda")
        else:
            outfile = f"{args.lattice_file}.usda"
    else:
        outfile = args.outfile

    # Create a running instance of PyTao
    logger.info("Initializing Tao with lattice file: %s", args.lattice_file)
    tao = pytao.Tao(lattice_file=args.lattice_file, noplot=True)

    # Build lattice and export to USD
    logger.info("Exporting lattice to USD: %s", outfile)
    lattice = Lattice.from_tao(tao)
    lattice.to_usd(
        outfile,
        up_axis=args.up_axis,
        catalogue=args.catalogue,
        copy_models=not args.no_copy_models,
        models_dir=args.models_dir,
    )
    logger.info("USD export completed successfully.")


# Envelope and Bmad dump file


def wedge_star_envelope(
    points: np.ndarray,
    n_bins: int = 360,
    margin: float = 0.0,
    fallback_fraction: float = 0.05,
    closed: bool = False,
    normalize: Literal[False, "std", "cov"] = "cov",
) -> tuple[np.ndarray, np.ndarray]:
    """
    Create a star-shaped envelope by binning points into angular wedges.
    Supports optional normalization using standard deviation or covariance.

    Parameters
    ----------
    points : np.ndarray
        (N, 2) array of 2D points.
    n_bins : int
        Number of angular wedges.
    margin : float
        Fractional margin to expand envelope radius slightly.
    fallback_fraction : float
        Radius fraction to use in empty wedges.
    closed : bool
        If True, first point is repeated at the end.
    normalize : {'std', 'cov', False}
        Method for normalizing point distribution before computing angles.

    Returns
    -------
    envelope : np.ndarray
        (n_bins [+1], 2) array of boundary points.
    centroid : np.ndarray
        (2,) centroid of the input points.
    """
    centroid = np.mean(points, axis=0)
    rel = points - centroid

    if normalize == "cov":
        C = np.cov(rel.T)
        try:
            L = np.linalg.cholesky(C)
            C_inv_sqrt = np.linalg.inv(L).T
            rel_norm = rel @ C_inv_sqrt
        except np.linalg.LinAlgError:
            rel_norm = rel  # fallback: no normalization
            C_inv_sqrt = None
    elif normalize == "std":
        scale = np.std(rel, axis=0)
        scale[scale == 0] = 1
        rel_norm = rel / scale
    else:
        rel_norm = rel

    angles = np.arctan2(rel_norm[:, 1], rel_norm[:, 0]) % (2 * np.pi)
    radii = np.linalg.norm(rel_norm, axis=1)
    r_fallback = np.mean(radii) * fallback_fraction

    bin_edges = np.linspace(0, 2 * np.pi, n_bins + 1)
    bin_indices = np.digitize(angles, bin_edges) - 1

    angle_mids = (bin_edges[:-1] + bin_edges[1:]) / 2
    cos_vals = np.cos(angle_mids)
    sin_vals = np.sin(angle_mids)

    envelope = []
    for i in range(n_bins):
        mask = bin_indices == i
        r_max = np.max(radii[mask]) * (1 + margin) if np.any(mask) else r_fallback
        vec_norm = np.array([r_max * cos_vals[i], r_max * sin_vals[i]])

        # Un-normalize if needed
        if normalize == "cov" and "C_inv_sqrt" in locals():
            vec = vec_norm @ np.linalg.inv(C_inv_sqrt)
        elif normalize == "std":
            vec = vec_norm * scale
        else:
            vec = vec_norm

        envelope.append(centroid + vec)

    envelope = np.array(envelope)
    if closed:
        envelope = np.vstack([envelope, envelope[0]])

    return envelope, centroid


def extract_dump_particles(h5, gname, species=None):
    from pmd_beamphysics import ParticleGroup

    g = h5["data"][gname]["particles"]
    if species is None:
        species = get_species(g)
    g = g[species]
    return ParticleGroup(g)


def get_species(h5):
    slist = list(h5)
    if len(slist) != 1:
        raise NotImplementedError(f"More than one species: {slist=}")
    return slist[0]


# Bmad Dump file utils
def extract_dump_ix_ele(h5, gname, species=None):
    g = h5[f"data/{gname}/particles"]
    if species is None:
        species = get_species(g)
    g = g[species]
    return int(g["elementIndex"].attrs["value"][0])


def beam_global_envelopeloop(
    h5,
    gname,
    rvec=None,
    wmat=None,
    n_bins=360,
    scale=1,
):
    pg = extract_dump_particles(h5, gname)
    x = pg.x
    y = pg.y
    points = np.array([x, y]).T
    envelope, _ = wedge_star_envelope(points, n_bins=n_bins)

    # Extend to 3d
    envelope_3d = np.hstack([envelope * scale, np.zeros((envelope.shape[0], 1))])

    # Global
    if rvec is not None and wmat is not None:
        envelope_3d = (wmat @ envelope_3d.T).T + rvec

    return EnvelopeLoop(envelope_3d)


def beam_envelope_from_dump_h5(tao, h5, n_bins=36, scale=1):
    loops = []
    unique_s = set()
    for gname in list(h5["data"]):
        ix_ele = extract_dump_ix_ele(h5, gname)
        rvec, wmat = get_rvec_wmat(tao, ix_ele)
        head = tao.ele_head(ix_ele)
        s = head["s"]
        if s in unique_s:
            print("skipping duplicate s:", s)
            continue
        else:
            unique_s.add(s)
        loop = beam_global_envelopeloop(
            h5, gname, rvec, wmat, n_bins=n_bins, scale=scale
        )
        loops.append(loop)

    envelope = Envelope(loops=loops)

    return envelope


def beam_envelope_from_dump(tao, file, n_bins=36, scale=1):
    import h5py

    with h5py.File(file, "r") as h5:
        envelope = beam_envelope_from_dump_h5(tao, h5, n_bins=n_bins, scale=scale)
    return envelope
