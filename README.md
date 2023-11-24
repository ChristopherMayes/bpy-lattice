# bpy-lattice
Extensions to Blender to draw accelerator lattices


# Installation into Blender

Blender ships with its own Python. On macOS, this is in a place like:

`/Applications/Blender.app/Contents/Resources/4.0/python/bin/python3.10`

## Users
Most users should install the latest release through PyPI:
`/Applications/Blender.app/Contents/Resources/4.0/python/bin/python3.10 -m pip install bpy-lattice`

## Developers
Developers can clone this repository and install using pip and the editable flag:
`/Applications/Blender.app/Contents/Resources/4.0/python/bin/python3.10 -m pip install --no-dependencies -e .`


# Usage

Open Blender, and choose the scripting tab. 

Paste the contents of `scripts/make_lattice.py` in the editor. Edit to point to a valid `.layout_table` file, and run the script.
