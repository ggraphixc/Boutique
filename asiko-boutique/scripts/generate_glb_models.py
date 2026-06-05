#!/usr/bin/env python3
"""
GLB Model Generator for ASIKO Boutique Virtual Atelier
Generates minimal valid glTF 2.0 Binary files with embedded geometry and PBR materials.
Uses only Python stdlib (struct, json, math) — no external dependencies.
"""

import struct
import json
import math
import os
import sys
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Garment Geometry Generators
# Each generates a triangulated mesh approximating a specific garment silhouette.
# Returns (positions, normals, indices) tuples.
# ---------------------------------------------------------------------------

def _f3(x, y, z):
    return [float(x), float(y), float(z)]

def _face_normal(v0, v1, v2):
    """Compute normalized face normal for a triangle."""
    nx = (v1[1]-v0[1])*(v2[2]-v0[2]) - (v1[2]-v0[2])*(v2[1]-v0[1])
    ny = (v1[2]-v0[2])*(v2[0]-v0[0]) - (v1[0]-v0[0])*(v2[2]-v0[2])
    nz = (v1[0]-v0[0])*(v2[1]-v0[1]) - (v1[1]-v0[1])*(v2[0]-v0[0])
    length = math.sqrt(nx*nx+ny*ny+nz*nz)
    if length > 0: nx, ny, nz = nx/length, ny/length, nz/length
    return (nx, ny, nz)

def _lathe_profile(profile_points, segments=24):
    """
    Revolve a 2D profile around the Y axis to create a lathed mesh.
    profile_points: list of (x, y) tuples defining the cross-section.
    Returns (positions, normals, indices).
    """
    positions, normals, indices = [], [], []
    n_pts = len(profile_points)
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        next_theta = 2 * math.pi * (i + 1) / segments
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        cos_nt, sin_nt = math.cos(next_theta), math.sin(next_theta)
        for j in range(n_pts - 1):
            x1, y1 = profile_points[j]
            x2, y2 = profile_points[j + 1]
            # Four vertices of the quad strip
            v0 = (x1 * cos_t, y1, x1 * sin_t)
            v1 = (x1 * cos_nt, y1, x1 * sin_nt)
            v2 = (x2 * cos_nt, y2, x2 * sin_nt)
            v3 = (x2 * cos_t, y2, x2 * sin_t)
            # Two triangles per quad
            for tri in [(v0, v1, v2), (v0, v2, v3)]:
                for v in tri:
                    positions.extend(v)
                nx, ny, nz = _face_normal(tri[0], tri[1], tri[2])
                for _ in range(3):
                    normals.extend([nx, ny, nz])
    indices = list(range(len(positions) // 3))
    return positions, normals, indices


def dress_form():
    """Generate a flowing A-line dress silhouette."""
    # Profile: bodice (narrow at top) flares to full skirt
    profile = [
        (0.08, 0.95),   # neck
        (0.20, 0.88),   # shoulder/bust
        (0.18, 0.70),   # waist
        (0.22, 0.55),   # hip
        (0.35, 0.30),   # mid-skirt
        (0.42, 0.05),   # hem
        (0.42, 0.0),    # hem bottom
        (0.0, 0.0),     # center bottom (close)
    ]
    return _lathe_profile(profile, segments=28)


def blazer_form():
    """Generate a structured blazer/ jacket silhouette with broader shoulders."""
    profile = [
        (0.06, 1.05),   # collar top
        (0.12, 1.0),    # collar base
        (0.32, 0.90),   # broad shoulder
        (0.28, 0.75),   # chest
        (0.22, 0.60),   # waist (cinched)
        (0.26, 0.40),   # hip
        (0.30, 0.15),   # hem
        (0.30, 0.0),    # hem bottom
        (0.0, 0.0),
    ]
    return _lathe_profile(profile, segments=24)


def trouser_form():
    """Generate a tapered trouser silhouette with two legs."""
    positions, normals, indices = [], [], []
    segs = 20
    # Left leg
    l_profile = [
        (0.14, 0.55),   # waist left
        (0.16, 0.40),   # hip
        (0.14, 0.25),   # thigh
        (0.10, 0.10),   # calf
        (0.08, 0.0),    # ankle
    ]
    l_pos, l_norm, l_idx = _lathe_profile(l_profile, segs)
    # Offset left leg to the left
    for i in range(0, len(l_pos), 3):
        l_pos[i] -= 0.12  # shift left
        l_pos[i+1] -= 0.05  # lower slightly
    base = len(positions) // 3
    positions.extend(l_pos); normals.extend(l_norm)
    indices.extend([i + base for i in l_idx])

    # Right leg (mirror)
    r_pos, r_norm, r_idx = _lathe_profile(l_profile, segs)
    for i in range(0, len(r_pos), 3):
        r_pos[i] += 0.12  # shift right
        r_pos[i+1] -= 0.05
    base = len(positions) // 3
    positions.extend(r_pos); normals.extend(r_norm)
    indices.extend([i + base for i in r_idx])

    # Waistband connecting both legs
    waist_profile = [
        (0.22, 0.55), (0.18, 0.52), (0.0, 0.50),
        (-0.18, 0.52), (-0.22, 0.55),
    ]
    for i in range(len(waist_profile) - 1):
        x1, y1 = waist_profile[i]
        x2, y2 = waist_profile[i + 1]
        for tri in [
            ((x1, y1, 0.04), (x2, y2, 0.04), (x2, y2, -0.04)),
            ((x1, y1, 0.04), (x2, y2, -0.04), (x1, y1, -0.04)),
        ]:
            for v in tri:
                positions.extend(v)
            nx, ny, nz = _face_normal(tri[0], tri[1], tri[2])
            for _ in range(3): normals.extend([nx, ny, nz])
    # Recompute sequential indices matching full vertex count
    indices = list(range(len(positions) // 3))
    return positions, normals, indices


def top_form():
    """Generate a structured shell top with defined shoulders."""
    profile = [
        (0.05, 1.0),    # neck
        (0.24, 0.92),   # shoulder
        (0.22, 0.80),   # upper chest
        (0.20, 0.65),   # mid torso
        (0.18, 0.50),   # waist
        (0.18, 0.0),    # hem
    (0.0, 0.0),     # center bottom (close)
    ]
    return _lathe_profile(profile, segments=22)


def draped_gown_form():
    """Generate an elegant floor-length draped gown silhouette."""
    profile = [
        (0.06, 1.10),   # neck
        (0.18, 1.02),   # bust
        (0.14, 0.85),   # waist (cinched)
        (0.20, 0.65),   # hip
        (0.30, 0.40),   # mid gown
        (0.40, 0.15),   # lower gown
        (0.45, 0.02),   # hem
        (0.0, 0.0),
    ]
    return _lathe_profile(profile, segments=30)


def structural_top_form():
    """Generate an avant-garde structural top with asymmetric geometry."""
    positions, normals, indices = [], [], []
    segs = 20
    # Main torso with slight asymmetry
    for i in range(segs):
        theta = 2 * math.pi * i / segs
        nt = 2 * math.pi * (i + 1) / segs
        # Asymmetric scaling: bulge more on one side
        asym = 1.0 + 0.15 * math.cos(theta)
        asym_n = 1.0 + 0.15 * math.cos(nt)
        h = 0.75
        # Vertical profile
        y_vals = [0.0, 0.15, 0.30, 0.50, 0.65, 0.75]
        r_vals = [0.18, 0.20, 0.22, 0.24, 0.20, 0.10]
        for j in range(len(y_vals) - 1):
            y1, y2 = y_vals[j], y_vals[j+1]
            r1, r2 = r_vals[j] * asym, r_vals[j+1] * asym_n
            v0 = (r1 * math.cos(theta), y1, r1 * math.sin(theta))
            v1 = (r2 * math.cos(nt), y2, r2 * math.sin(nt))
            v2 = (r1 * math.cos(nt), y1, r1 * math.sin(nt))
            v3 = (r2 * math.cos(theta), y2, r2 * math.sin(theta))
            for tri in [(v0, v2, v1), (v0, v1, v3)]:
                for v in tri: positions.extend(v)
                nx, ny, nz = _face_normal(tri[0], tri[1], tri[2])
                for _ in range(3): normals.extend([nx, ny, nz])
    indices = list(range(len(positions) // 3))
    return positions, normals, indices


def cyber_blazer_form():
    """Generate a futuristic cyber-blazer with sharp angular shoulders."""
    positions, normals, indices = [], [], []
    segs = 22
    # Add exaggerated shoulder pads at specific angles
    for i in range(segs):
        theta = 2 * math.pi * i / segs
        nt = 2 * math.pi * (i + 1) / segs
        # Shoulder pad bulge at 45 deg angles
        shoulder = 1.0 + 0.25 * (max(0, math.cos(theta - 0.8))**8 + max(0, math.cos(theta - 2.3))**8)
        shoulder_n = 1.0 + 0.25 * (max(0, math.cos(nt - 0.8))**8 + max(0, math.cos(nt - 2.3))**8)
        # Vertical profile with cinched waist
        y_vals = [0.0, 0.10, 0.30, 0.50, 0.65, 0.82, 0.92, 1.0]
        r_vals = [0.28, 0.30, 0.28, 0.22, 0.26, 0.32, 0.28, 0.12]
        for j in range(len(y_vals) - 1):
            y1, y2 = y_vals[j], y_vals[j+1]
            r1, r2 = r_vals[j] * shoulder, r_vals[j+1] * shoulder_n
            v0 = (r1 * math.cos(theta), y1, r1 * math.sin(theta))
            v1 = (r2 * math.cos(nt), y2, r2 * math.sin(nt))
            v2 = (r1 * math.cos(nt), y1, r1 * math.sin(nt))
            v3 = (r2 * math.cos(theta), y2, r2 * math.sin(theta))
            for tri in [(v0, v2, v1), (v0, v1, v3)]:
                for v in tri: positions.extend(v)
                nx, ny, nz = _face_normal(tri[0], tri[1], tri[2])
                for _ in range(3): normals.extend([nx, ny, nz])
    indices = list(range(len(positions) // 3))
    return positions, normals, indices


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

MODELS = {
    # Showroom items
    "architectural-blazer": {
        "shape": "blazer",
        "color": [0.05, 0.16, 0.13],       # #0D2A22
        "emissive": [0.05, 0.16, 0.13],
        "metalness": 0.3,
        "roughness": 0.4,
        "scale": 0.65,
    },
    "draped-silhouette-gown": {
        "shape": "draped_gown",
        "color": [0.10, 0.10, 0.18],       # #1a1a2e
        "emissive": [0.29, 0.29, 0.56],
        "metalness": 0.1,
        "roughness": 0.5,
        "scale": 0.6,
    },
    "tailored-column-trouser": {
        "shape": "trouser",
        "color": [0.91, 0.84, 0.75],       # #e8d5c0
        "emissive": [0.77, 0.64, 0.35],
        "metalness": 0.0,
        "roughness": 0.7,
        "scale": 0.7,
    },
    # Dressing room items
    "mesh_dress_lux": {
        "shape": "dress",
        "color": [0.10, 0.10, 0.18],       # #1a1a2e
        "emissive": [0.29, 0.29, 0.56],
        "metalness": 0.1,
        "roughness": 0.4,
        "scale": 0.6,
    },
    "mesh_jacket_cyber": {
        "shape": "cyber_blazer",
        "color": [0.05, 0.29, 0.23],       # #0D4A3A
        "emissive": [0.13, 0.83, 0.93],
        "metalness": 0.4,
        "roughness": 0.3,
        "scale": 0.55,
    },
    "mesh_trouser_tapered": {
        "shape": "trouser",
        "color": [0.91, 0.84, 0.75],       # #e8d5c0
        "emissive": [0.77, 0.64, 0.35],
        "metalness": 0.0,
        "roughness": 0.7,
        "scale": 0.65,
    },
    "mesh_top_structural": {
        "shape": "structural_top",
        "color": [0.77, 0.64, 0.35],       # #c4a35a
        "emissive": [0.83, 0.69, 0.22],
        "metalness": 0.2,
        "roughness": 0.5,
        "scale": 0.55,
    },
}

SHAPE_FUNCS = {
    "dress": dress_form,
    "blazer": blazer_form,
    "trouser": trouser_form,
    "top": top_form,
    "draped_gown": draped_gown_form,
    "structural_top": structural_top_form,
    "cyber_blazer": cyber_blazer_form,
}


# ---------------------------------------------------------------------------
# GLB Writer
# ---------------------------------------------------------------------------

def write_glb(output_path: str, positions: List[float], normals: List[float],
              indices: List[int], color: List[float], emissive: List[float],
              metalness: float, roughness: float, scale: float = 1.0) -> None:
    """
    Write a minimal valid glTF 2.0 Binary (.glb) file.

    Structure:
      [12-byte header]
      [JSON chunk]  (chunkLength + chunkType + chunkData)
      [BIN chunk]   (chunkLength + chunkType + chunkData)
    """
    # Apply scale to positions
    scaled_positions = []
    for i in range(0, len(positions), 3):
        scaled_positions.extend([positions[i] * scale, positions[i+1] * scale, positions[i+2] * scale])

    # Pack data into buffer
    buf = bytearray()
    # Positions: float32 x 3 per vertex
    for i in range(0, len(scaled_positions), 3):
        buf.extend(struct.pack('<fff', scaled_positions[i], scaled_positions[i+1], scaled_positions[i+2]))
    # Normals: float32 x 3 per vertex
    for i in range(0, len(normals), 3):
        buf.extend(struct.pack('<fff', normals[i], normals[i+1], normals[i+2]))
    # Indices: uint16 per index
    for idx in indices:
        buf.extend(struct.pack('<H', idx))

    vertex_count = len(scaled_positions) // 3
    byte_offset_positions = 0
    byte_offset_normals = vertex_count * 3 * 4  # after positions
    byte_offset_indices = vertex_count * 6 * 4  # after positions + normals

    # Build glTF JSON
    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "ASIKO GLB Generator"
        },
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{
            "mesh": 0,
            "rotation": [0.7071, 0.0, 0.0, 0.7071],  # 90 deg tilt for visual interest
        }],
        "meshes": [{
            "primitives": [{
                "attributes": {
                    "POSITION": 0,
                    "NORMAL": 1,
                },
                "indices": 2,
                "material": 0,
            }]
        }],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,  # FLOAT
                "count": vertex_count,
                "type": "VEC3",
                "min": [
                    min(scaled_positions[i] for i in range(0, len(scaled_positions), 3)),
                    min(scaled_positions[i] for i in range(1, len(scaled_positions), 3)),
                    min(scaled_positions[i] for i in range(2, len(scaled_positions), 3)),
                ],
                "max": [
                    max(scaled_positions[i] for i in range(0, len(scaled_positions), 3)),
                    max(scaled_positions[i] for i in range(1, len(scaled_positions), 3)),
                    max(scaled_positions[i] for i in range(2, len(scaled_positions), 3)),
                ],
            },
            {
                "bufferView": 1,
                "componentType": 5126,  # FLOAT
                "count": vertex_count,
                "type": "VEC3",
            },
            {
                "bufferView": 2,
                "componentType": 5123,  # UNSIGNED_SHORT
                "count": len(indices),
                "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": byte_offset_positions,
                "byteLength": vertex_count * 3 * 4,
                "target": 34962,  # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": byte_offset_normals,
                "byteLength": vertex_count * 3 * 4,
                "target": 34962,  # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": byte_offset_indices,
                "byteLength": len(indices) * 2,
                "target": 34963,  # ELEMENT_ARRAY_BUFFER
            },
        ],
        "buffers": [{
            "byteLength": len(buf),
        }],
        "materials": [{
            "pbrMetallicRoughness": {
                "baseColorFactor": color + [1.0],
                "metallicFactor": metalness,
                "roughnessFactor": roughness,
            },
            "emissiveFactor": emissive,
            "name": "ASIKO Atelier Material",
        }],
    }

    json_str = json.dumps(gltf, separators=(',', ':'))
    # Pad JSON to 4-byte alignment
    json_padding = (4 - len(json_str) % 4) % 4
    json_bytes = json_str.encode('utf-8') + b' ' * json_padding

    # Pad BIN to 4-byte alignment
    bin_padding = (4 - len(buf) % 4) % 4
    buf += b'\x00' * bin_padding

    # Compute total length
    json_chunk_length = len(json_bytes)
    bin_chunk_length = len(buf)
    total_length = 12 + 8 + json_chunk_length + 8 + bin_chunk_length

    with open(output_path, 'wb') as f:
        # Header
        f.write(struct.pack('<I', 0x46546C67))  # magic: "glTF"
        f.write(struct.pack('<I', 2))            # version: 2
        f.write(struct.pack('<I', total_length)) # length

        # JSON chunk
        f.write(struct.pack('<I', json_chunk_length))
        f.write(struct.pack('<I', 0x4E4F534A))  # "JSON"
        f.write(json_bytes)

        # BIN chunk
        f.write(struct.pack('<I', bin_chunk_length))
        f.write(struct.pack('<I', 0x004E4942))  # "BIN\0"
        f.write(bytes(buf))

    print(f"  [OK] {os.path.basename(output_path)} ({total_length} bytes, {vertex_count} vertices, {len(indices)} indices)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "models")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Generating GLB models in: {output_dir}")
    print()

    total = 0
    for name, config in MODELS.items():
        shape_func = SHAPE_FUNCS.get(config["shape"])
        if not shape_func:
            print(f"  ✗ Unknown shape '{config['shape']}' for {name}")
            continue

        positions, normals, indices = shape_func()
        output_path = os.path.join(output_dir, f"{name}.glb")
        write_glb(
            output_path=output_path,
            positions=positions,
            normals=normals,
            indices=indices,
            color=config["color"],
            emissive=config["emissive"],
            metalness=config["metalness"],
            roughness=config["roughness"],
            scale=config["scale"],
        )
        total += 1

    print(f"\n[DONE] Generated {total} GLB model files.")
    print(f"\nNext: Place real .glb exports in static/models/ to override these placeholders.")


if __name__ == "__main__":
    main()
