import bpy
import numpy as np
from bpy_lattice.materials import assign_color_material  # Ensure these are imported


def create_curve_from_data(
    x,
    y,
    z,
    name=None,
    weight=1,
    color=None,
) -> bpy.types.Object:
    """
    Create a 3D curve object in Blender from coordinate arrays and assign a colored material.

    This function constructs a Blender curve object using the provided `x`, `y`, `z` coordinate arrays,
    adds bevel thickness based on the `weight`, and assigns a material with the specified `color`.
    The curve is represented as a polyline in 3D space.

    Parameters
    ----------
    x : array-like
        Array of x-coordinates of the curve points.
    y : array-like
        Array of y-coordinates of the curve points.
    z : array-like
        Array of z-coordinates of the curve points.
    name : str, optional
        Name for the created curve object and its material. If None, a default name is used.
    weight : float, default=1
        Thickness of the curve via the bevel depth.
    color : Any, optional
        A color specification passed to `assign_color_material`, such as a name or (R, G, B, A) tuple.

    Returns
    -------
    bpy.types.Object
        The Blender object containing the created 3D curve.

    Raises
    ------
    ValueError
        If the input `x`, `y`, and `z` arrays do not have the same length.

    Notes
    -----
    - The curve uses a 'POLY' spline type, meaning it consists of straight segments.
    - The color is applied using `assign_color_material()` from `bpy_lattice.materials`.
    - The bevel depth controls the curve thickness and can be used to visualize weights.

    Examples
    --------
    >>> obj = create_curve_from_data([0, 1], [0, 1], [0, 1], name="Line", weight=0.1, color="red")
    >>> bpy.context.collection.objects.link(obj)
    """

    # Ensure x, y, z have the same length
    if not (len(x) == len(y) == len(z)):
        raise ValueError("x, y, z arrays must have the same length.")

    # Create a Nx3 numpy array of points
    points = np.column_stack((x, y, z))

    # Create a new curve data block
    curve_data = bpy.data.curves.new(name=f"{name}_curve", type="CURVE")
    curve_data.dimensions = "3D"

    # Add bevel depth for thickness

    curve_data.bevel_depth = (
        weight  # or: np.sqrt(weight) / np.pi # Set cross-sectional area by weight
    )
    curve_data.bevel_resolution = 2  # Smoothness of the curve (higher is smoother)

    # Create a new spline in the curve
    spline = curve_data.splines.new(type="POLY")
    spline.points.add(len(points) - 1)

    # Assign points to the spline
    for i, point in enumerate(points):
        spline.points[i].co = (*point, 1.0)

    # Create a new curve object
    curve_object = bpy.data.objects.new(name if name else "Unnamed_Track", curve_data)

    # Apply Material using your assign_color_material() function
    if color:
        assign_color_material(
            curve_object, color, material_name_prefix=name if name else "Mat"
        )

    return curve_object
