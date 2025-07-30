//! Skia-based document renderer
//! VANILLA 1.0 - This is the active renderer in the stable version

pub mod document_canvas;
pub mod pdf_renderer;

pub use document_canvas::SkiaDocumentCanvas;