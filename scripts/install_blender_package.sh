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
  echo "Usage: $0 <blender_version> <path_to_local_package> [--editable]"
  echo
  echo "This script installs a local Python package into Blender's Python environment."
  echo
  echo "Arguments:"
  echo "  <blender_version>          The version of Blender to target (e.g., 4.2)."
  echo "  <path_to_local_package>    The path to the local Python package to install."
  echo "  [--editable]               Optional flag to install the package in editable mode."
  echo
  echo "Base Path: $BASE_PATH"
  echo "Modules Path: $MODULES_PATH"
  echo
  echo "Examples:"
  echo "  $0 4.2 /path/to/your/package"
  echo "  $0 4.2 /path/to/your/package --editable"
  echo
  echo "This script also lists available Blender versions if arguments are missing or incorrect."
}

# Check if at least two arguments are provided
if [ -z "$1" ] || [ -z "$2" ]; then
  BASE_PATH="/Users/$(whoami)/Library/Application Support/Blender"
  MODULES_PATH="$BASE_PATH/<version>/scripts/modules"
  show_help
  list_blender_versions
  exit 1
fi

BLENDER_VERSION=$1
PACKAGE_PATH=$2
EDITABLE_FLAG=$3
BASE_PATH="/Users/$(whoami)/Library/Application Support/Blender/$BLENDER_VERSION"
MODULES_PATH="$BASE_PATH/scripts/modules"

# Check if the base path exists
if [ ! -d "$BASE_PATH" ]; then
  echo "Blender version directory does not exist: $BASE_PATH"
  exit 1
fi

# Create the modules directory if it doesn't exist
mkdir -p "$MODULES_PATH"

# Find the Python executable within the specified Blender version path
BLENDER_APP_PATH="/Applications/Blender.app/Contents/Resources/$BLENDER_VERSION/python/bin"
PYTHON_EXEC=$(find "$BLENDER_APP_PATH" -name "python3.*" 2>/dev/null | head -n 1)

# Check if the Python executable was found
if [ -z "$PYTHON_EXEC" ]; then
  echo "Blender Python executable not found for version $BLENDER_VERSION"
  exit 1
fi

# Ensure pip is available
"$PYTHON_EXEC" -m ensurepip

# Upgrade pip to the latest version
"$PYTHON_EXEC" -m pip install --upgrade pip

# Determine the install command
if [ "$EDITABLE_FLAG" == "--editable" ]; then
  INSTALL_COMMAND="$PYTHON_EXEC -m pip install -e --target=\"$MODULES_PATH\" \"$PACKAGE_PATH\""
else
  INSTALL_COMMAND="$PYTHON_EXEC -m pip install --target=\"$MODULES_PATH\" \"$PACKAGE_PATH\""
fi

# Install the local package directly into Blender's scripts/modules directory
eval $INSTALL_COMMAND

echo "Custom Python package installed into: $MODULES_PATH"
