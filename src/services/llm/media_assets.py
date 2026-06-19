"""
Media Asset Map for Indus Net Technologies
This file maps semantic asset keys to their corresponding URLs.
mediaType and aspectRatio are intentionally omitted — the frontend resolves these intelligently.

LOCAL-FIRST: each key is grouped into a category in the VAANI Library
(`vaani_library/media/assets/<category>/`). Drop an image named after the key
(e.g. `leadership/ceo_abhishek_rungta.jpg`) — or a folder `leadership/ceo_abhishek_rungta/`
with images inside — and `local_asset_url()` returns that local file instead of
the external URL below. This lets the team build/swap photo libraries by simple
copy-paste, with the external URL kept as a fallback.
"""
import glob
import os
from typing import Dict, Any, List, Optional
from urllib.parse import quote

MEDIA_ASSETS: Dict[str, Dict[str, Any]] = {
    # IMAGES
    "indus_office": {
        "urls": ["https://media.licdn.com/dms/image/v2/D5622AQEXFMOWHG9UEQ/feedshare-shrink_800/B56Zoqi1FHG4Ag-/0/1761650367301?e=2147483647&v=beta&t=exXz0i4LcAqW6E3yIHlA7mggZvz4pE2X3OWWq4Eecmw"],
    },
    # Kolkata Newtown (Ecospace) office. "kolkata_office" kept as a generic
    # alias for back-compat; it points to the same Newtown image.
    "kolkata_newtown_office": {
        "urls": ["https://intglobal.com/wp-content/uploads/2025/06/image-134.webp"],
    },
    "kolkata_office": {
        "urls": ["https://intglobal.com/wp-content/uploads/2025/06/image-134.webp"],
    },
    # Kolkata Sector 5 (SDF Building) office.
    "kolkata_sector5_office": {
        "urls": ["https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgBP_TLtUJMWc8xyC8r2b1pTCbaOP4kALPPdr7x44Ts12WNfv4XPtmkDsUmSeJ9M4HOnf6ApIn_CZE4Gs7I3zCpL2m0fbPoaKAt8UcBwT2zoAGWuD0gqp4GebqFvfuCwvzTae-v13u3KhU/s1600/DSCN0274.JPG"],
    },
    "ceo_abhishek_rungta": {
        # External stock link removed (didn't fit the card). The CEO photos in the
        # library ("CEO (Abhishek Rungta) Images/") are used instead — see
        # ASSET_LIBRARY_FOLDER + local_asset_url.
        "urls": [],
    },
    "abhishek_rungta_sign": {
        "urls": ["https://intglobal.com/wp-content/uploads/2025/01/Abhishek-Rungta-1.png"],
    },
    "contact": {
        "urls": ["https://intglobal.com/wp-content/uploads/2025/01/image-1226x1511-1.png"],
    },
    "customer_experience": {
        "urls": ["https://www.gosurvey.in/media/a0vmcbf1/customer-experience-is-important-for-businesses.jpg"],
    },
    "ai_analytics": {
        "urls": ["https://www.gooddata.com/img/blog/_1200x630/what-is-ai-analytics_cover.png.webp"],
    },
    "cybersecurity": {
        "urls": ["https://www.dataguard.com/hubfs/240326_Blogpost_CybersecurityMeasures%20(1).webp"],
    },
    "global_map": {
        "urls": ["https://i.pinimg.com/564x/4e/9f/64/4e9f64e490a5fa034082d107ecbb5faf.jpg"],
    },
    # Flagship AI products
    "vyom_ai": {
        "urls": ["https://intglobal.com/wp-content/uploads/2025/11/vyom_ai_brain-1024x534.webp"],
    },

    # VIDEOS
    "intro_video": {
        "urls": ["https://youtu.be/iOvGVR7Lo_A?si=p8j8c72qXh-wpm4Z"],
    },
    "ceo_video": {
        "urls": ["https://intglobal.com/wp-content/uploads/2025/06/Abhishek-Rungta-INT-Intro.mp4"],
    },
    "careers_video": {
        "urls": ["https://www.youtube.com/watch?v=1pk9N_yS3lU&t=12s"],
    },
}


# ── Local asset libraries (VAANI Library) ────────────────────────────────────
# Maps each semantic key → its category folder under media/assets/. To override
# an asset with a local image, drop a file (or a folder of images) named after
# the key into that category, e.g. media/assets/leadership/ceo_abhishek_rungta.jpg
# Categories are just for tidiness; resolution is by key.
ASSET_CATEGORY: Dict[str, str] = {
    # leadership
    "ceo_abhishek_rungta": "leadership",
    "abhishek_rungta_sign": "leadership",
    "ceo_video": "leadership",
    # office / company
    "indus_office": "office",
    "kolkata_office": "office",
    "contact": "office",
    "global_map": "office",
    # partners
    "partner_microsoft": "partners",
    "partner_aws": "partners",
    "partner_google": "partners",
    "partner_strapi": "partners",
    "partner_odoo": "partners",
    "partner_zoho": "partners",
    "partner_meta": "partners",
    # testimonials
    "testimonial_malcolm": "testimonials",
    "testimonial_michael": "testimonials",
    "testimonial_roger": "testimonials",
    "testimonial_tapan": "testimonials",
    "testimonial_aniket": "testimonials",
    # case studies
    "case_sbig": "cases",
    "case_cashpoint": "cases",
    "case_dcb_bank": "cases",
    # service themes
    "customer_experience": "services",
    "digital_engineering": "services",
    "ai_analytics": "services",
    "cloud_devops": "services",
    "cybersecurity": "services",
    # videos
    "intro_video": "videos",
    "careers_video": "videos",
}

_IMAGE_EXTS = (".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".avif")

# Curated keys → an EXISTING library folder (matched to how the photos are
# actually organised, names with spaces are fine). When the folder has images,
# the library photo is used instead of the external URL above — so real photos
# replace stock links automatically. Folders are scanned recursively.
ASSET_LIBRARY_FOLDER: Dict[str, str] = {
    "ceo_abhishek_rungta": "CEO (Abhishek Rungta) Images",
    "abhishek_rungta_sign": "CEO (Abhishek Rungta) Images",
    "indus_office": "office",
    "kolkata_office": "office",
}


def local_asset_url(key: str) -> Optional[str]:
    """Return a served URL for a locally-provided override of `key`, else None.

    Resolution order:
      0. An explicit library folder mapped for this key (ASSET_LIBRARY_FOLDER),
         scanned recursively — first image wins.
      1. LIBRARY_ASSETS_DIR/<category>/<key>/  (folder of images named after key)
      2. LIBRARY_ASSETS_DIR/<category>/<key>.<ext>  (single file named after key)
    Served at /assets (paths URL-encoded).
    """
    if not key:
        return None
    # Imported lazily to avoid a circular import at module load.
    from src.core.config import settings

    base = settings.LIBRARY_ASSETS_DIR

    # 0) Explicit library folder for this key (recursive) — preferred.
    folder_rel = ASSET_LIBRARY_FOLDER.get(key)
    if folder_rel:
        folder_abs = os.path.join(base, folder_rel)
        if os.path.isdir(folder_abs):
            imgs = []
            for root, _d, files in os.walk(folder_abs):
                for f in files:
                    if not f.startswith(".") and f.lower().endswith(_IMAGE_EXTS):
                        imgs.append(os.path.join(root, f))
            if imgs:
                imgs.sort()
                rel = os.path.relpath(imgs[0], base).replace(os.sep, "/")
                return f"{settings.MEDIA_BASE_URL}/assets/{quote(rel)}"

    category = ASSET_CATEGORY.get(key)
    search_dirs = [os.path.join(base, category)] if category else []
    search_dirs.append(base)  # also allow a flat drop directly under assets/

    for d in search_dirs:
        # 1) a folder named after the key, with images inside
        folder = os.path.join(d, key)
        if os.path.isdir(folder):
            hits = sorted(
                p for p in glob.glob(os.path.join(folder, "*"))
                if p.lower().endswith(_IMAGE_EXTS)
            )
            if hits:
                rel = os.path.relpath(hits[0], base).replace(os.sep, "/")
                return f"{settings.MEDIA_BASE_URL}/assets/{rel}"
        # 2) a single file named after the key
        for ext in _IMAGE_EXTS:
            f = os.path.join(d, f"{key}{ext}")
            if os.path.isfile(f):
                rel = os.path.relpath(f, base).replace(os.sep, "/")
                return f"{settings.MEDIA_BASE_URL}/assets/{rel}"
    return None


# ── Pick-by-name library catalog ─────────────────────────────────────────────
# The primary way VAANI uses local images: every image under media/assets/ is
# listed (recursively) and shown to the card-writer LLM, which picks one by its
# path/name. Drop in new images or whole new folders any time — they appear in
# the catalog automatically, no code change needed.

def list_library_images() -> List[str]:
    """All image files under media/assets/ as forward-slash relative paths,
    sorted. Recurses into subfolders (e.g. 'Culture/Festivals/Diwali.jpg')."""
    from src.core.config import settings

    base = settings.LIBRARY_ASSETS_DIR
    out: List[str] = []
    if not os.path.isdir(base):
        return out
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f.startswith(".") or not f.lower().endswith(_IMAGE_EXTS):
                continue
            rel = os.path.relpath(os.path.join(root, f), base).replace(os.sep, "/")
            out.append(rel)
    return sorted(out)


def library_image_url(rel_path: str, used: Optional[set] = None) -> Optional[str]:
    """Resolve an LLM-chosen library image path to a served /assets URL.

    Matches the catalog tolerantly (exact → case-insensitive → basename) so small
    deviations in what the model echoes back still resolve. Path-traversal safe:
    only files that actually exist in the catalog can be returned. Returns None if
    no match or the resolved URL is already used in this batch."""
    if not rel_path:
        return None
    from src.core.config import settings

    catalog = list_library_images()
    if not catalog:
        return None

    want = rel_path.strip().replace("\\", "/").lstrip("/")
    want_low = want.lower()
    target = None
    for c in catalog:                       # exact
        if c == want:
            target = c
            break
    if target is None:                      # case-insensitive full path
        for c in catalog:
            if c.lower() == want_low:
                target = c
                break
    if target is None:                      # basename only
        want_base = os.path.basename(want_low)
        for c in catalog:
            if os.path.basename(c).lower() == want_base:
                target = c
                break
    if target is None:
        return None

    url = f"{settings.MEDIA_BASE_URL}/assets/{quote(target)}"
    if used and url in used:
        return None
    return url
