"""High-quality CAD render of the conformal multi-cell torsion box (`exports/torsion_box/`).

Run with ParaView's interpreter (NOT the project venv):

    /Applications/ParaView-6.1.1.app/Contents/bin/pvbatch paraview/torsion_box.py --screenshot
    /Applications/ParaView-6.1.1.app/Contents/bin/pvpython paraview/torsion_box.py        # interactive

Loads one STL per part (data-driven from ``manifest.csv``), colours each, and writes four PNGs to
``exports/``: the assembled root segment (shell translucent), an **exploded** view (parts pulled
apart), a **cutaway** (sectioned to reveal the hollow cells), and the **full mast** for context.
This replaces the matplotlib slab plot — real shaded CAD with lighting + feature edges.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paraview.simple import (  # type: ignore[import-not-found]
    Clip,
    GetActiveViewOrCreate,
    Render,
    ResetCamera,
    OpenDataFile,
    SaveScreenshot,
    Show,
    Transform,
)

ROOT = Path(__file__).resolve().parent.parent
PDIR = ROOT / "exports" / "torsion_box"
OUT = ROOT / "exports"

ZTOP = 4.5          # root-segment clip height [m] (covers stock+transition for the continuous build)
DX, DY, DZ = 0.70, 0.62, 1.8     # explode offsets


def read_manifest():
    parts = []
    for line in (PDIR / "manifest.csv").read_text().splitlines()[1:]:
        name, r, g, b, op = line.split(",")
        parts.append((name, (float(r), float(g), float(b)), float(op)))
    return parts


def explode_offset(name: str):
    if name.startswith("cell_LE"):
        return (-DX, 0.0, 0.0)
    if name.startswith("cell_TE"):
        return (DX, 0.0, 0.0)
    if name.startswith("cell_mid"):
        return (0.0, 0.0, 0.0)
    if name.startswith("longeron"):
        top = int(name.split("_")[1]) % 2 == 0
        return (0.0, DY if top else -DY, 0.0)
    if name == "fw_shell":
        return (0.0, 2.0 * DY, 0.0)
    if name == "bearing_stock":
        return (0.0, 0.0, -DZ)
    return (0.0, 0.0, 0.0)


def style(disp, rgb, opacity):
    # plain Surface — the STL is finely tessellated spanwise, so "Surface With Edges" draws a
    # barcode of mesh edges. Clean shaded surfaces + lighting read as CAD; no mesh wireframe.
    disp.Representation = "Surface"
    disp.DiffuseColor = list(rgb)
    disp.AmbientColor = list(rgb)
    disp.Opacity = opacity
    disp.Specular = 0.30
    disp.SpecularPower = 40.0
    disp.Ambient = 0.18
    disp.Diffuse = 0.85


def clip_top(src, z=ZTOP):
    c = Clip(Input=src)
    c.ClipType = "Plane"
    c.ClipType.Origin = [0.0, 0.0, z]
    c.ClipType.Normal = [0.0, 0.0, 1.0]
    c.Invert = 1            # keep z < z
    return c


def clip_half(src, normal=(0.0, 1.0, 0.0)):
    c = Clip(Input=src)
    c.ClipType = "Plane"
    c.ClipType.Origin = [0.0, 0.0, 0.0]
    c.ClipType.Normal = list(normal)
    c.Invert = 1
    return c


def fresh_view(view, size=(1700, 1150)):
    for src in list(view.Representations):
        view.Representations.remove(src)
    view.ViewSize = list(size)
    view.Background = [1.0, 1.0, 1.0]
    view.OrientationAxesVisibility = 0
    view.UseColorPaletteForBackground = 0
    return view


def cam_threequarter(view, direction=(2.4, 1.5, 0.9)):
    # set direction only; ResetCamera recentres focal on the data bounds and fits distance.
    view.CameraViewUp = [0.0, 0.0, 1.0]
    view.CameraFocalPoint = [0.0, 0.0, 0.0]
    view.CameraPosition = list(direction)
    view.CameraParallelProjection = 0
    ResetCamera(view)
    view.CameraViewAngle = 30


def cam_side(view):
    view.CameraViewUp = [0.0, 0.0, 1.0]
    view.CameraFocalPoint = [0.0, 0.0, 0.0]
    view.CameraPosition = [1.0, 0.18, 0.0]
    view.CameraParallelProjection = 1     # orthographic — true profile of the slender mast
    ResetCamera(view)


def save(view, name, args):
    Render(view)
    if args.screenshot:
        path = str(OUT / name)
        SaveScreenshot(path, view, ImageResolution=view.ViewSize)
        print(f"  wrote {path}")


def _detail_parts(parts):
    """Detail views = wing root segment only (drop the bearing stock; it dwarfs the wing)."""
    return [(n, rgb, op) for n, rgb, op in parts if n != "bearing_stock"]


def render_assembly(view, parts, args):
    fresh_view(view)
    for name, rgb, op in _detail_parts(parts):
        src = clip_top(OpenDataFile(str(PDIR / f"{name}.stl")))
        d = Show(src, view)
        style(d, rgb, 0.28 if name == "fw_shell" else op)
    cam_threequarter(view)
    save(view, "torsion_box_assembly.png", args)


def render_exploded(view, parts, args):
    fresh_view(view)
    dp = _detail_parts(parts)
    cells = [p for p in dp if p[0].startswith("cell_")]
    ci = 0
    for name, rgb, op in dp:
        src = clip_top(OpenDataFile(str(PDIR / f"{name}.stl")))
        tr = Transform(Input=src)
        if name.startswith("cell_"):                  # spread all cells evenly along the chord
            tr.Transform.Translate = [(ci - (len(cells) - 1) / 2.0) * DX, 0.0, 0.0]
            ci += 1
        else:
            tr.Transform.Translate = list(explode_offset(name))
        d = Show(tr, view)
        style(d, rgb, 0.4 if name == "fw_shell" else op)
    cam_threequarter(view, direction=(2.4, 1.3, 0.8))
    save(view, "torsion_box_exploded.png", args)


def render_cutaway(view, parts, args):
    fresh_view(view)
    for name, rgb, op in _detail_parts(parts):
        src = clip_half(clip_top(OpenDataFile(str(PDIR / f"{name}.stl"))), (0.0, 1.0, 0.0))
        d = Show(src, view)
        style(d, rgb, op)
    cam_threequarter(view, direction=(1.8, 1.9, 0.9))
    save(view, "torsion_box_cutaway.png", args)


def render_fullmast(view, parts, args):
    fresh_view(view, size=(900, 1500))
    for name, rgb, op in parts:
        rdr = OpenDataFile(str(PDIR / f"{name}.stl"))
        d = Show(rdr, view)
        style(d, rgb, 0.18 if name == "fw_shell" else op)
    cam_side(view)
    save(view, "torsion_box_fullmast.png", args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screenshot", action="store_true", help="save PNGs (else interactive)")
    args = ap.parse_args()
    if not (PDIR / "manifest.csv").exists():
        sys.exit("Run `just example 62_amazon_torsion_box` first (no exports/torsion_box/).")
    parts = read_manifest()
    view = GetActiveViewOrCreate("RenderView")
    print(f"Rendering {len(parts)} parts ...")
    render_assembly(view, parts, args)
    render_exploded(view, parts, args)
    render_cutaway(view, parts, args)
    render_fullmast(view, parts, args)
    if not args.screenshot:
        from paraview.simple import Interact
        Interact()


if __name__ == "__main__":
    main()
