# J. 3D & VIRTUAL SYSTEMS

## Overview

These 3 systems handle 3D content generation, avatar profile management, and site-wide 3D branding imagery. Note: the 3D showroom has been removed — ASIKO now uses 3D PNG images for branding instead of WebGL/Three.js.

---

## 1. Mesh Generator Service

**File:** `app/services/mesh_generator.py`

### What It Does
Integration with Meshy.ai for AI-powered 3D garment generation from 2D images. Submits photos for 3D model generation and polls for completion status.

### Key Functions

#### Initiate 3D Generation
```python
async def initiate_3d_generation_task(image_url: str, product_id: str) -> dict:
    """
    Submit a 2D photo URL for 3D model generation.
    
    Args:
        image_url: URL of the source image
        product_id: Product to associate the model with
    
    Returns:
        {"task_id": "...", "status": "submitted"}
    """
    payload = {
        "image_url": image_url,
        "art_style": "realistic",
        "enable_pbr": True,
    }
    # POST to Meshy.ai API
```

#### Check Task Status
```python
async def check_external_task_status(task_id: str) -> dict:
    """
    Poll generation status.
    
    Returns:
        {"status": "in_progress"|"succeeded"|"failed", "model_url": "..."}
    """
    # GET from Meshy.ai API
```

### Generation Pipeline
```
1. Admin uploads product image
2. initiate_3d_generation_task() → Meshy.ai API
3. Meshy.ai processes (30-60 seconds)
4. check_external_task_status() polls every 5 seconds
5. On success: model_url saved to products.model_3d_url
6. On failure: pipeline_status set to 'failed'
```

### Status Flow
```
idle → queued → generating_mesh → completed | failed
```

### Why It Matters
3D models let customers see garments from every angle. This is the future of fashion e-commerce.

---

## 2. Avatar Profile Binding

**File:** `app/routes/dpp_verification.py`

### What It Does
Gender profile endpoint for gender-based skeleton fit selection. Maps customer gender to avatar type for virtual try-on.

### Route
```python
async def set_avatar_profile(request):
    """
    POST /api/virtual/profile/set
    Binds avatar gender to session.
    """
    form = await request.form()
    gender = form.get("gender", "unisex")  # male | female | unisex
    
    request.session["avatar_gender"] = gender
    
    return JSONResponse({
        "gender": gender,
        "skeleton_fit": "masculine" if gender == "male" else "feminine" if gender == "female" else "neutral"
    })
```

### Gender → Skeleton Mapping
| Gender | Skeleton Fit | Description |
|--------|-------------|-------------|
| male | masculine | Broader shoulders, narrower hips |
| female | feminine | Narrower shoulders, wider hips |
| unisex | neutral | Balanced proportions |

### Why It Matters
Different body types need different 3D models. This ensures the virtual try-on looks realistic.

---

## 3. 3D Brand Imagery

**Directory:** `static/images/icon-image/` (16 PNG files)

### What It Does
Site-wide branding using free 3D-rendered PNG images. Replaced the removed 3D showroom/WebGL system with static 3D imagery that works everywhere without JavaScript.

### Image Files
| Image | Used On | Purpose |
|-------|---------|---------|
| `hoody.png` | Login page, hero | Floating fashion item |
| `beanie hat.png` | Login, register | Accessory imagery |
| `necklace.png` | Register page | Jewelry imagery |
| `dress.png` | Hero section | Category representation |
| `shirt.png` | Hero section | Category representation |
| `trouser.png` | Hero section | Category representation |
| `skirt.png` | Hero section | Category representation |
| `jacket.png` | Hero section | Category representation |
| `shoe.png` | Hero section, footer | Category representation |
| `bag.png` | Hero section, footer | Category representation |
| `cap.png` | Lookbook | Accessory imagery |
| `gown.png` | Footer | Decorative element |
| `ankara.png` | Footer | Nigerian fashion element |
| `aso-oke.png` | Footer | Nigerian fashion element |
| `gele.png` | Footer | Nigerian fashion element |
| `agbada.png` | Footer | Nigerian fashion element |

### Placement
- **Hero section:** Floating 3D PNGs with parallax animation
- **Login/Register:** Left-side decorative panel
- **Lookbook:** Category illustrations
- **Footer:** Decorative elements
- **Dashboard:** Welcome imagery
- **Admin sidebar:** Brand identity

### CSS Animations
```css
@keyframes authFloat1 {
    0%, 100% { transform: translateY(0) rotate(-2deg) scale(1); }
    50% { transform: translateY(-20px) rotate(3deg) scale(1.02); }
}
.float-1 { animation: authFloat1 7s ease-in-out infinite; }
```

### Why It Matters
3D PNGs give the visual depth of 3D without the performance cost of WebGL. They work on every device, every browser, no JavaScript required.

---

## Summary

| System | File | Lines | Key Feature |
|--------|------|-------|-------------|
| Mesh Generator | `app/services/mesh_generator.py` | ~80 | Meshy.ai 2D→3D generation |
| Avatar Binding | `app/routes/dpp_verification.py` | ~30 | Gender-based skeleton fit |
| 3D Brand Imagery | `static/images/icon-image/` | 16 files | Site-wide 3D PNG branding |

**Total: ~110 lines of code + 16 image assets**
