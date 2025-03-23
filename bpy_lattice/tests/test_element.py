import pytest
from bpy_lattice.elements import (
    Element,
    Bend,
    BeginningEle,
    get_element_class,
    save_elements_to_json,
    load_elements_from_json,
    CLASS_MAP,
)


def test_to_dict_includes_class():
    e = Element(name="test")
    d = e.to_dict()
    assert d["class"] == "Element"
    assert d["name"] == "test"


def test_from_dict_reconstructs_element():
    d = {"name": "abc", "class": "Element"}
    obj = Element.from_dict(d)
    assert isinstance(obj, Element)
    assert obj.name == "abc"


def test_to_json_and_from_json():
    e = Bend(name="bend1", curvature=0.5)
    json_str = e.to_json()
    new_obj = Bend.from_json(json_str)
    assert isinstance(new_obj, Bend)
    assert new_obj.curvature == 0.5
    assert new_obj.name == "bend1"


def test_abstract_base_instantiation():
    from bpy_lattice.elements import BaseElement

    with pytest.raises(TypeError):
        BaseElement.from_dict({"name": "oops"})


def test_get_element_class_success():
    cls = get_element_class("Bend")
    assert cls is Bend


def test_get_element_class_failure():
    with pytest.raises(ValueError):
        get_element_class("DoesNotExist")


def test_class_map_contains_all_subclasses():
    from bpy_lattice.elements import get_all_subclasses, BaseElement

    subclasses = get_all_subclasses(BaseElement)
    for cls in subclasses:
        assert cls.__name__ in CLASS_MAP


def test_save_and_load_json_roundtrip(tmp_path):
    elements = [Element(name="e1"), Bend(name="bend", curvature=0.1)]
    file = tmp_path / "elements.json"
    save_elements_to_json(elements, file)
    loaded = load_elements_from_json(file)
    assert len(loaded) == 2
    assert isinstance(loaded[0], Element)
    assert isinstance(loaded[1], Bend)
    assert loaded[1].curvature == 0.1


def test_beginning_element_to_object():
    ele = BeginningEle(name="start")
    obj = ele.to_object()
    assert obj is not None  # mock object returned
