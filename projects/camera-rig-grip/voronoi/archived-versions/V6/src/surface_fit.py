#!/usr/bin/env python3
"""
Smooth surface-fit stage for camera-grip-voronoi-adjustable.

Purpose
-------
The canonical ergonomic grip begins as an STL mesh. STL triangles are excellent
for robust boolean/voxel work, but poor for CAD selection because every triangle
is just mesh topology.

This stage samples the actual grip cross-sections and fits a small number of
B-spline/NURBS surface patches around the exterior. The result is exported as:

    assets/smooth/Camera_Right_Grip_SURFACE_FIT.step
    assets/smooth/Camera_Right_Grip_SURFACE_FIT.brep
    assets/smooth/Camera_Right_Grip_SURFACE_FIT_PREVIEW.stl

The STEP/BREP outputs expose meaningful smooth CAD faces, patch-boundary edges,
and vertices. They are reference/reconstruction geometry; they do NOT recover
the original CAD feature history.

Default strategy
----------------
- 8 angular patches around the grip
- 4 vertical Z bands
- shared sample boundaries between adjacent patches
- C2 B-spline fitting
- deterministic sampling
- source STL remains immutable

This is intentionally separate from the Voronoi generation pipeline. The
Voronoi/print geometry should continue to use the canonical STL/voxel pipeline,
while this fitted model is used as a CAD reference for sketches, ShapeBinders,
mounts, and electronics placement.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from trimesh.intersections import mesh_plane

from OCP.gp import gp_Pnt
from OCP.TColgp import TColgp_Array2OfPnt
from OCP.GeomAPI import GeomAPI_PointsToBSplineSurface
from OCP.GeomAbs import GeomAbs_C2
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Compound
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fit smooth B-spline/NURBS patches to the canonical camera-grip STL."
    )
    p.add_argument(
        "--input",
        type=Path,
        default=ROOT / "assets" / "Camera_Right_Grip_MASTER_98mm.stl",
        help="Canonical STL master.",
    )
    p.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "surface_fit.json",
        help="Surface-fit configuration JSON.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "assets" / "smooth",
        help="Destination for STEP/BREP/preview outputs.",
    )
    p.add_argument("--patches", type=int, help="Override angular patch count.")
    p.add_argument("--fit-tolerance", type=float, help="Override 3D fit tolerance in mm.")
    p.add_argument("--preview-only", action="store_true", help="Skip BREP; still writes STEP + preview.")
    return p.parse_args()


def load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text())
    return cfg


def ray_segment_intersection(
    origin: np.ndarray,
    direction: np.ndarray,
    a: np.ndarray,
    b: np.ndarray,
) -> float | None:
    """Return positive ray parameter t for 2D ray/segment intersection."""
    seg = b - a
    mat = np.array(
        [[direction[0], -seg[0]], [direction[1], -seg[1]]],
        dtype=float,
    )
    det = float(np.linalg.det(mat))
    if abs(det) < 1e-10:
        return None

    t, u = np.linalg.solve(mat, a - origin)
    if t >= 0.0 and -1e-8 <= u <= 1.0 + 1e-8:
        return float(t)
    return None


class SectionSampler:
    """
    Cache horizontal mesh sections and sample the outermost boundary radially.

    Using the farthest positive ray hit intentionally follows the outer envelope
    when a cross-section contains a concavity.
    """

    def __init__(self, mesh: trimesh.Trimesh):
        self.mesh = mesh
        self.cache: dict[float, tuple[np.ndarray, np.ndarray]] = {}

    def section(self, z: float) -> tuple[np.ndarray, np.ndarray]:
        key = round(float(z), 6)
        if key in self.cache:
            return self.cache[key]

        segments3 = mesh_plane(
            self.mesh,
            plane_normal=[0.0, 0.0, 1.0],
            plane_origin=[0.0, 0.0, float(z)],
        )
        if len(segments3) == 0:
            raise RuntimeError(f"No mesh section found at Z={z:.4f} mm")

        segments2 = np.asarray(segments3[:, :, :2], dtype=float)
        points2 = segments2.reshape(-1, 2)

        # Section-local center follows the grip as the cross-section shifts.
        center = points2.mean(axis=0)

        self.cache[key] = (segments2, center)
        return self.cache[key]

    def sample(self, z: float, theta: float) -> np.ndarray:
        segments, center = self.section(z)
        direction = np.array([math.cos(theta), math.sin(theta)], dtype=float)

        hits: list[float] = []
        for segment in segments:
            t = ray_segment_intersection(
                center,
                direction,
                segment[0],
                segment[1],
            )
            if t is not None:
                hits.append(t)

        if hits:
            radius = max(hits)
        else:
            # Defensive fallback for numerically awkward section vertices.
            points = segments.reshape(-1, 2)
            radius = float(np.max((points - center) @ direction))

        xy = center + radius * direction
        return np.array([xy[0], xy[1], float(z)], dtype=float)


def build_patch(
    sampler: SectionSampler,
    z0: float,
    z1: float,
    theta0: float,
    theta1: float,
    z_samples: int,
    angular_samples: int,
    degree_min: int,
    degree_max: int,
    tolerance_mm: float,
):
    zs = np.linspace(z0, z1, z_samples)
    angles = np.linspace(theta0, theta1, angular_samples)

    points = TColgp_Array2OfPnt(
        1,
        len(zs),
        1,
        len(angles),
    )

    for i, z in enumerate(zs, start=1):
        for j, theta in enumerate(angles, start=1):
            p = sampler.sample(float(z), float(theta))
            points.SetValue(
                i,
                j,
                gp_Pnt(float(p[0]), float(p[1]), float(p[2])),
            )

    fitter = GeomAPI_PointsToBSplineSurface(
        points,
        int(degree_min),
        int(degree_max),
        GeomAbs_C2,
        float(tolerance_mm),
    )

    surface = fitter.Surface()
    face_maker = BRepBuilderAPI_MakeFace(surface, max(1e-4, tolerance_mm * 0.1))
    if not face_maker.IsDone():
        raise RuntimeError(
            f"Failed to construct surface face for Z={z0:.3f}..{z1:.3f}, "
            f"theta={theta0:.3f}..{theta1:.3f}"
        )
    return face_maker.Face()


def build_surface_fit(mesh: trimesh.Trimesh, cfg: dict):
    patches = int(cfg["angular_patches"])
    z_bands = [float(v) for v in cfg["z_bands_mm"]]

    sampler = SectionSampler(mesh)

    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)

    faces = []
    for band_idx in range(len(z_bands) - 1):
        z0 = z_bands[band_idx]
        z1 = z_bands[band_idx + 1]

        for patch_idx in range(patches):
            theta0 = 2.0 * math.pi * patch_idx / patches
            theta1 = 2.0 * math.pi * (patch_idx + 1) / patches

            face = build_patch(
                sampler=sampler,
                z0=z0,
                z1=z1,
                theta0=theta0,
                theta1=theta1,
                z_samples=int(cfg["z_samples_per_band"]),
                angular_samples=int(cfg["angular_samples_per_patch"]),
                degree_min=int(cfg["degree_min"]),
                degree_max=int(cfg["degree_max"]),
                tolerance_mm=float(cfg["fit_tolerance_mm"]),
            )

            builder.Add(compound, face)
            faces.append(face)

    return compound, faces


def write_step(shape, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    result = writer.Write(str(path))
    if result != IFSelect_RetDone:
        raise RuntimeError(f"STEP export failed: {path}")


def write_brep(shape, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok = BRepTools.Write_s(shape, str(path))
    if ok is False:
        raise RuntimeError(f"BREP export failed: {path}")


def write_preview(step_path: Path, preview_path: Path, tolerance: float) -> None:
    """
    Tessellate the fitted STEP back to STL for quick visual comparison.

    CadQuery is only used for tessellation/export here; the fitting itself uses
    OpenCascade directly.
    """
    import cadquery as cq

    model = cq.importers.importStep(str(step_path))
    cq.exporters.export(
        model,
        str(preview_path),
        tolerance=max(0.05, float(tolerance) * 0.5),
        angularTolerance=0.1,
    )


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    if args.patches is not None:
        cfg["angular_patches"] = args.patches
    if args.fit_tolerance is not None:
        cfg["fit_tolerance_mm"] = args.fit_tolerance

    mesh = trimesh.load(args.input, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"Expected Trimesh, got {type(mesh)!r}")
    if not mesh.is_watertight:
        raise RuntimeError("Input master must be watertight before surface fitting.")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    compound, faces = build_surface_fit(mesh, cfg)

    step_path = args.output_dir / "Camera_Right_Grip_SURFACE_FIT.step"
    brep_path = args.output_dir / "Camera_Right_Grip_SURFACE_FIT.brep"
    preview_path = args.output_dir / "Camera_Right_Grip_SURFACE_FIT_PREVIEW.stl"
    report_path = args.output_dir / "surface_fit_report.json"

    write_step(compound, step_path)
    if not args.preview_only:
        write_brep(compound, brep_path)

    write_preview(
        step_path=step_path,
        preview_path=preview_path,
        tolerance=float(cfg["fit_tolerance_mm"]),
    )

    report = {
        "source": str(args.input),
        "step": str(step_path),
        "brep": None if args.preview_only else str(brep_path),
        "preview_stl": str(preview_path),
        "surface_faces": len(faces),
        "angular_patches": int(cfg["angular_patches"]),
        "z_band_count": len(cfg["z_bands_mm"]) - 1,
        "z_bands_mm": cfg["z_bands_mm"],
        "fit_tolerance_mm": float(cfg["fit_tolerance_mm"]),
        "degree_min": int(cfg["degree_min"]),
        "degree_max": int(cfg["degree_max"]),
        "note": (
            "Smooth fitted reference geometry. This does not reconstruct "
            "the original feature history and is not used as the print master."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2))

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
