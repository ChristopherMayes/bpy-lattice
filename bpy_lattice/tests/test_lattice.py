from bpy_lattice.lattice import ele_object


def test():
    ele = {
        "name": "test_pipe",
        "radius_x": 0.2,
        "radius_y": 0.1,
        "thickness": 0.01,
        "L": 1,
        "key": "PIPE",
        "descrip": "",
    }
    ele_object(ele, None)
