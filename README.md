# 🐹 CHONKER3 - VANILLA 1.0

The ultimate PDF extraction and editing tool with sacred hamster powers!

**⚠️ CURRENT VERSION: VANILLA 1.0** - This is the stable baseline with working text rendering.
See [VERSION.md](VERSION.md) for version details.

## ⚠️ IMPORTANT: Virtual Environment Usage

This project uses a Python virtual environment at `.venv/` for PDF extraction.
**ALWAYS use this virtual environment** - it contains all required dependencies:
- docling (PDF extraction)
- pypdfium2 (PDF processing)
- opencv-python (image preprocessing)
- And more...

The Rust code automatically uses `.venv/bin/python`. 
See [VENV_USAGE.md](VENV_USAGE.md) for details.

## ✨ New Features

### Interactive Document Editing
- **Double-click to Edit**: Click any text element twice to edit it inline
- **Drag & Drop Elements**: Click and drag any text to reposition it
- **Smart Text Wrapping**: Long lines automatically wrap for better readability
- **Persistent Edits**: Your changes persist until you change pages or load a new PDF

### Advanced PDF Processing
- **OCR Preprocessing**: Toggle preprocessing for better text extraction from scanned PDFs
  - Automatic deskewing (straightens tilted documents)
  - Denoising for cleaner scans
  - Contrast enhancement (CLAHE)
  - Sharpening for crisp text
  - Adaptive thresholding for optimal OCR
- **Real-time Preview**: See preprocessed PDF in the left panel when enabled

### Enhanced UI/UX
- **Teal Theme**: Beautiful teal (#1ABC9C) highlighting with light gray text
- **Hamster Icon**: Adorable hamster face icon matching Google's emoji design
- **Smooth Scrolling**: Dragged elements maintain position relative to document
- **Zoom Controls**: Zoom in/out with buttons or trackpad pinch gestures
- **Page Navigation**: Easy page switching with arrow buttons

## 🚀 Features

- **Native Performance**: Pure Rust with egui for blazing fast rendering
- **PDF Extraction**: Built-in Docling support via Python subprocess
- **Sacred Hamster**: 🐹 animations and helpful status messages
- **Dual Panel View**: PDF on left, extracted content on right
- **Smart Tables**: Automatic table detection and rendering
- **Drag & Drop**: Drop PDFs directly into the window

## 🏗️ Architecture

```
CHONKER3 (Rust + Python)
├── Rust GUI (egui/eframe)
├── PDF Rendering (pdfium)
├── Python Extraction (Docling via subprocess)
├── OCR Preprocessing (OpenCV)
└── Sacred Hamster 🐹
```

## 📦 Building

```bash
# Clone the repository
git clone <repo-url>
cd chonker3

# Run the convenient setup script
./run.sh

# Or manually:
# 1. Create virtual environment
uv venv .venv
uv pip install docling opencv-python-headless pdf2image pillow img2pdf numpy

# 2. Build Chonker3
cargo build --release
```

## 🎮 Usage

```bash
# Run with the script (recommended)
./run.sh

# Or run directly
cargo run --release

# The app runs in the background, check logs at:
tail -f chonker3.log
```

## 🎯 Controls

### File Operations
- **Open Button**: Load a PDF file
- **Drag & Drop**: Drop PDFs directly into the window
- **Extract Button**: Process the PDF with Docling

### Navigation
- **◀/▶ Buttons**: Navigate between pages
- **Page Counter**: Shows current page / total pages

### View Controls
- **🔍+/- Buttons**: Zoom in/out
- **Zoom %**: Current zoom level
- **Preprocess Checkbox**: Toggle OCR preprocessing

### Editing (Right Panel)
- **Double-click**: Edit any text element
- **Enter**: Save edit
- **Escape**: Cancel edit
- **Click & Drag**: Move text elements around
- **Hover**: See teal highlight on interactive elements

## 🐹 The Sacred Hamster

The hamster provides moral support during operations:
- 🐹 *chomping* - Extracting content
- 🐹 *preprocessing* - Enhancing PDF for OCR
- 🐹 Ready state - Waiting for your commands

## 🛠️ Technical Details

- **GUI Framework**: egui/eframe for native performance
- **PDF Rendering**: pdfium-render for accurate display
- **Extraction Engine**: Docling (state-of-the-art document AI)
- **OCR Preprocessing**: OpenCV with advanced image processing
- **Memory Efficient**: ~70MB idle (vs 200MB+ for Electron apps)
- **Cross-platform**: Works on macOS, Linux, and Windows

## 🎨 UI Improvements

- Maximized screen real estate with minimal controls
- Increased font sizes for better readability
- Consistent teal theme throughout
- Proper hamster emoji rendering 🐹
- Responsive layout that adapts to window size

## 🔧 Troubleshooting

- **Missing pdfium**: The app will try to find pdfium automatically
- **Python dependencies**: Run `uv pip install -r requirements.txt` if needed
- **Preprocessing not working**: Ensure OpenCV is installed in the virtual environment

Built with love, Rust, and hamster energy! 🐹✨