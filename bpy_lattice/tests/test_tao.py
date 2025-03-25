import pathlib

import bpy
import pytao
import pytest

from .conftest import LATTICES_ROOT, TEST_ARTIFACTS
from ..interfaces.bmad import bpy_elements_from_tao
from ..blend import add_elements_to_blender


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

        # Create camera if it doesn't exist
        if "Camera" not in bpy.data.objects:
            bpy.ops.object.camera_add(location=(0, 0, 10))

        camera = bpy.data.objects["Camera"]

        # Set camera to top-down view
        camera.location = (0, 0, 10)
        # Ensure the camera is looking down
        camera.rotation_euler = (0, 0, 0)

        # Set the camera as the active camera
        scene.camera = camera

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
        bpy.ops.wm.save_as_mainfile(filepath=str(output_path.with_suffix(".blend")))
        print(f"Output saved to {output_path}*")
