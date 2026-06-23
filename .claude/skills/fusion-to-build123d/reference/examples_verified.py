#!/usr/bin/env python
"""Golden Fusion 360 -> build123d translation idioms, every one executed and
verified against build123d 0.10.0 in this repo's .venv. Run it to see each
idiom produce geometry (and as regression coverage that the API names still
exist after a build123d bump):

    .venv/bin/python .claude/skills/fusion-to-build123d/reference/examples_verified.py

Each example mirrors a kb.md section. The Fusion-side source is in kb.md §5.
"""

from __future__ import annotations

from build123d import *  # noqa: F403 - idiomatic for build123d scripts


def _report(name: str, shape) -> None:
    bb = shape.bounding_box()
    s = bb.size
    print(f"  [{name:24}] vol={shape.volume:10.1f}  "
          f"bbox=({s.X:.1f},{s.Y:.1f},{s.Z:.1f})  solids={len(shape.solids())}")


# 1. Extrude-from-sketch + a bored hole (kb.md §5.1).  Builder and algebra agree.
def extrude_from_sketch():
    length, width, thickness = 80 * MM, 60 * MM, 10 * MM
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            Rectangle(length, width)
        extrude(amount=thickness)
        with BuildSketch(bp.faces().sort_by(Axis.Z)[-1]):   # the top face
            Circle(15 * MM)
        # CUT DIRECTION: negative amount bores DOWN into the plate. A positive
        # amount would extrude away from the solid and remove nothing.
        extrude(amount=-thickness, mode=Mode.SUBTRACT)
    _report("extrude.builder", bp.part)

    part = extrude(Rectangle(length, width), amount=thickness)
    # build123d algebra mode: `-` cut, `*` placement. ty's stubs don't model these operators.
    part -= Plane(part.faces().sort_by(Axis.Z).last) * extrude(Circle(15 * MM), amount=-thickness)  # ty: ignore[unsupported-operator]
    _report("extrude.algebra", part)


# 2. Revolve a profile about an axis (kb.md §5.2).
def revolve_profile():
    with BuildPart() as bp:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline((0, 0), (20, 0), (20, 5), (5, 5), (5, 30), (0, 30), close=True)
            make_face()
        revolve(axis=Axis.Z, revolution_arc=360)            # degrees, not radians
    _report("revolve", bp.part)


# 3. Fillet edges chosen by geometric property, never by raw index (kb.md §5.3, §4.2).
def fillet_selected_edges():
    with BuildPart() as bp:
        Cylinder(radius=20 * MM, height=40 * MM)
        top = bp.faces().sort_by(Axis.Z)[-1]
        fillet(top.edges(), radius=3 * MM)
    _report("fillet.selected", bp.part)


# 4. Boolean cut + chamfer (kb.md §5.4). FeatureOperation Cut -> Mode.SUBTRACT / `-`.
def boolean_cut():
    part = Box(40 * MM, 40 * MM, 20 * MM) - Cylinder(radius=8 * MM, height=20 * MM)
    part = chamfer(part.edges().filter_by(GeomType.CIRCLE), length=2 * MM)
    _report("boolean_cut+chamfer", part)


# 5. Circular pattern via PolarLocations (kb.md §5.5). Builder and algebra agree.
def circular_pattern():
    with BuildPart() as bp:
        Cylinder(radius=50 * MM, height=10 * MM)
        with Locations(bp.faces().sort_by(Axis.Z)[-1]):
            with PolarLocations(radius=40 * MM, count=6):
                Hole(radius=4 * MM)                          # default Mode.SUBTRACT
    _report("polar.builder", bp.part)

    part = Cylinder(radius=50 * MM, height=10 * MM)
    plane = Plane(part.faces().sort_by(Axis.Z).last)
    part -= plane * PolarLocations(radius=40 * MM, count=6) * Hole(radius=4 * MM, depth=10 * MM)  # ty: ignore[unsupported-operator]
    _report("polar.algebra", part)


# 6. Assembly with a revolute joint (kb.md §5.6).
#    VERIFIED RULE: call connect_to on the FIXED joint and pass the MOVING joint's
#    DOF kwarg. `fixed.connect_to(mover, angle=45)` applies the angle;
#    `mover.connect_to(fixed, angle=45)` runs but SILENTLY IGNORES it.
def assembly_with_joint():
    with BuildPart() as base_b:
        Box(60 * MM, 40 * MM, 10 * MM)
        RigidJoint("hinge", joint_location=Location((25 * MM, 0, 10 * MM), (0, 0, 0)))
    base = base_b.part
    base.label = "base"

    with BuildPart() as arm_b:
        Box(50 * MM, 12 * MM, 6 * MM, align=(Align.MIN, Align.CENTER, Align.CENTER))
        RevoluteJoint("pivot", axis=Axis((0, 0, 0), (0, 0, 1)), angular_range=(0, 180))
    arm = arm_b.part
    arm.label = "arm"

    base.joints["hinge"].connect_to(arm.joints["pivot"], angle=45)   # fixed.connect_to(mover, dof)
    assembly = Compound(label="hinge_assembly", children=[base, arm])
    print(f"  [assembly] children={[c.label for c in assembly.children]}  "
          f"arm@45deg bbox.Y=({arm.bounding_box().min.Y:.1f},{arm.bounding_box().max.Y:.1f})")


def main() -> int:
    for fn in (extrude_from_sketch, revolve_profile, fillet_selected_edges,
               boolean_cut, circular_pattern, assembly_with_joint):
        print(fn.__name__)
        fn()
    print("\nall idioms executed OK (build123d 0.10.0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
