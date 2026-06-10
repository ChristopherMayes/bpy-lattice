import pathlib

import bpy
import pytao
import pytest

from .conftest import LATTICES_ROOT, TEST_ARTIFACTS
from ..interfaces.bmad import bpy_elements_from_tao
from ..blend import add_elements_to_blender
from ..lattice import Lattice

lattices = pytest.mark.parametrize(
    ("lattice,"),
    [
        pytest.param(LATTICES_ROOT / fn, id=fn.name)
        for fn in LATTICES_ROOT.glob("*.bmad")
        if fn.name not in {"gg.bmad"}
    ],
)


@lattices
def test_bpy_elements_from_tao(lattice: pathlib.Path) -> None:
    with pytao.SubprocessTao(lattice_file=lattice, noplot=True) as tao:
        for ele in bpy_elements_from_tao(tao):
            print(ele)


@lattices
def test_lattice_from_tao(lattice: pathlib.Path) -> None:
    with pytao.SubprocessTao(lattice_file=lattice, noplot=True) as tao:
        lat = Lattice.from_tao(tao)

    lat.to_json("lat.json")
    lat2 = Lattice.from_json("lat.json")

    # Check elements
    for ele1, ele2 in zip(lat.elements, lat2.elements):
        assert ele1 == ele2

    lat.add_elements_to_blender()
    lat.add_tracks_to_blender()


@lattices
def test_render(lattice: pathlib.Path, request: pytest.FixtureRequest) -> None:
    with pytao.SubprocessTao(lattice_file=lattice, noplot=True) as tao:
        eles = bpy_elements_from_tao(tao)

    # This command resets Blender to a new, empty state. The
    # `use_empty=True` parameter ensures that it creates a completely empty
    # file rather than loading the default startup file.
    bpy.ops.wm.read_homefile(use_empty=True)

    add_elements_to_blender(eles, catalogue=pathlib.Path("."))

    # Set up a top-down view
    scene = bpy.context.scene

    bpy.ops.object.camera_add(location=(0, 0, 10))

    camera = bpy.context.active_object
    camera.rotation_euler = (0, 0, 0)
    scene.camera = camera

    # Select all objects to make them visible in camera view
    bpy.ops.object.select_all(action="SELECT")

    # Frame all objects to be visible in the camera view
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            with bpy.context.temp_override(area=area, region=area.regions[-1]):
                bpy.ops.view3d.camera_to_view_selected()

    # Configure render settings
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

    # if "Light" not in bpy.data.objects:
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 10))
    light = bpy.context.active_object
    light.data.energy = 5.0
    light.rotation_euler = camera.rotation_euler

    test_name = request.node.name.replace("[", "_").replace("]", "_")
    output_path = TEST_ARTIFACTS / test_name
    scene.render.filepath = str(output_path.with_suffix(".png"))
    bpy.ops.render.render(write_still=True)

    blend_fn = output_path.with_suffix(".blend")

    if blend_fn.exists():
        blend_fn.unlink()

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_fn))
    print(f"Output saved to {output_path}*")
