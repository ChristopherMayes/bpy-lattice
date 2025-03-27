from typing import Dict, List

from .named_colors import COLORNAME_VALUES, ColorName


def resolve_color(color):
    """
    Resolves a color value to an (R, G, B, A) tuple.

    Accepts:
    - ColorName enum member
    - Color name string (case-insensitive)
    - Hex string (e.g. "#ff00ff" or "ff00ff")
    - Tuple/list of RGB or RGBA values
    """
    # If it's a ColorName enum member
    if isinstance(color, ColorName):
        return tuple(COLORNAME_VALUES[color])

    # If it's a string
    if isinstance(color, str):
        name = color.lower().strip()
        # Try ColorName enum by value
        try:
            enum_val = ColorName(name)
            return tuple(COLORNAME_VALUES[enum_val])
        except ValueError:
            pass

        # Hex format
        if name.startswith("#"):
            name = name[1:]
        if len(name) in (6, 8):  # RGB or RGBA hex
            try:
                r = int(name[0:2], 16) / 255
                g = int(name[2:4], 16) / 255
                b = int(name[4:6], 16) / 255
                a = 1.0
                if len(name) == 8:
                    a = int(name[6:8], 16) / 255
                return (r, g, b, a)
            except ValueError:
                raise ValueError(f"Invalid hex color string: {color}")

    # If it's a tuple or list
    if isinstance(color, (tuple, list)):
        if len(color) == 3:
            return tuple(color) + (1.0,)  # Add alpha
        elif len(color) == 4:
            return tuple(color)
        else:
            raise ValueError(f"Expected RGB or RGBA tuple, got: {color}")

    raise TypeError(f"Unsupported color format: {color}")


"""
Generate a Python module containing:
- A StrEnum class for CSS4 color names.
- A dictionary mapping enum members to RGBA values.

This script uses matplotlib to fetch CSS4 named colors and converts them
into normalized (0.0–1.0) RGBA values for use in environments without matplotlib.

Output: named_colors.py
"""


def generate_color_enum_and_dict(enum_name: str = "ColorName") -> str:
    """
    Generate Python source code for a StrEnum of CSS4 color names and a dict of RGBA values.

    Args:
        enum_name: The name to give the generated StrEnum class.

    Returns:
        A string containing the full Python source code.
    """
    import matplotlib.colors as mcolors

    all_colors: Dict[str, str] = dict(mcolors.CSS4_COLORS)
    sorted_items = sorted(all_colors.items())  # Sort alphabetically

    lines: List[str] = [
        "# Auto-generated CSS4 color names and RGBA values",
        "from enum import StrEnum",
        "",
        f"class {enum_name}(StrEnum):",
    ]

    for name, _ in sorted_items:
        enum_member = name.upper().replace(" ", "_")
        lines.append(f'    {enum_member} = "{name.lower()}"')

    lines.append("")
    lines.append(f"{enum_name.upper()}_VALUES = {{")

    for name, hex_code in sorted_items:
        enum_member = name.upper().replace(" ", "_")
        rgba = mcolors.to_rgba(hex_code)
        rgba_str = "[" + ", ".join(f"{v:.4f}" for v in rgba) + "]"
        lines.append(f"    {enum_name}.{enum_member}: {rgba_str},")

    lines.append("}")
    lines.append("")  # Final newline
    return "\n".join(lines)


def write_named_colors_py(output_path: str = "named_colors.py") -> None:
    """
    Generate and save the named_colors.py file.

    Args:
        output_path: File path to save the generated Python module.
    """
    code = generate_color_enum_and_dict()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"✅ Generated {output_path} with named color enum and RGBA values.")
