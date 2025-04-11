import argparse
import logging
from enum import StrEnum

import numpy as np

# from pytao import Tao
from ..elements import (
    Aperture,
    Bend,
    get_element_class,
    save_elements_to_json,
)
from ..types import ApertureShape

from ..tracks import Track

#
#
# apertures will be separated from elements:
# quad with aperture ->
#     Quadrupole
#     Pipe with parent


# Note that these shou
class EleKey(StrEnum):
    AB_MULTIPOLE = "ab_multipole"
    AC_KICKER = "ac_kicker"
    BEAMBEAM = "beambeam"
    BEGINNING_ELE = "beginning_ele"
    CONVERTER = "converter"
    CRAB_CAVITY = "crab_cavity"
    CUSTOM = "custom"
    DRIFT = "drift"
    E_GUN = "e_gun"
    ECOLLIMATOR = "ecollimator"
    ELSEPARATOR = "elseparator"
    EM_FIELD = "em_field"
    FEEDBACK = "feedback"
    FIDUCIAL = "fiducial"
    FLOOR_SHIFT = "floor_shift"
    FOIL = "foil"
    FORK = "fork"
    GKICKER = "gkicker"
    GROUP = "group"
    HKICKER = "hkicker"
    HYBRID = "hybrid"
    INSTRUMENT = "instrument"
    KICKER = "kicker"
    LCAVITY = "lcavity"
    MARKER = "marker"
    MASK = "mask"
    MATCH = "match"
    MIRROR = "mirror"
    MONITOR = "monitor"
    MULTIPOLE = "multipole"
    NULL_ELE = "null_ele"
    OCTUPOLE = "octupole"
    OVERLAY = "overlay"
    PATCH = "patch"
    PHOTON_FORK = "photon_fork"
    PIPE = "pipe"
    QUADRUPOLE = "quadrupole"
    RCOLLIMATOR = "rcollimator"
    RF_BEND = "rf_bend"
    RFCAVITY = "rfcavity"
    SAD_MULT = "sad_mult"
    SBEND = "sbend"
    SEXTUPOLE = "sextupole"
    SOL_QUAD = "sol_quad"
    SOLENOID = "solenoid"
    TAYLOR = "taylor"
    THICK_MULTIPOLE = "thick_multipole"
    UNDULATOR = "undulator"
    VKICKER = "vkicker"
    WIGGLER = "wiggler"


# Mapping Enum to Class Names
EleKey_TO_CLASSNAME = {
    EleKey.AB_MULTIPOLE: "Multipole",
    EleKey.AC_KICKER: "ACKicker",
    EleKey.BEAMBEAM: "BeamBeam",
    EleKey.BEGINNING_ELE: "BeginningEle",
    EleKey.CONVERTER: "Converter",
    EleKey.CRAB_CAVITY: "CrabCavity",
    EleKey.DRIFT: "Pipe",
    EleKey.E_GUN: "EGun",
    EleKey.ECOLLIMATOR: "Collimator",
    EleKey.ELSEPARATOR: "Instrument",  # TODO
    EleKey.EM_FIELD: "Instrument",  # TODO
    EleKey.FIDUCIAL: "Fiducial",
    EleKey.FLOOR_SHIFT: "FloorShift",
    EleKey.FOIL: "Foil",
    EleKey.FORK: "Fork",
    EleKey.GKICKER: "Kicker",  # TODO
    EleKey.HKICKER: "Kicker",
    EleKey.INSTRUMENT: "Instrument",
    EleKey.KICKER: "Kicker",
    EleKey.LCAVITY: "LCavity",
    EleKey.MARKER: "Marker",
    EleKey.MASK: "Collimator",
    EleKey.MATCH: "Match",
    EleKey.MIRROR: "Mirror",
    EleKey.MONITOR: "Instrument",
    EleKey.MULTIPOLE: "Multipole",
    EleKey.NULL_ELE: "NullEle",
    EleKey.OCTUPOLE: "Octupole",
    EleKey.PATCH: "Patch",
    EleKey.PIPE: "Pipe",
    EleKey.QUADRUPOLE: "Quadrupole",
    EleKey.RCOLLIMATOR: "Collimator",
    EleKey.RFCAVITY: "RFCavity",
    EleKey.SAD_MULT: "Instrument",  # TODO
    EleKey.SBEND: "Bend",
    EleKey.SEXTUPOLE: "Sextupole",
    EleKey.SOLENOID: "Solenoid",
    EleKey.SOL_QUAD: "Instrument",  # TODO
    EleKey.TAYLOR: "Taylor",
    EleKey.THICK_MULTIPOLE: "Multipole",
    EleKey.UNDULATOR: "Undulator",
    EleKey.VKICKER: "Kicker",
    EleKey.WIGGLER: "Undulator",
}


def element_class_from_key(key: EleKey):
    key = EleKey(key)
    if key not in EleKey_TO_CLASSNAME:
        raise NotImplementedError(key)
    return get_element_class(EleKey_TO_CLASSNAME[key])


def get_rvec_wmat(tao, ele_id):
    floor = tao.ele_floor(ele_id)
    rvec = floor["Reference"][0:3]
    wmat = floor["Reference-W"].reshape(3, 3)
    return rvec, wmat


def get_global_orbit(tao, ele_id):
    """
    returns position and momentum vectors in global coordinates


    Returns
    -------
    position: ndarray
        array with [x, y, z] in m
    momentum: ndarray
        momentum with [px, py, pz] in eV/c
    """

    orbit = tao.ele_orbit(ele_id)
    rvec, wmat = get_rvec_wmat(tao, ele_id)

    x, y = orbit["x"], orbit["y"]
    p0c = orbit["p0c"]
    px, py, delta = orbit["px"], orbit["py"], orbit["pz"]  # Bmad coordinates
    # Momenta in eV/c
    pz = np.sqrt((1 + delta) ** 2 - px**2 - py**2) * p0c
    px = px * p0c
    py = py * p0c

    xvec = np.array([x, y, 0])  # z=0 by definition
    pvec = np.array([px, py, pz])

    position = wmat @ xvec + rvec
    momentum = wmat @ pvec

    return position, momentum


def get_ele_data(tao, ele_id):
    """
    Get normalized element data dict from Tao
    """
    info = tao.ele_head(ele_id)
    info.update(tao.ele_gen_attribs(ele_id))
    # info.update(tao.ele_methods)

    # Convert to lower case
    info = {k.lower(): v for k, v in info.items()}
    ix_ele = info["ix_ele"]
    # use EleKey
    key = EleKey(info["key"].lower())
    info["key"] = key

    # Get global floor
    if key == EleKey.MIRROR:
        # Average the floor position vectors
        # Use Reference because of a bug:
        # https://github.com/bmad-sim/bmad-ecosystem/issues/1266
        r = tao.ele_floor(ix_ele, where="end")["Reference"]
        r0 = tao.ele_floor(ix_ele - 1, where="end")["Reference"]  # Previous element
        r = (r + r0) / 2
    else:
        floor = tao.ele_floor(ele_id, where="center")
        # Handle for multipass floor
        if (
            "Actual" not in floor
        ):  # TODO: Actual is better, but if gives the wrong orientation
            r = floor["Actual-Slave1"]
        else:
            r = floor["Actual"]
    x, y, z, theta, phi, psi = r
    info["floor_x"] = x
    info["floor_y"] = y
    info["floor_z"] = z
    info["floor_theta"] = theta
    info["floor_phi"] = phi
    info["floor_psi"] = psi

    # Normalize kicker attributes
    if key == EleKey.HKICKER:
        info["hkick"] = info.pop("kick")
        info["bl_hkick"] = info.pop("bl_kick")
    elif key == EleKey.VKICKER:
        info["vkick"] = info.pop("kick")
        info["bl_vkick"] = info.pop("bl_kick")

    # TODO
    # elif key == EleKey.GKICKER:
    #    print(info)
    #    raise NotImplementedError(key)

    return info


def get_basic_element_kwargs_from_tao_data(data):
    """
    Sets basic element data from tao data.
    """
    descrip = data["descrip"]
    cad_model = descrip.split("3DMODEL=")[-1].split(",")[0]  # Extract before the comma
    if cad_model:
        description = descrip.replace(cad_model, "")
    else:
        description = descrip

    return dict(
        name=str(data["name"]),
        x=float(data["floor_x"]),
        y=float(data["floor_y"]),
        z=float(data["floor_z"]),
        theta=float(data["floor_theta"]),
        phi=float(data["floor_phi"]),
        psi=float(data["floor_psi"]),
        description=description,
        cad_model=cad_model,
    )


def get_aperture_from_tao_data(data):
    """
    Sets Pipe specfic data from tao data
    """

    return Aperture(
        shape=ApertureShape(data["aperture_type"].lower()),
        x1_limit=float(data["x1_limit"]),
        x2_limit=float(data["x2_limit"]),
        y1_limit=float(data["y1_limit"]),
        y2_limit=float(data["y2_limit"]),
        thickness=0.0,  # Not available in Tao
        material="",  # Not available in Tao
    )


def bpy_element_from_tao(tao, ele_id):
    """

    Create elements from a single Tao element.

    Multiple elements are created


    Parameters
    ----------
    tao : pytao.Tao
        running instance of tao

    ele_id : int or str
        Element ID to look up in Tao.
        For Mirror elements, the previous element is used for the floor calc.

    Returns
    -------


    """
    data = get_ele_data(tao, ele_id)
    return bpy_element_from_tao_data(data)


def get_length_from_element(key: EleKey, data):
    if key in (EleKey.BEGINNING_ELE, EleKey.FIDUCIAL):
        return None

    # zero-length elements
    if key in (EleKey.GKICKER,):
        return 1e-6
    if "l" not in data:
        raise AttributeError(f"'l' missing from {key}")

    return data["l"]


def bpy_element_from_tao_data(data):
    # Cast to proper EleKey
    key = EleKey(data["key"])

    # Skip
    if key in (EleKey.OVERLAY,):
        return None

    ele_cls = element_class_from_key(key)
    basic_kw = get_basic_element_kwargs_from_tao_data(data)

    length = get_length_from_element(key, data)

    if length is None:
        return ele_cls(**basic_kw)

    aperture = get_aperture_from_tao_data(data)

    if ele_cls is Bend:
        return ele_cls(
            **basic_kw,
            length=length,
            aperture=aperture,
            curvature=float(data["g"]),
            edge_angle1=float(data["e1"]),
            edge_angle2=float(data["e2"]),
            tilt=float(data["ref_tilt"]),
        )

    return ele_cls(
        **basic_kw,
        length=length,
        aperture=aperture,
    )


def bpy_elements_from_tao(
    tao,
    ele_ids=None,
    add_bend_pipes=True,
):
    if ele_ids is None:
        ele_ids = tao.lat_list("*", "ele.ix_ele", flags="-no_slaves")

    eles = []
    for ele_id in ele_ids:
        # print(ele_id)
        ele = bpy_element_from_tao(tao, ele_id)

        if ele is None:
            continue

        eles.append(ele)

    return eles


def write_bpy_lattice_json(tao, outfile, ele_ids=None):
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

    ele_ids: list of str or int, optional
        List of elements to extract
        Default: None => will match all unique elements of the lattice (i.e., without slaves)


    """
    eles = bpy_elements_from_tao(tao, ele_ids=ele_ids)

    save_elements_to_json(eles, outfile)


def floor_orbit_track_from_tao(
    tao,
    match="*",
    remove_duplicates=True,
    name="orbit",
    weight=0.01,
    color="blue",
):
    """
    Return a Track of the orbit in global coordinates
    """

    xs = tao.lat_list(match, "orbit.floor.x")
    ys = tao.lat_list(match, "orbit.floor.y")
    zs = tao.lat_list(match, "orbit.floor.z")

    # Filter
    if remove_duplicates:
        ss = tao.lat_list(match, "ele.s")
        uix = np.unique(ss, return_index=True)[1]
        xs = xs[uix]
        ys = ys[uix]
        zs = zs[uix]
    return Track(x=xs, y=ys, z=zs, name=name, weight=weight, color=color)


def bmad_to_blender_entrypoint():
    """
    Entry point for generating a lattice JSON from a Bmad lattice file.

    This function parses command-line arguments to specify the lattice file, output file, element list, and verbosity level.
    It initializes an instance of PyTao, processes the lattice data, and writes the output JSON.
    """
    try:
        import pytao
    except ImportError:
        raise RuntimeError(
            "pytao is required to use this entrypoint. Install it with `python -m pip install pytao`"
        )

    parser = argparse.ArgumentParser(description="Generate a lattice JSON from Tao.")

    parser.add_argument("lattice_file", type=str, help="Lattice file path")
    parser.add_argument(
        "outfile",
        type=str,
        nargs="?",
        help="Output JSON file path (default: based on lattice file)",
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
    logger.info("Writing lattice JSON to: %s", outfile)
    write_bpy_lattice_json(tao, outfile, ele_ids=args.elements)
    logger.info("Lattice JSON generation completed successfully.")
