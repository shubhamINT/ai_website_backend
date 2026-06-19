# VAANI Library

Everything VAANI needs, in one folder: the knowledge base + all media. Self-contained
and portable — point another agent at it with the `VAANI_LIBRARY_DIR` env var.

```
vaani_library/
├── knowledge/
│   └── rich_chroma_db/        # ChromaDB vector store (collections: company_knowledge, page_index)
└── media/
    ├── cards/                 # card images, one per knowledge block (served at /media)
    │                          # filename = the block's media_id, e.g. awards-55dcd5d9-0.webp
    └── assets/                # curated photo libraries — add by copy-paste (served at /assets)
        ├── leadership/        #   ceo_abhishek_rungta, abhishek_rungta_sign, ceo_video
        ├── office/            #   indus_office, kolkata_office, contact, global_map
        ├── partners/          #   partner_microsoft, partner_aws, partner_google, …
        ├── testimonials/      #   testimonial_malcolm, testimonial_michael, …
        ├── cases/             #   case_sbig, case_cashpoint, case_dcb_bank
        ├── services/          #   customer_experience, digital_engineering, ai_analytics, …
        └── videos/            #   intro_video, careers_video
```

## Adding / swapping a photo (copy-paste)

The agent refers to curated visuals by a **semantic key** (e.g. `ceo_abhishek_rungta`).
Each key has an external fallback URL in `src/services/llm/media_assets.py`, but a
**local file wins** ("local-first"). To override:

1. Find the key's category (see comments above, or `ASSET_CATEGORY` in `media_assets.py`).
2. Drop an image into that category folder, named after the key:
   ```
   media/assets/leadership/ceo_abhishek_rungta.jpg
   ```
   (any of `.webp .png .jpg .jpeg .gif .svg .avif`)
3. That's it — VAANI now uses your image. Delete it to revert to the URL.

**Multiple photos / a real "library":** instead of a single file, make a folder named
after the key and put images inside — the first (alphabetical) is used:
```
media/assets/leadership/ceo_abhishek_rungta/
    01-headshot.jpg
    02-keynote.jpg
```

A new key is not required to be in any category — a file dropped directly in
`media/assets/<key>.<ext>` also resolves.

## Wiring (backend)

`src/core/config.py` → `VAANI_LIBRARY_DIR` (default: this folder).
- `KNOWLEDGE_DIR`      → `knowledge/rich_chroma_db` (read by `vectordb_svc.py`)
- `MEDIA_DIR`          → `media/cards`  (mounted at `/media`)
- `LIBRARY_ASSETS_DIR` → `media/assets` (mounted at `/assets`)

To use this library from a different location/agent, set `VAANI_LIBRARY_DIR` to its path.
