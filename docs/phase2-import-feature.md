# Phase 2: Document Import Feature

**Status: Planned — not yet implemented. Built after Phase 1 is stable and tested.**

---

## Overview

Phase 2 allows users to upload Word (`.docx`) or PDF documents and automatically create ProPresenter 7 presentations from the content. Pattern rules (regex or formatting-based) define how text elements map to PP7 slide types, looks, and themes.

**Example use cases:**
- Sermon notes in a Word document → presentation with verse/point/quote slides
- Bulletin PDF → announcement slides
- Song lyrics in a text file → song presentation with verse/chorus structure

---

## User Workflow

```
1. User uploads .docx / .pdf
2. User selects (or creates) an Import Profile
   - Import Profile: a set of pattern rules that define text → slide mappings
3. App parses the document
4. App previews the detected structure (editable before creating)
5. User confirms → App creates presentations in PP7 via the API
6. User is taken to the standard QA audit to validate the new presentations
```

---

## Import Profile (Rule Schema)

An Import Profile is a named collection of **Pattern Rules**.

### Pattern Rule

```json
{
  "name": "Quoted text → Highlight slide",
  "pattern_type": "regex | formatting | position",
  "pattern": "\"([^\"]+)\"",
  "target_slide_type": "verse | chorus | bridge | title | point | quote | scripture | blank",
  "look_name": "Highlight",
  "theme_name": "Quote Theme",
  "text_transform": "uppercase | titlecase | none",
  "notes": "Apply to text surrounded by double quotes"
}
```

### Pattern Types

| Type | Description | Examples |
|---|---|---|
| `regex` | Match text against a regex pattern | `"([^"]+)"` matches quoted text; `^\d+\.` matches numbered points |
| `formatting` | Match based on DOCX formatting (bold, italic, underline, heading level) | `underline = true` → Title slide |
| `position` | Match by position in document (first paragraph, last paragraph, after heading) | `first_paragraph → Title` |

### Formatting Attributes (DOCX only)

| Attribute | Values |
|---|---|
| `bold` | `true / false` |
| `italic` | `true / false` |
| `underline` | `true / false` |
| `heading_level` | `1 / 2 / 3 / null` |
| `font_size_gte` | Minimum font size (pt) |
| `font_size_lte` | Maximum font size (pt) |
| `color` | Hex colour string e.g. `#FF0000` |

---

## Technical Implementation Plan

### New Dependencies (backend)

```python
python-docx==1.1.2        # Word document parsing
PyMuPDF==1.24.14          # PDF text extraction (fitz)
# or pdfplumber==0.11.4   # Alternative PDF parser (simpler API)
```

### New Files

```
backend/app/
├── models/
│   └── import_profile.py      # ImportProfile + ImportPatternRule ORM models
├── schemas/
│   └── import_profile.py      # Pydantic schemas
├── routers/
│   ├── import_profiles.py     # CRUD for import profiles
│   └── document_import.py     # Upload + parse + preview + create endpoints
└── services/
    ├── document_parser.py     # .docx and .pdf → ParsedDocument
    ├── pattern_engine.py      # Apply pattern rules → structured slide list
    └── presentation_builder.py # POST to PP7 API to create presentations

frontend/src/app/
└── import/
    ├── page.tsx               # Upload UI + Import Profile selector
    ├── preview/page.tsx       # Editable preview of detected structure
    └── profiles/page.tsx      # Manage Import Profiles
```

### New API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET/POST/PUT/DELETE` | `/api/import-profiles` | Import Profile CRUD |
| `POST` | `/api/import/upload` | Upload document, return file_id |
| `POST` | `/api/import/preview` | Parse document + apply pattern rules → preview |
| `POST` | `/api/import/create` | Create PP7 presentations from preview |

### PP7 API Calls for Presentation Creation

Phase 2 will use:
- `POST /v1/playlists` — Create a new playlist for the imported presentations
- `POST /v1/playlist/{id}` — Add presentation to playlist

> **Note:** The PP7 API v1 does not expose a direct `POST /v1/presentation` endpoint for creating new presentations with full slide content. Phase 2 will require investigation of the PP7 API's actual write capabilities at implementation time. Options include:
> 1. Using any available POST endpoint for presentations
> 2. Using PP7's built-in import file format if accessible via API
> 3. Triggering PP7 macros configured to create slide types

---

## Data Models

### `ImportProfile` (table: `import_profiles`)

```
id              INT PK
name            TEXT unique
description     TEXT
default_look    TEXT null    PP7 look name to use if rule has none
default_theme   TEXT null    PP7 theme name to use if rule has none
created_at      DATETIME
updated_at      DATETIME
```

### `ImportPatternRule` (table: `import_pattern_rules`)

```
id                  INT PK
import_profile_id   INT FK
name                TEXT
pattern_type        TEXT   regex | formatting | position
pattern             TEXT   regex string or JSON formatting spec
target_slide_type   TEXT
look_name           TEXT null
theme_name          TEXT null
text_transform      TEXT   uppercase | titlecase | none
position            INT    ordering within profile
```

---

## Document Parsing Pipeline

```
Upload file
  │
  ├── .docx → python-docx
  │     Extract: paragraphs with run-level formatting
  │     (bold, italic, underline, heading level, font size, color)
  │
  └── .pdf → PyMuPDF / pdfplumber
        Extract: text blocks with approximate formatting
        (limited — PDF doesn't always preserve semantic formatting)
         │
         ▼
  ParsedDocument: list of ParsedBlock
    { text, bold, italic, underline, heading_level, font_size, color, page_num }
         │
         ▼
  pattern_engine.apply_rules(document, import_profile)
    For each block, find first matching pattern rule
    Return: list of SlideSpec
      { text, slide_type, look_name, theme_name, text_transform }
         │
         ▼
  Preview sent to frontend (editable)
         │
  User confirms
         │
         ▼
  presentation_builder.create_in_pp7(slide_specs)
    POST to PP7 API
```

---

## UI Design Notes

- **Upload page**: drag-and-drop or file picker; select Import Profile; real-time preview
- **Preview table**: each row is a detected slide — editable type, look, theme; reorderable
- **Confirm**: shows count of slides to create; links to profile being used
- **Post-create**: auto-navigate to Audit page with the new presentations highlighted

---

## Regex Examples

| Rule | Pattern | Matches |
|---|---|---|
| Quoted text | `"([^"]+)"` | "Amazing Grace" → quote slide |
| Scripture reference | `\b\d?\s?[A-Z][a-z]+\s+\d+:\d+` | John 3:16 → scripture slide |
| Numbered point | `^\d+[\.\)]\s+(.+)` | 1. First point → point slide |
| Chorus marker | `(?i)^chorus:?\s*` | CHORUS: → chorus slide type |
| ALL CAPS line | `^[A-Z\s]{4,}$` | OPENING PRAYER → title slide |

---

## Open Questions for Phase 2 Implementation

1. Does PP7 expose a create-presentation API? If not, what's the best workaround?
2. Should Import Profiles be mergeable with QA Profiles (run audit immediately after import)?
3. PDF formatting extraction is lossy — should we prefer DOCX only and note PDF as "best effort"?
4. Should pattern matching be ordered (first match wins) or priority-based?
5. Should the AI assistant be able to suggest Import Pattern Rules from a sample document?

---

## Timeline Estimate

Phase 2 is estimated at 3–5 days of implementation after Phase 1 is fully tested:
- Day 1: Document parsing services + pattern engine
- Day 2: API endpoints + presentation builder
- Day 3: Frontend upload + preview pages
- Day 4–5: Testing, edge cases, PP7 API write investigation
