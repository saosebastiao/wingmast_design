# ParaView scripts — `paraview/`

Per-export visualization recipes for the VTU files produced by
`examples/`. **Targets ParaView 6.1.1** (any 6.x should work — the
`paraview.simple` API + VTU XML format + preset names used here are
stable across the 6.x series).

The scripts are intentionally short. Each one loads a single VTU,
sets a sensible color map + camera, and either opens an interactive
window or saves a PNG. They're meant to be readable recipes you can
copy into the ParaView GUI's *Python Shell* (View → Python Shell) and
adapt — not a black-box framework.

## Running

ParaView ships its own Python interpreter. Don't use the project's
`uv run python` — the project venv has no `paraview` module.

The `justfile` wraps the common invocations:

```sh
just view shell_fea                                # open interactive window
just view shell_stress_lines                       # surface streamlines on the OML
just shot shell_fea                                # screenshot → docs/figures/shell_fea.png
just shot shell_fea /tmp/foo.png                   # custom output path
just shots                                         # regenerate every screenshot
just pv exports/shell_fea.vtu                      # launch the ParaView GUI
```

If ParaView is installed somewhere other than
`/Applications/ParaView-6.1.1.app/Contents/bin`, override the path on
the command line: `just PV=/usr/local/bin view shell_fea`.

The raw invocations work too:

```sh
PV=/Applications/ParaView-6.1.1.app/Contents/bin
$PV/pvpython paraview/shell_fea.py
$PV/pvbatch paraview/shell_stress_lines.py exports/shell_stress_lines.vtu \
    --screenshot streamlines.png
```

Every script accepts a positional VTU path; if omitted it loads the
matching file from `exports/`. Run with `--help` for per-script flags.

## What each script visualizes

| Script | Default VTU | Phase | Visualization |
|--------|-------------|-------|---------------|
| `fea_volumetric.py` | `fea_<case>.vtu` (default: survival) | 4a | Tet σ_VM with displacement-warped solid |
| `frame_phi.py` | `frame_phi.vtu` | 5b | φ scalar + smoothed eigenvector glyphs on the tet volume |
| `frame_streamlines.py` | `frame_streamlines.vtu` | 5b | Retraced streamlines through the smoothed frame field |
| `stress_lines.py` | `stress_lines.vtu` | 5a | Raw volumetric streamlines per (case × tack × family) |
| `shell_fea.py` | `shell_fea.vtu` | 4b | Shell σ_VM + principal-direction glyphs on the OML |
| `shell_stress_lines.py` | `shell_stress_lines.vtu` | 5e | Surface streamlines on the OML (spar caps) |

> Note: this table lists the scripts **actually present** in `paraview/`. The
> interior-truss / per-region-skin / coupled-frame scripts from the shell-beam era
> (`isocurves`, `sized_truss`, `interior_candidates`, `coupled_shell_frame`,
> `shell_per_region_skin`) were removed and are intentionally absent (re-scope; the
> three standing exports are re-targeted in the plan). `R-GND-8`.

See [`../docs/visualizations.md`](../docs/visualizations.md) for the
**physical interpretation** of each view — what the Michell pattern
should look like, where to expect the spar caps, what σ levels mean
"safe" vs "saturated", etc.

## What lives in `_common.py`

Helpers shared by every script. Read this if you're writing a new
visualization:

- `default_argparser(filename, doc)` — `[vtu] [--screenshot] [--size]`.
- `open_vtu(path)` — `XMLUnstructuredGridReader` + missing-file check.
- `color_by(display, association, field, preset='Cool to Warm')` —
  `ColorBy` + rescale + named preset + scalar bar.
- `glyph_vectors(source, field, scale_factor, every_nth, color)` —
  `Glyph` filter for vector fields (arrows / lines).
- `threshold_between(source, assoc, field, lo, hi)` — `Threshold`
  filter using `LowerThreshold` / `UpperThreshold` (ParaView 6.x API).
- `set_thick_lines(display, width)` — `RenderLinesAsTubes` + width.
- `finish(args, view)` — installs a span-agnostic 3/4 side camera
  (view direction + `ResetCamera` refit to the data bounds), renders,
  and either saves a screenshot or opens an interactive window.

## State files (`.pvsm`)

ParaView's session-state format. Save one via *File → Save State*
after you've tuned a view in the GUI; reload via *File → Load State*.
We don't ship `.pvsm` files because (a) they embed the absolute VTU
path and break if the repo moves and (b) the Python scripts already
encode the recipe in a more portable way. If you want
session-specific tweaks (lights, custom annotations, multi-view
layouts), save your own `.pvsm` once you're happy and commit it next
to the script.

## Limitations

- The camera frames the loaded data at any span (`_wing_side_view`
  sets the view direction and lets `ResetCamera` refit). Glyph
  *density* (`scale_factor` / `every_nth`) is still tuned per script
  and may want adjusting for a wildly different span.
- The scripts assume the VTU file already exists. Run the
  corresponding `examples/NN_<phase>.py` first.
- macOS ParaView prints `[openvkl] INITIALIZATION ERROR: …` on
  startup. That's a missing volume-rendering plugin in the upstream
  build, not our problem; rendering still works.
