import argparse
import logging
# from pytao import Tao


def bpy_lattice_line_from_tao(tao, ele_id):
    """
    Parameters
    ----------
    tao : pytao.Tao
        running instance of tao

    ele_id : int or str
        Element ID to look up in Tao.
        For Mirror elements, the previous element is used for the floor calc.

    Returns
    -------
    line: str
        comma separated line that the bpy_lattice package expects

    """
    head = tao.ele_head(ele_id)
    descrip = head["descrip"]
    ix_ele = head["ix_ele"]
    name = head["name"]
    key = head["key"].upper()

    # Ignore these elements
    if key in (
        "BEGINNING_ELE",
        "PATCH",
        "MATCH",
        "NULL_ELE",
        "FLOOR_SHIFT",
        "GKICKER",
        "GROUP",
        "OVERLAY",
        "FORK",
        "PHOTON_FORK",
    ):
        return None

    floor = tao.ele_floor(ele_id, where="center")
    attrs = tao.ele_gen_attribs(ele_id)

    # Defaults
    if "L" not in attrs:
        print(name, attrs)
    L = attrs["L"]

    # Handle for multipass floor
    if (
        "Actual" not in floor
    ):  # TODO: Actual is better, but if gives the wrong orientation
        r = floor["Actual-Slave1"]
    else:
        r = floor["Actual"]

    custom1 = 0
    custom2 = 0
    custom3 = 0

    if key == "MIRROR":
        # Average the floor position vectors
        # Use Reference because of a bug:
        # https://github.com/bmad-sim/bmad-ecosystem/issues/1266
        r = tao.ele_floor(ele_id, where="end")["Reference"]
        r0 = tao.ele_floor(ix_ele - 1, where="end")["Reference"]  # Previous element
        r = (r + r0) / 2
        key = "MARKER"  # TODO: enable Mirror in bpy-lattice.
        if L == 0:
            L = 0.001

    elif key in ("PIPE",):
        custom1 = attrs["X1_LIMIT"]
        custom2 = attrs["Y1_LIMIT"]
        custom3 = 0.002
    elif key == "SBEND":
        L = attrs["L"]
        custom1 = attrs["ANGLE"]
        custom2 = attrs["E1"]
        custom3 = attrs["E2"]
    elif key in (
        "CRYSTAL",
        "DETECTOR",
        "MIRROR",
        "MULTILAYER_MIRROR",
        "DIFFRACTION_PLATE",
        "MASK",
    ):
        custom1 = attrs["X1_LIMIT"]
        custom2 = attrs["Y1_LIMIT"]
        custom3 = 0.001

    x, y, z, theta, phi, psi = r

    line = f"{name}, {ix_ele}, {x}, {y}, {z}, {theta} ,{phi}, {psi}, {key}, {L}, {custom1}, {custom2}, {custom3}, {descrip}"
    return line


def write_bpy_lattice_csv(tao, outfile, ele_list=None):
    """
    This writes the `.layout_table` style file that the
    bmad_to_blender Fortran program creates for bpy_lattice

    Notes
    -----
    This is intended to replace the functionality of:
    https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/interface/blender_interface_mod.f90

    Parameters
    ----------
    tao: PyTao.tao
        running instance of tao

    outfile: str
        File to write to

    ele_list: list of str or int, optional
        List of elements to extract
        Default: None => will match all unique elements of the lattice (i.e., without slaves)


    """

    if ele_list is None:
        ele_list = tao.lat_list("*", "ele.ix_ele", flags="-no_slaves")

    header = "# ele_name, ix_ele, x, y, z, theta ,phi, psi, key, L, custom1, custom2, custom3, descrip"

    with open(outfile, "w") as f:
        f.write(header + "\n")
        for name in ele_list:
            line = bpy_lattice_line_from_tao(tao, name)
            if line is not None:
                print(line, file=f)


def bmad_to_blender_entrypoint():
    """
    Entry point for generating a lattice CSV from a Bmad lattice file.

    This function parses command-line arguments to specify the lattice file, output file, element list, and verbosity level.
    It initializes an instance of PyTao, processes the lattice data, and writes the output CSV.
    """
    try:
        import pytao
    except ImportError:
        raise RuntimeError(
            "pytao is required to use this entrypoint. Install it with `python -m pip install pytao`"
        )

    parser = argparse.ArgumentParser(description="Generate a lattice CSV from Tao.")

    parser.add_argument("lattice_file", type=str, help="Lattice file path")
    parser.add_argument(
        "outfile",
        type=str,
        nargs="?",
        help="Output CSV file path (default: based on lattice file)",
    )
    parser.add_argument(
        "--elements",
        type=int,
        nargs="+",
        default=None,
        help="List of element IDs to extract (default: all elements)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Set up logging
    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    # Determine output file name if not provided
    if args.outfile is None:
        if args.lattice_file.endswith(".bmad"):
            outfile = args.lattice_file.replace(".bmad", ".layout_table")
        else:
            outfile = f"{args.lattice_file}.layout_table"
    else:
        outfile = args.outfile

    # Create a running instance of PyTao
    logger.info("Initializing Tao with lattice file: %s", args.lattice_file)
    tao = pytao.Tao(lattice_file=args.lattice_file, noplot=True)

    # Call the function to write the CSV
    logger.info("Writing lattice CSV to: %s", outfile)
    write_bpy_lattice_csv(tao, outfile, ele_list=args.elements)
    logger.info("Lattice CSV generation completed successfully.")
