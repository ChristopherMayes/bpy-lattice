import pytest

from ..elements import Element, Pipe, Bend, Undulator
from ..lattice import ele_object


@pytest.mark.parametrize("element_class", [Element, Bend, Pipe, Undulator])
def test_ele_object(element_class):
    ele = element_class()
    ele_object(ele)
