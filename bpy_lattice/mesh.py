from typing import List, Tuple
import numpy as np

from mathutils import Matrix, Vector  # must be import after bpy for some reason!


def ellipse_points(
    a: float, b: float, n: int = 30, x: float = 0, a2: float = 0, b2: float = 0
) -> List[Tuple[float, float, float]]:
    """
    Generate a loop of points forming an ellipse in the y-z plane.

    The ellipse allows asymmetric semi-axes for positive and negative y and z values.

    Parameters
    ----------
    a : float
        Semi-major axis for negative y direction (-a).
    b : float
        Semi-minor axis for negative z direction (-b).
    n : int, optional
        Total number of points in the loop (default is 30).
    x : float, optional
        x-coordinate of the section, for positioning in 3D space (default is 0).
    a2 : float, optional
        Semi-major axis for positive y direction. If 0, defaults to `a` (default is 0).
    b2 : float, optional
        Semi-minor axis for positive z direction. If 0, defaults to `b` (default is 0).

    Returns
    -------
    List[Tuple[float, float, float]]
        List of (x, y, z) tuples representing ellipse points in 3D space.
    """
    if not a2:
        a2 = a  # If not provided, assume symmetry
    if not b2:
        b2 = b  # If not provided, assume symmetry

    # Divide n points approximately equally among 4 quadrants
    n_per_quad = [n // 4] * 4  # Evenly distribute
    # for i in range(n % 4):  # Distribute remainder points
    #    n_per_quad[i] += 1

    # Define angles for each quadrant
    theta1 = np.linspace(0, np.pi / 2, n_per_quad[0], endpoint=False)
    theta2 = np.linspace(np.pi / 2, np.pi, n_per_quad[1], endpoint=False)
    theta3 = np.linspace(np.pi, 3 * np.pi / 2, n_per_quad[2], endpoint=False)
    theta4 = np.linspace(3 * np.pi / 2, 2 * np.pi, n_per_quad[3], endpoint=True)

    # Compute (y, z) for each quadrant
    y1, z1 = a2 * np.cos(theta1), b2 * np.sin(theta1)
    y2, z2 = a * np.cos(theta2), b2 * np.sin(theta2)
    y3, z3 = a * np.cos(theta3), b * np.sin(theta3)
    y4, z4 = a2 * np.cos(theta4), b * np.sin(theta4)

    # Combine all quadrants ensuring n total points
    y = np.concatenate([y1, y2, y3, y4])
    z = np.concatenate([z1, z2, z3, z4])

    return [(x, float(y[i]), float(z[i])) for i in range(len(y))]


def rectangle_points(
    a: float, b: float, n: int = 4, x: float = 0, a2: float = None, b2: float = None
) -> List[Tuple[float, float, float]]:
    """
    Generate a rectangular loop of 4 points in the y-z plane, supporting asymmetric semi-axes.

    The rectangle allows for different limits for positive and negative y and z values.

    Parameters
    ----------
    a : float
        Half-width of the rectangle along the negative y direction (-a).
    b : float
        Half-height of the rectangle along the negative z direction (-b).
    n : int, optional
        Ignored (only included for argument consistency with `ellipse_section`).
    x : float, optional
        x-coordinate of the section, for positioning in 3D space (default is 0).
    a2 : float, optional
        Half-width of the rectangle along the positive y direction. If None, defaults to `a` (default is None).
    b2 : float, optional
        Half-height of the rectangle along the positive z direction. If None, defaults to `b` (default is None).

    Returns
    -------
    List[Tuple[float, float, float]]
        List of (x, y, z) tuples representing the four corners of the rectangle in 3D space.
    """
    if a2 is None:
        a2 = a
    if b2 is None:
        b2 = b

    # Define the four corners in (y, z) space
    points = [
        (x, -a, -b),  # Bottom-left
        (x, -a, b2),  # Top-left
        (x, a2, b2),  # Top-right
        (x, a2, -b),  # Bottom-right
    ]

    return points


def revolve_section(
    section,
    s_rel: float,
    g: float = 0,
    e1: float = 0,
    e2: float = 0,
    L: float = 0,
) -> List[Tuple[float, float, float]]:
    """
    Generate a transformed aperture

    Parameters
    ----------
    s_rel : float
        Relative position along the  length (m).
    g : float, optional
        Curvature parameter, defining the radius of bending (default is 0, meaning no curvature).

    Returns
    -------
    List[Tuple[float, float, float]]
        List of (x, y, z) points defining the transformed pipe section.
    """

    # Edge angle (used in bends)
    if L != 0:
        f = s_rel / L + 0.5
        edge = e2 * f + (-1) * e1 * (1 - f)
    else:
        edge = 0

    if g != 0:
        rho = 1 / g
        m0 = Matrix.Rotation(edge, 4, "Z")
        m1 = Matrix.Translation((0, rho, 0))
        m2 = Matrix.Rotation(-g * s_rel, 4, "Z")
        m3 = Matrix.Translation((0, -rho, 0))
        m = m3 @ m2 @ m1 @ m0
    else:
        m0 = Matrix.Rotation(edge, 4, "Z")
        m1 = Matrix.Translation((s_rel, 0, 0))
        m = m1 @ m0

    sec = []
    for p in section:
        v = m @ Vector(p)
        sec.append(v[:])
    return sec


def join_sections(section1, section2):
    """
    Create faces between two consecutive sections.

    Parameters
    ----------
    section1 : List[int]
        Vertex indices for the first section.
    section2 : List[int]
        Vertex indices for the second section.

    Returns
    -------
    List[Tuple[int, int, int, int]]
        List of faces (each defined by four vertex indices).
    """
    faces = []
    n = len(section1)

    for i in range(n):
        v1 = section1[i]
        v2 = section1[(i + 1) % n]  # Wrap-around
        v3 = section2[(i + 1) % n]
        v4 = section2[i]

        faces.append((v1, v4, v3, v2))  # Normal faces outward

    return faces


def build_aperture_mesh(inner_sections):
    """
    Generate a mesh from a series of inner pipe sections.

    Parameters
    ----------
    inner_sections : List[List[Tuple[float, float, float]]]
        List of sections, each containing vertices in (x, y, z) format.

    Returns
    -------
    Tuple[List[Tuple[float, float, float]], List[Tuple[int, int, int, int]]]
        - List of unique vertices.
        - List of faces connecting the sections.
    """
    all_vertices = []
    vertex_index_map = {}

    def add_vertex(vertex):
        """Helper function to ensure unique vertex indexing"""
        index = len(all_vertices)
        all_vertices.append(vertex)
        return index

    # Flatten vertex list and create index mapping
    for section in inner_sections:
        for vertex in section:
            vertex_index_map[vertex] = add_vertex(vertex)

    all_faces = []

    # Create faces by joining sequential sections
    for i in range(len(inner_sections) - 1):
        all_faces.extend(
            join_sections(
                [vertex_index_map[v] for v in inner_sections[i]],
                [vertex_index_map[v] for v in inner_sections[i + 1]],
            )
        )

    return all_vertices, all_faces
