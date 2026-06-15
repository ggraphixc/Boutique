# J. 3D & VIRTUAL SYSTEMS

## Overview

ASIKO uses 3D-rendered PNG images for site-wide branding. The 3D showroom/WebGL system, mesh generator, and avatar binding have been removed — the platform is now a pure fashion e-commerce storefront.

---

## 1. 3D Brand Imagery

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
| `Leather pant.png` | Hero section | Category representation |
| `denim skirt.png` | Hero section | Category representation |
| `black jacket.png` | Hero section | Category representation |
| `leather shoe.png` | Hero section, footer | Category representation |
| `bootshoe.png` | Hero section, footer | Category representation |
| `cap.png` | Lookbook | Accessory imagery |
| `lady gown.png` | Footer | Decorative element |
| `neck chain.png` | Footer | Jewelry element |
| `ripped jeans.png` | Footer | Fashion element |
| `short jeans.png` | Footer | Fashion element |
| `sweatshirt.png` | Footer | Fashion element |

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

| System | Status | Notes |
|--------|--------|-------|
| Mesh Generator | Removed | Dead code deleted |
| Avatar Binding | Removed | Dead code deleted |
| 3D Brand Imagery | Active | 16 PNG assets in `static/images/icon-image/` |

**Total: 16 image assets**
