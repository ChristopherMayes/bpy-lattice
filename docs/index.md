# bpy-lattice
Extensions to Blender to draw accelerator lattices


## Installation into Blender

Blender ships with its own Python. On macOS, this is in a place like:

`/Applications/Blender.app/Contents/Resources/4.2/python/bin/python3.11`

This package includes a general installation script for macOS:

```bash
bash scripts/install_blender_package.sh
Usage: scripts/install_blender_package.sh <blender_version> <path_to_local_package> [--editable]

This script installs a local Python package into Blender's Python environment.

Arguments:
  <blender_version>          The version of Blender to target (e.g., 4.2).
  <path_to_local_package>    The path to the local Python package to install.
  [--editable]               Optional flag to install the package in editable mode.

Base Path: /Users/<username>/Library/Application Support/Blender
Modules Path: /Users/<username>/Library/Application Support/Blender/<version>/scripts/modules

Examples:
  scripts/install_blender_package.sh 4.2 /path/to/your/package
  scripts/install_blender_package.sh 4.2 /path/to/your/package --editable

This script also lists available Blender versions if arguments are missing or incorrect.
Available Blender versions:
4.2
```

Note that older installation methods no longer work.


## Usage

Open Blender, and choose the scripting tab.

Paste the contents of `scripts/make_lattice.py` in the editor. Edit to point to a valid `.layout_table` file, and run the script.
