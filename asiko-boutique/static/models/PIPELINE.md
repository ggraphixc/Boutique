# ASIKO Atelier — 3D Garment Model Pipeline

This document describes how to replace the procedural placeholder GLB models with real 3D-scanned or professionally modeled garments.

---

## Current State

The `static/models/` directory contains procedurally generated GLB files that approximate garment silhouettes (dress, blazer, trouser, top) using lathed geometry. These are **placeholders** — they lack fabric drape, stitching, texture maps, and realistic topology.

## Goal

Replace each `.glb` file with a production-quality 3D garment model suitable for real-time rendering in the Three.js virtual atelier.

---

## Model Requirements

| Requirement | Specification |
|-------------|---------------|
| Format | glTF 2.0 Binary (.glb) |
| Max file size | 2 MB per garment (target: <500 KB) |
| Max triangle count | 50,000 per garment (target: <15,000) |
| PBR materials | Standard roughness/metalness workflow |
| Textures | Embedded or separate (PNG/JPEG, max 2048×2048) |
| Skeleton | Only if using morph targets; no animation rigs needed |
| Scale | 1 unit ≈ 1 meter; garments should fit within a 0.6m bounding box |
| Origin | Centered at hip/waist level (y=0 at waist) |
| Orientation | Y-up, facing +Z |
| UV mapping | Required if using textures |

---

## Recommended Tools

| Tool | Use Case | Cost |
|------|----------|------|
| **CLO 3D** | Fashion-grade garment simulation & export | $50/mo |
| **Marvelous Designer** | Fabric draping & pattern-based modeling | $50/mo |
| **Blender + Cloth Sims** | Free alternative; requires manual setup | Free |
| **VITUS 3D Scanner** | Real garment scanning (hardware) | $$$ |
| **Photogrammetry (RealityCapture)** | Photo-based 3D scanning | $ |

### Recommended Pipeline (CLO 3D → Blender → GLB)

1. **CLO 3D:** Create/import 2D patterns, simulate fabric draping, pose on avatar
2. **Export:** Export as FBX (with embedded textures)
3. **Blender:** Import FBX, decimate to <15K triangles, rebake textures, export as GLB
4. **Validate:** Check file size, triangle count, and visual quality in Three.js

---

## File Naming Convention

Models are loaded by filename matching the `modelUrl` emitted by the showroom items API:

```
static/models/{slug}.glb
```

### Required Files

| File | Wardrobe Item | Showroom Product |
|------|---------------|-----------------|
| `architectural-blazer.glb` | — | The Architectural Blazer |
| `draped-silhouette-gown.glb` | — | Draped Silhouette Gown |
| `tailored-column-trouser.glb` | — | Tailored Column Trouser |
| `mesh_dress_lux.glb` | Atelier Drape Dress | — |
| `mesh_jacket_cyber.glb` | Cyber Blazer | — |
| `mesh_trouser_tapered.glb` | Tapered Trouser | — |
| `mesh_top_structural.glb` | Structural Shell Top | — |

---

## Export Checklist

### Before Exporting

- [ ] Mesh is manifold (no holes, no inverted normals)
- [ ] Triangle count ≤ 50,000
- [ ] All transforms applied (location [0,0,0], rotation [0,0,0], scale [1,1,1])
- [ ] Materials use PBR roughness/metalness workflow
- [ ] UV maps are non-overlapping
- [ ] Textures in PNG format, power-of-two dimensions (e.g., 1024×1024, 2048×2048)
- [ ] No animation data included
- [ ] File size ≤ 2 MB

### During Export (Blender → GLB)

1. Select the garment mesh(es)
2. File → Export → glTF 2.0 (.glb)
3. Settings:
   - Include: Selected Objects ✓
   - Transform: +Y Up (since Three.js uses Y-up)
   - Data: Include mesh data, materials, and textures
   - Compression: Enable Draco mesh compression if triangle count > 30K
4. Export to `static/models/` with the correct filename

---

## Verification Steps

After placing a new `.glb` file:

1. **Check the file serves correctly:**
   ```bash
   curl -I http://localhost:8000/static/models/architectural-blazer.glb
   # Expected: 200 OK, Content-Type: application/octet-stream or model/gltf-binary
   ```

2. **Check the Three.js loader handles it:**
   - Open the virtual atelier at `/virtual-experience`
   - Click the corresponding product card in the showroom panel
   - The model should load within 2 seconds with proper materials

3. **Check the dressing room swap:**
   - Switch to Dressing Room mode
   - Click the wardrobe item
   - The garment should swap in real-time with correct positioning

---

## Fallback Behavior

If a `.glb` file fails to load (404, corrupt file, etc.), the Three.js engine automatically falls back to:

- **Showroom mode:** A procedural dodecahedron with the product's brand color
- **Dressing room mode:** A procedural garment mesh matching the placeholder shape

This ensures the UI never breaks — placeholders are always available.

---

## Performance Targets

| Metric | Target | Threshold |
|--------|--------|-----------|
| GLB file size | <500 KB | <2 MB |
| Triangle count | <15,000 | <50,000 |
| Texture resolution | 1024×1024 | 2048×2048 |
| Material count | 1-2 per garment | Max 4 |
| Load time (3G) | <1.5s | <3s |
| Load time (broadband) | <0.3s | <1s |
| Memory usage (per model) | <10 MB | <30 MB |

---

## Troubleshooting

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| Model appears black | Missing normals or invalid material | Re-export with "Include Normals" checked |
| Model is tiny/huge | Wrong unit scale | Apply scale (1 GLB unit = 1 meter) |
| Model rotates oddly | Wrong up-axis | Export with +Y up, or add rotation in Three.js |
| Textures missing | External texture references | Embed textures in GLB or provide relative paths |
| Model loads slowly | Too many triangles | Decimate in Blender, enable Draco compression |
| Mesh z-fighting | Overlapping geometry | Clean mesh, remove internal faces |
