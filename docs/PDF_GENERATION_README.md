# Getting Started PDF - Generation Notes

## Overview

A visual "Getting Started" PDF walkthrough has been created for new Yoto Smart Stream users. This is a **local-only** document and is not committed to git.

## Files Created

### PDF Document
- **Location:** `docs/getting-started.pdf`
- **Size:** 5.1 MB
- **Pages:** ~8 pages
- **Format:** Letter size (8.5" x 11")

### Screenshots
All screenshots are stored in `docs/screenshots/`:

1. **01-dashboard.png** (469 KB)
   - Shows the main dashboard with player status, audio library, and quick actions
   - Displays 2 connected players (Living Room and New Bedroom)
   - Shows 10 available audio files

2. **02-smart-streams.png** (577 KB)
   - Shows Smart Streams page with play modes
   - Demonstrates sequential, loop, shuffle, and endless shuffle modes
   - Shows managed streams and create card form

3. **03-library.png** (1.9 MB)
   - Shows the Yoto Library with 234 cards
   - Displays card grid with cover art and titles
   - Shows filter functionality

## PDF Contents

The PDF includes:

1. **Title Page** - Professional cover with project name and subtitle
2. **Introduction** - Welcome message and feature overview
3. **Section 1: Dashboard** - Full walkthrough of the dashboard interface
4. **Section 2: Smart Streams** - Explanation of play modes and stream creation
5. **Section 3: Library** - How to browse and manage Yoto cards
6. **Next Steps** - Suggested actions for new users
7. **Getting Help** - Support resources and documentation links

## Generation Script

- **Location:** `docs/generate_pdf.py`
- **Dependencies:** reportlab
- **Usage:** Run with Python 3 to regenerate the PDF

```bash
# Create temporary venv and generate PDF
python3 -m venv .venv-pdf
source .venv-pdf/bin/activate
pip install reportlab
python docs/generate_pdf.py
deactivate
rm -rf .venv-pdf
```

## Screenshots Source

Screenshots were captured from the live Railway develop deployment at:
`https://yoto-smart-stream-develop.up.railway.app`

Using Playwright browser automation via the MCP Microsoft Playwright server.

## Notes

- The PDF uses the Yoto Smart Stream branding colors (blues: #2563eb, #1e40af)
- All screenshots are embedded at 6" width for readability
- Text is set in Helvetica with justified body text
- The document is designed for printing or digital distribution

## Regeneration

To regenerate the PDF with updated screenshots:

1. Update screenshots in `docs/screenshots/`
2. Run `python docs/generate_pdf.py`
3. The PDF will be overwritten at `docs/getting-started.pdf`

---

**Created:** January 12, 2025  
**Environment:** Railway develop (v0.2.1)  
**Status:** ✅ Complete - Local only, not committed to git
