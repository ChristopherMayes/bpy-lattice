from bpy_lattice.lattice import ele_object
from bpy_lattice.elements import Element, SBend, Pipe, Wiggler


def test_ele_object():
    for ele in (Element(), SBend(), Pipe(), Wiggler()):
        ele = Element()
        ele_object(ele, None)
