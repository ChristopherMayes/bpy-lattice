import csv
import os
from bpy_lattice.element import (
    Element,
    ApertureType,
    KeyType,
    save_elements_to_csv,
    load_elements_from_csv,
)
import random


def test_element_defaults():
    """Test that an Element initializes with correct default values."""
    elem = Element()
    assert elem.name == ""
    assert elem.x == 0.0
    assert elem.y == 0.0
    assert elem.z == 0.0
    assert elem.theta == 0.0
    assert elem.phi == 0.0
    assert elem.psi == 0.0
    assert elem.cad_model == ""
    assert elem.key == "marker"
    assert elem.L == 0.0
    assert elem.angle == 0.0
    assert elem.e1 == 0.0
    assert elem.e2 == 0.0
    assert elem.aperture_type == ApertureType.RECTANGULAR  # Default Enum
    assert elem.x1_limit == 0.0
    assert elem.x2_limit == 0.0
    assert elem.y1_limit == 0.0
    assert elem.y2_limit == 0.0


def test_element_key_type():
    """Test that the key field enforces valid KeyType values."""
    elem = Element(key=KeyType.DRIFT)
    assert elem.key == KeyType.DRIFT

    elem.key = KeyType.QUADRUPOLE
    assert elem.key == KeyType.QUADRUPOLE


def test_element_aperture_type():
    """Test that the aperture_type field enforces valid values."""
    elem = Element(aperture_type=ApertureType.ELLIPTICAL)
    assert elem.aperture_type == ApertureType.ELLIPTICAL

    elem.aperture_type = ApertureType.WALL3D
    assert elem.aperture_type == ApertureType.WALL3D


def test_csv_save_load():
    """Test saving and loading Element objects to/from a CSV."""
    test_elements = [
        Element(
            name="Elem1", x=1.0, y=2.0, z=3.0, aperture_type=ApertureType.ELLIPTICAL
        ),
        Element(name="Elem2", x=4.0, y=5.0, z=6.0, aperture_type=ApertureType.WALL3D),
    ]

    csv_file = "test_elements.csv"

    # Save elements to CSV
    save_elements_to_csv(test_elements, csv_file)

    # Load elements back from CSV
    loaded_elements = load_elements_from_csv(csv_file)

    assert len(loaded_elements) == len(test_elements)

    for orig, loaded in zip(test_elements, loaded_elements):
        assert orig.name == loaded.name
        assert orig.x == loaded.x
        assert orig.y == loaded.y
        assert orig.z == loaded.z
        assert orig.aperture_type == loaded.aperture_type  # Enum check

    # Clean up
    os.remove(csv_file)


def test_csv_column_shuffling():
    """Test that shuffled CSV columns are still correctly parsed."""
    test_elements = [
        Element(
            name="Elem1", x=1.0, y=2.0, z=3.0, aperture_type=ApertureType.ELLIPTICAL
        ),
        Element(name="Elem2", x=4.0, y=5.0, z=6.0, aperture_type=ApertureType.WALL3D),
    ]

    csv_file = "test_elements.csv"
    shuffled_csv_file = "shuffled_test_elements.csv"

    # Save normally
    save_elements_to_csv(test_elements, csv_file)

    # Shuffle columns
    with open(csv_file, newline="") as f:
        reader = list(csv.reader(f))
        headers, rows = reader[0], reader[1:]

    shuffled_indices = list(range(len(headers)))
    random.shuffle(shuffled_indices)

    shuffled_headers = [headers[i] for i in shuffled_indices]
    shuffled_rows = [[row[i] for i in shuffled_indices] for row in rows]

    with open(shuffled_csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(shuffled_headers)
        writer.writerows(shuffled_rows)

    # Load shuffled CSV
    loaded_elements = load_elements_from_csv(shuffled_csv_file)

    assert len(loaded_elements) == len(test_elements)

    for orig, loaded in zip(test_elements, loaded_elements):
        assert orig.name == loaded.name
        assert orig.x == loaded.x
        assert orig.y == loaded.y
        assert orig.z == loaded.z
        assert orig.key == loaded.key  # Enum chec
        assert orig.aperture_type == loaded.aperture_type  # Enum check

    # Clean up
    os.remove(csv_file)
    os.remove(shuffled_csv_file)
