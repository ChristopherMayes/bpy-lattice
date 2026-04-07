# Command-Line Tools

`bpy-lattice` provides command-line entrypoints for converting Bmad lattice
files without writing any Python.

## `bmad-to-usd`

Export a Bmad lattice to a [USD](https://openusd.org/) file that can be
imported into **Blender**, **NVIDIA Omniverse**, or any USD-compatible
application.

```bash
bmad-to-usd lattice.bmad                 # writes lattice.usda
bmad-to-usd lattice.bmad output.usd      # explicit output path
```

### Options

| Flag | Description |
|---|---|
| `--catalogue PATH` | Directory containing CAD model files (`.blend` / `.usd`). Element `cad_model` paths are resolved relative to this. |
| `--up-axis {Y,Z}` | Stage up-axis. `Y` (default) for Omniverse, `Z` for Blender. |
| `--no-copy-models` | Reference catalogue USD models in place instead of copying them next to the output. |
| `--models-dir PATH` | Directory for converted/copied CAD models (default: `models/` next to output). |
| `--verbose` | Enable verbose logging. |

### Examples

Basic export:

```bash
bmad-to-usd my_ring.bmad
```

With CAD models from a catalogue:

```bash
bmad-to-usd my_ring.bmad --catalogue /path/to/Catalogue
```

Z-up for Blender, referencing models in place:

```bash
bmad-to-usd my_ring.bmad --up-axis Z --catalogue /path/to/Catalogue --no-copy-models
```

---

## `bmad-to-blender`

Export a Bmad lattice to a JSON file that can be loaded by `bpy_lattice`
inside Blender.

```bash
bmad-to-blender lattice.bmad              # writes lattice.json
bmad-to-blender lattice.bmad output.json  # explicit output path
```

### Options

| Flag | Description |
|---|---|
| `--verbose` | Enable verbose logging. |
