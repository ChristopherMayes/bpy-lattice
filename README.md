# bpy-lattice
Extensions to Blender to draw accelerator lattices


# Installation into Blender

Blender ships with its own Python. On macOS, this is in a place like:

`/Applications/Blender.app/Contents/Resources/2.83/python/bin/python3.7m`

Developers can install using pip and the editable flag:

`/Applications/Blender.app/Contents/Resources/2.83/python/bin/python3.7m -m pip install -e .`


# Usage

Open Blender, and choose the scripting tab. 

Paste the contents of `scriots/make_lattice.py` in the editor. Edit to point to a valid `.layout_table` file, and run the script.
