# Chonker3

A stable PDF viewer with text extraction and rendering.

## Version: Vanilla 1.0

This is the clean baseline version with:
- Egui-based text rendering
- Fixed font sizes (no more random sizing)
- Proper coordinate conversion
- 1,061 lines of clean code

## Quick Start

```bash
# Use the virtual environment
source .venv/bin/activate

# Run the app
cargo run

# Or use the helper script
./run.sh
```

## Features

- ✅ PDF viewing with zoom and pan
- ✅ Text extraction with Docling/pypdfium2  
- ✅ Stable text rendering
- ✅ Click text to copy
- ✅ Cmd+scroll to zoom

## Requirements

- Rust 1.70+
- Python 3.8+ with virtual environment
- pdfium library

The app uses the `.venv` virtual environment which has all Python dependencies pre-installed.

