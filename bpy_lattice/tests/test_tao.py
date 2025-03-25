import pathlib

import pytao
import pytest

from ..interfaces.bmad import bpy_elements_from_tao


TESTS_ROOT = pathlib.Path(__file__).resolve().parent
LATTICES_ROOT = TESTS_ROOT / "bmad"


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
    with pytao.SubprocessTao(lattice_file=lattice) as tao:
        for ele in bpy_elements_from_tao(tao):
            print(ele)
