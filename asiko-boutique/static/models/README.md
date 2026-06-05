# ASIKO Atelier — 3D Model Assets

Place `.glb` (GLTF Binary) files in this directory to serve them to the 3D Virtual Atelier.

## Model Naming Convention

Models are loaded by name via the showroom items API. The convention is:

```
{slug}.glb
```

Example: `architectural-blazer.glb`

## Required Models

The showroom loads models dynamically based on product catalog. Place `.glb` files for each product to enable 3D product cards.

## Dressing Room Wardrobe

The dressing room expects these model IDs (fallback to procedural geometry if missing):

| File | Wardrobe Item | Target Mesh |
|------|---------------|-------------|
| `mesh_dress_lux.glb` | Atelier Drape Dress | Full garment mesh |
| `mesh_jacket_cyber.glb` | Cyber Blazer | Full garment mesh |
| `mesh_trouser_tapered.glb` | Tapered Trouser | Full garment mesh |
| `mesh_top_structural.glb` | Structural Shell Top | Full garment mesh |

## Model Requirements

- Format: GLTF Binary (.glb)
- Scale: Should fit within a 1x1x1 unit bounding box centered at origin
- PBR materials with standard roughness/metalness workflow
- Max 50k triangles per garment for performance
- No external texture dependencies (embedded textures preferred)

## Serving

Models are served automatically via Starlette's StaticFiles mount at `/static/models/{filename}`.

## Loading Priority

1. If `.glb` file exists → loads via GLTFLoader with progress indicator
2. If no `.glb` file → falls back to procedural Three.js geometry generator
