from unittest.mock import Mock

import pytest

from bpy_lattice.elements import (
    CLASS_MAP,
    BaseElement,
    BeamElement,
    BeginningEle,
    Bend,
    Element,
    get_all_subclasses,
    get_element_class,
    load_elements_from_json,
    save_elements_to_json,
    load_elements_from_csv,
    save_elements_to_csv,
)


def test_to_dict_includes_class():
    e = Element(name="test")
    d = e.to_dict()
    assert d["class"] == "Element"
    assert d["name"] == "test"


def test_from_dict_reconstructs_element():
    d = {"name": "abc", "x": "3", "class": "Element"}
    obj = BaseElement.from_dict(d)
    assert isinstance(obj, Element)
    assert obj.name == "abc"
    assert obj.x == 3.0


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
    subclasses = get_all_subclasses(BaseElement)
    for cls in subclasses:
        assert cls.__name__ in CLASS_MAP


element_classees = pytest.mark.parametrize(
    ("cls",),
    [
        pytest.param(cls, id=cls.__name__)
        for cls in sorted(
            BaseElement.available_classes().values(), key=lambda cls: cls.__name__
        )
        if cls not in {BaseElement}
    ],
)

beam_element_classees = pytest.mark.parametrize(
    ("cls",),
    [
        pytest.param(cls, id=cls.__name__)
        for cls in sorted(
            BaseElement.available_classes().values(), key=lambda cls: cls.__name__
        )
        if issubclass(cls, BeamElement)
    ],
)


@element_classees
def test_default_instantiate(cls: type[BaseElement]) -> None:
    cls()


@element_classees
def test_dict_roundtrip(cls: type[BaseElement]) -> None:
    instance = cls()
    data = instance.to_dict()
    result = BaseElement.from_dict(data)
    assert instance == result


@element_classees
def test_json_roundtrip(cls: type[BaseElement]) -> None:
    instance = cls()
    data = instance.to_json()
    result = BaseElement.from_json(data)
    assert instance == result


@beam_element_classees
def test_align_object_location_and_rotation(cls: type[BeamElement]) -> None:
    obj = Mock()

    instance = cls()
    instance.align_object_location_and_rotation(obj)
    assert obj.rotation_euler.z == instance.theta
    assert obj.rotation_euler.y == -instance.phi
    assert obj.rotation_euler.x == instance.psi
    assert obj.location == (instance.z, instance.x, instance.y)


@beam_element_classees
def test_to_object_smoke(cls: type[BeamElement]) -> None:
    instance = cls()
    instance.to_empty_object()
    instance.to_object()
    instance.to_basic_object()
    instance.aperture_object()


def test_save_and_load_json_roundtrip(tmp_path) -> None:
    elements = [Element(name="e1"), Bend(name="bend", curvature=0.1)]
    file = tmp_path / "elements.json"
    save_elements_to_json(elements, file)
    loaded = load_elements_from_json(file)
    assert len(loaded) == 2
    assert isinstance(loaded[0], Element)
    assert isinstance(loaded[1], Bend)
    assert loaded[1].curvature == 0.1


def test_save_and_load_csv_roundtrip(tmp_path) -> None:
    elements = [Element(name="e1"), Bend(name="bend", curvature=0.1)]
    file = tmp_path / "elements.csv"
    save_elements_to_csv(elements, file)

    print("CSV contents:")
    with open(file) as fp:
        print(fp.read())
    print("---")

    loaded = load_elements_from_csv(file)
    assert len(loaded) == 2
    assert isinstance(loaded[0], Element)
    assert isinstance(loaded[1], Bend)
    assert loaded[1].curvature == 0.1


def test_beginning_element_to_object():
    ele = BeginningEle(name="start")
    obj = ele.to_object()
    assert obj is not None  # mock object returned
