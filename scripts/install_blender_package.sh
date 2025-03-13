#!/bin/bash

# Function to list available Blender versions
list_blender_versions() {
  echo "Available Blender versions:"
  if [ -d "/Applications/Blender.app/Contents/Resources" ]; then
    ls "/Applications/Blender.app/Contents/Resources" | grep -E '^[0-9]+\.[0-9]+$'
  else
    echo "Blender resources directory not found."
  fi
}

# Documentation
show_help() {
  echo "Usage: $0 <blender_version> [--editable]"
  echo
  echo "This script installs bpy-lattice into Blender's Python environment."
  echo
  echo "Arguments:"
  echo "  <blender_version>          The version of Blender to target (e.g., 4.2)."
  echo "  [--editable]               Optional flag to install the package in editable mode."
  echo
  echo "Base Path: $BASE_PATH"
  echo "Modules Path: $MODULES_PATH"
  echo
  echo "Examples:"
  echo "  $0 4.2"
  echo "  $0 4.2 --editable"
  echo
  echo "This script also lists available Blender versions if arguments are missing or incorrect."
}

# Check if at least two arguments are provided
if [ -z "$1" ]; then
  BASE_PATH="/Users/$(whoami)/Library/Application Support/Blender"
  MODULES_PATH="$BASE_PATH/<version>/scripts/modules"
  show_help
  list_blender_versions
  exit 1
fi

BLENDER_VERSION=$1
EDITABLE_FLAG=$2

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
GIT_SOURCE_DIR=$(cd $SCRIPT_DIR/.. && pwd)
BPY_LATTICE_PACKAGE_DIR="$GIT_SOURCE_DIR/bpy_lattice"
BASE_PATH="/Users/$(whoami)/Library/Application Support/Blender/$BLENDER_VERSION"
MODULES_PATH="$BASE_PATH/scripts/modules"
DEST_MODULE_PATH="$BASE_PATH/scripts/modules/bpy_lattice"

# Check if the base path exists
if [ ! -d "$BASE_PATH" ]; then
  echo "Blender version directory does not exist: $BASE_PATH"
  exit 1
fi

# Find the Python executable within the specified Blender version path
BLENDER_APP_PATH="/Applications/Blender.app/Contents/Resources/$BLENDER_VERSION/python/bin"
PYTHON_EXEC=$(find "$BLENDER_APP_PATH" -name "python3.*" 2>/dev/null | head -n 1)

# Check if the Python executable was found
if [ ! -x "$PYTHON_EXEC" ]; then
  echo "Blender Python executable not found for version $BLENDER_VERSION"
  exit 1
fi

# Create the modules directory if it doesn't exist
mkdir -p "$MODULES_PATH"

# Clean previous installations
if [[ -d "$DEST_MODULE_PATH" || -L "$DEST_MODULE_PATH" ]]; then
  rm -rf "$DEST_MODULE_PATH"* "$MODULES_PATH/bin/bmad-to-blender"
  echo "* Cleaned previous installation of bpy-lattice"
fi

# Determine the install command
if [ "$EDITABLE_FLAG" == "--editable" ] || [ "$EDITABLE_FLAG" == "-e" ]; then
  INSTALL_COMMAND="ln -sf \"$BPY_LATTICE_PACKAGE_DIR\" \"$MODULES_PATH\""
else
  INSTALL_COMMAND="$PYTHON_EXEC -m pip install --no-deps --upgrade --target=\"$MODULES_PATH\" \"$GIT_SOURCE_DIR\""
fi

echo "Installing with command: $INSTALL_COMMAND"

# Install the local package directly into Blender's scripts/modules directory
eval $INSTALL_COMMAND || exit

echo "Custom Python package installed into: $MODULES_PATH"
