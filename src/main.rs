// CHONKER3 - VANILLA 1.0
// This is the stable baseline version with working text rendering
// Tag: vanilla-1.0
// See VERSION.md for details

use eframe::egui;
use egui::{Color32, RichText, Vec2, ColorImage, TextureHandle, ScrollArea, Pos2};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use pdfium_render::prelude::*;

mod extractor;
use extractor::{extract_pdf, ExtractionResult};

mod types;

mod skia_renderer;

const TEAL: Color32 = Color32::from_rgb(0x1A, 0xBC, 0x9C);

#[derive(Default)]
struct Chonker3App {
    current_pdf: Option<PathBuf>,
    extracted_json: Option<PathBuf>,
    extracted_data: Option<serde_json::Value>,
    status_message: String,
    is_extracting: bool,
    extraction_result: Arc<Mutex<Option<ExtractionResult>>>,
    pdf_page: usize,
    pdf_bytes: Option<Vec<u8>>,
    pdfium: Option<Arc<Pdfium>>,
    pdf_texture: Option<TextureHandle>,
    pdf_page_count: usize,
    zoom_level: f32,
    pan_offset: egui::Vec2,
    search_query: String,
    show_search: bool,
    show_help: bool,
    // Edit and drag support
    item_offsets: std::collections::HashMap<String, egui::Vec2>,
    item_text_overrides: std::collections::HashMap<String, String>,
    editing_item_id: Option<String>,
    edit_text: String,
    dragging_item_id: Option<String>,
    drag_offset: egui::Vec2,
}

impl Chonker3App {
    fn new(_cc: &eframe::CreationContext<'_>) -> Self {
        let mut app = Self::default();
        app.status_message = "Drop a PDF or click 'Open' to begin".to_string();
        app.zoom_level = 0.86; // Default zoom to fit page nicely
        
        app
    }
    
    fn load_pdf(&mut self, pdf_path: PathBuf) {
        self.current_pdf = Some(pdf_path.clone());
        self.extracted_data = None;
        self.extracted_json = None;
        self.status_message = "PDF loaded. Click 'Extract' to process.".to_string();
        
        if self.pdfium.is_none() {
            let lib_path = std::env::var("PDFIUM_DYNAMIC_LIB_PATH")
                .unwrap_or_else(|_| "./lib".to_string());
            
            match Pdfium::bind_to_library(
                Pdfium::pdfium_platform_library_name_at_path(&lib_path)
            ).or_else(|_| Pdfium::bind_to_system_library()) {
                Ok(bindings) => self.pdfium = Some(Arc::new(Pdfium::new(bindings))),
                Err(_) => return,
            }
        }
        
        if let Ok(bytes) = std::fs::read(&pdf_path) {
            self.pdf_bytes = Some(bytes);
            self.pdf_page = 0;
            self.pdf_texture = None;
            
        }
    }
    
    
    fn extract_content(&mut self) {
        if let Some(pdf_path) = self.current_pdf.clone() {
            self.is_extracting = true;
            self.status_message = "Extracting...".to_string();
            
            let result_handle = self.extraction_result.clone();
            
            std::thread::spawn(move || {
                let result = extract_pdf(&pdf_path).unwrap_or_else(|e| ExtractionResult {
                    success: false,
                    json_path: String::new(),
                    items: 0,
                    message: format!("Failed: {}", e),
                });
                
                *result_handle.lock().unwrap() = Some(result);
            });
        }
    }
    
    fn load_pdf_page(&mut self, ctx: &egui::Context, target_width: f32) {
        if let (Some(pdfium), Some(pdf_bytes)) = (&self.pdfium, &self.pdf_bytes) {
            if let Ok(document) = pdfium.load_pdf_from_byte_slice(pdf_bytes, None) {
                self.pdf_page_count = document.pages().len() as usize;
                
                if let Ok(page) = document.pages().get(self.pdf_page as u16) {
                    let page_width = page.width().value;
                    let page_height = page.height().value;
                    let scale = (target_width / page_width) * self.zoom_level;
                    
                    let render_width = (page_width * scale) as i32;
                    let render_height = (page_height * scale) as i32;
                    
                    let config = PdfRenderConfig::new()
                        .set_target_size(render_width, render_height)
                        .render_form_data(true);
                    
                    if let Ok(bitmap) = page.render_with_config(&config) {
                        let image = bitmap.as_image();
                        let image_buffer = image.as_bytes();
                        let pixels: Vec<_> = image_buffer
                            .chunks_exact(4)
                            .map(|p| Color32::from_rgba_unmultiplied(p[2], p[1], p[0], p[3]))
                            .collect();
                        
                        let color_image = ColorImage {
                            size: [render_width as usize, render_height as usize],
                            pixels,
                        };
                        
                        self.pdf_texture = Some(ctx.load_texture(
                            "pdf_page",
                            color_image,
                            Default::default()
                        ));
                    }
                }
            }
        }
    }
    
}

impl Chonker3App {
    fn convert_to_document_state(&self, json_data: &serde_json::Value) -> types::DocumentState {
        use crate::types::{DocumentItem, ItemType, BoundingBox};
        
        let mut items = Vec::new();
        
        // Get items array from JSON
        if let Some(json_items) = json_data.get("items").and_then(|v| v.as_array()) {
            for json_item in json_items {
                // Filter by current page
                let page = json_item.get("page").and_then(|v| v.as_u64()).unwrap_or(0);
                if page != self.pdf_page as u64 + 1 {
                    continue;
                }
                
                // Extract bbox
                let bbox = json_item.get("bbox");
                if let Some(bbox) = bbox {
                    if let (Some(left), Some(top), Some(width), Some(height)) = (
                        bbox.get("left").and_then(|v| v.as_f64()),
                        bbox.get("top").and_then(|v| v.as_f64()),
                        bbox.get("width").and_then(|v| v.as_f64()),
                        bbox.get("height").and_then(|v| v.as_f64()),
                    ) {
                        // Extract content
                        let content = json_item.get("content")
                            .or_else(|| json_item.get("text"))
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();
                        
                        if content.trim().is_empty() {
                            continue;
                        }
                        
                        // Determine item type
                        let item_type_str = json_item.get("type").and_then(|v| v.as_str()).unwrap_or("TextItem");
                        let item_type = match item_type_str {
                            "TitleItem" => ItemType::Title,
                            "SectionHeaderItem" => ItemType::Header,
                            "TableItem" => ItemType::Table,
                            _ => ItemType::Text,
                        };
                        
                        // Extract font size from attributes.style.font_size if available
                        let font_size = if let Some(attributes) = json_item.get("attributes") {
                            if let Some(style) = attributes.get("style") {
                                if let Some(fs) = style.get("font_size").and_then(|v| v.as_f64()) {
                                    fs as f32
                                } else {
                                    // Fallback: estimate from height if no font size in metadata
                                    12.0 // Default reasonable font size
                                }
                            } else {
                                12.0 // Default
                            }
                        } else {
                            12.0 // Default
                        };
                        
                        // Generate item ID
                        let item_id = format!("item_{}_{}_{}", 
                            self.pdf_page,
                            (left * 1000.0) as i32,
                            (top * 1000.0) as i32
                        );
                        
                        // Create document item
                        let doc_item = DocumentItem {
                            id: item_id,
                            bbox: BoundingBox {
                                left,
                                top,
                                width,
                                height: height.abs(),
                            },
                            content,
                            font_size,
                            color: match item_type {
                                ItemType::Title | ItemType::Header => (0, 100, 200),
                                _ => (0, 0, 0),
                            },
                            item_type,
                        };
                        
                        items.push(doc_item);
                    }
                }
            }
        }
        
        let search_results = self.find_search_matches(&items);
        
        types::DocumentState {
            items,
            page_size: (612.0, 792.0), // Standard US Letter
            zoom: self.zoom_level,
            offset: (self.pan_offset.x, self.pan_offset.y),
            selected_item: None,
            editing_item: self.editing_item_id.clone(),
            search_query: self.search_query.clone(),
            search_results,
            item_offsets: self.item_offsets.iter()
                .map(|(k, v)| (k.clone(), (v.x, v.y)))
                .collect(),
            item_text_overrides: self.item_text_overrides.clone(),
        }
    }
    
    fn find_search_matches(&self, items: &[types::DocumentItem]) -> Vec<String> {
        if self.search_query.is_empty() {
            return Vec::new();
        }
        
        let query = self.search_query.to_lowercase();
        items.iter()
            .filter(|item| item.content.to_lowercase().contains(&query))
            .map(|item| item.id.clone())
            .collect()
    }
}

impl eframe::App for Chonker3App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Handle keyboard shortcuts
        if ctx.input(|i| i.modifiers.command && i.key_pressed(egui::Key::F)) {
            self.show_search = true;
        }
        
        
        // Check extraction result
        let result_to_process = self.extraction_result.lock().unwrap().take();
        if let Some(result) = result_to_process {
            self.is_extracting = false;
            if result.success {
                self.status_message = format!("Extracted {} items", result.items);
                self.extracted_json = Some(PathBuf::from(&result.json_path));
                
                if let Ok(json_content) = std::fs::read_to_string(&result.json_path) {
                    if let Ok(data) = serde_json::from_str(&json_content) {
                        self.extracted_data = Some(data);
                    }
                }
            } else {
                self.status_message = result.message.clone();
            }
        }
        
        // Top panel
        egui::TopBottomPanel::top("top_panel")
            .exact_height(40.0)
            .show(ctx, |ui| {
            // Teal background
            ui.painter().rect_filled(ui.available_rect_before_wrap(), 0.0, TEAL);
            
            ui.horizontal_centered(|ui| {
                ui.add_space(5.0);
                
                // Hamster emoji - will display with proper colors
                ui.label(RichText::new("🐹").size(24.0));
                
                ui.label(RichText::new("CHONKER3").size(16.0).strong().color(Color32::WHITE));
                
                // Status message
                ui.separator();
                ui.label(RichText::new(&self.status_message).size(14.0).color(Color32::WHITE));
                if self.is_extracting {
                    ui.label(RichText::new(" 🐹 *chomping*").size(14.0));
                    ctx.request_repaint();
                }
                
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.add_space(5.0);
                    
                    // Controls
                    if self.current_pdf.is_some() {
                        // Extract button
                        if !self.is_extracting {
                            if ui.button(RichText::new("Extract").color(Color32::WHITE).strong().size(14.0))
                                .clicked() 
                            {
                                self.extract_content();
                            }
                        }
                        
                        ui.separator();
                        
                        // Search button
                        if ui.button(RichText::new("🔍").size(14.0).color(Color32::WHITE))
                            .on_hover_text("Search (Ctrl+F)")
                            .clicked() {
                            self.show_search = !self.show_search;
                        }
                        
                        ui.separator();
                        
                        // Help button
                        if ui.button(RichText::new("?").size(14.0).color(Color32::WHITE))
                            .on_hover_text("Help")
                            .clicked() {
                            self.show_help = !self.show_help;
                        }
                        
                        ui.separator();
                        
                        // Zoom controls
                        if ui.button(RichText::new("🔍+").size(14.0).color(Color32::WHITE)).clicked() {
                            self.zoom_level = (self.zoom_level * 1.2).min(3.0);
                            self.pdf_texture = None;
                        }
                        ui.label(RichText::new(format!("{}%", (self.zoom_level * 100.0) as i32)).size(12.0).color(Color32::WHITE));
                        if ui.button(RichText::new("🔍-").size(14.0).color(Color32::WHITE)).clicked() {
                            self.zoom_level = (self.zoom_level / 1.2).max(0.5);
                            self.pdf_texture = None;
                        }
                        
                        // Reset view button
                        if ui.button(RichText::new("🏠").size(14.0).color(Color32::WHITE))
                            .on_hover_text("Reset view")
                            .clicked() {
                            self.zoom_level = 1.0;
                            self.pan_offset = egui::Vec2::ZERO;
                        }
                        
                        ui.separator();
                        
                        // Page controls
                        if ui.button(RichText::new("▶").size(16.0).color(Color32::WHITE)).clicked() && self.pdf_page + 1 < self.pdf_page_count {
                            self.pdf_page += 1;
                            self.pdf_texture = None;
                        }
                        ui.label(RichText::new(format!("{}/{}", self.pdf_page + 1, self.pdf_page_count)).size(14.0).color(Color32::WHITE));
                        if ui.button(RichText::new("◀").size(16.0).color(Color32::WHITE)).clicked() && self.pdf_page > 0 {
                            self.pdf_page -= 1;
                            self.pdf_texture = None;
                        }
                    }
                    
                    if ui.button(RichText::new("Open").size(14.0).color(Color32::WHITE)).clicked() {
                        if let Some(path) = rfd::FileDialog::new()
                            .add_filter("PDF", &["pdf"])
                            .pick_file()
                        {
                            self.load_pdf(path);
                        }
                    }
                });
            });
        });
        
        // Search bar (appears below toolbar when active)
        if self.show_search {
            egui::TopBottomPanel::top("search_panel")
                .min_height(40.0)
                .show(ctx, |ui| {
                    ui.horizontal(|ui| {
                        ui.add_space(10.0);
                        ui.label("Search:");
                        
                        let response = ui.add_sized(
                            Vec2::new(200.0, 20.0),
                            egui::TextEdit::singleline(&mut self.search_query)
                        );
                        
                        // Focus on search box when it appears
                        if response.gained_focus() || self.show_search {
                            response.request_focus();
                        }
                        
                        // Handle Enter key
                        if response.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)) {
                            // Search is automatically updated through the binding
                        }
                        
                        // Handle Escape key to close search
                        if ui.input(|i| i.key_pressed(egui::Key::Escape)) {
                            self.show_search = false;
                            self.search_query.clear();
                        }
                        
                        // Clear button
                        if !self.search_query.is_empty() {
                            if ui.button("✕").clicked() {
                                self.search_query.clear();
                            }
                        }
                        
                        // Match count
                        if !self.search_query.is_empty() {
                            let match_count = if let Some(data) = &self.extracted_data {
                                let document_state = self.convert_to_document_state(data);
                                document_state.search_results.len()
                            } else {
                                0
                            };
                            ui.label(format!("{} matches", match_count));
                        }
                        
                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            if ui.button("Close").clicked() {
                                self.show_search = false;
                                self.search_query.clear();
                            }
                            ui.add_space(10.0);
                        });
                    });
                });
        }
        
        // Help panel (appears as a window when active)
        if self.show_help {
            egui::Window::new("Help")
                .collapsible(false)
                .resizable(false)
                .fixed_pos(Pos2::new(400.0, 200.0))
                .show(ctx, |ui| {
                    ui.heading("Chonker3 Help");
                    ui.separator();
                    
                    ui.label(RichText::new("Features:").strong());
                    ui.label("• Click on text to copy it to clipboard");
                    ui.label("• Use search to find text (highlights in yellow)");
                    ui.label("• Zoom with buttons or Cmd+scroll");
                    ui.label("• Pan by dragging the view");
                    ui.separator();
                    
                    ui.label(RichText::new("Keyboard Shortcuts:").strong());
                    ui.label("• Cmd+F: Open search");
                    ui.label("• Escape: Close search");
                    ui.label("• ▶/◀: Navigate pages");
                    ui.separator();
                    
                    ui.label(RichText::new("Tips:").strong());
                    ui.label("• Extract before viewing for best results");
                    ui.label("• Some PDFs may have text rendering issues");
                    ui.label("• Copy text that appears misplaced");
                    
                    ui.separator();
                    if ui.button("Close").clicked() {
                        self.show_help = false;
                    }
                });
        }
        
        // Central area
        egui::CentralPanel::default().show(ctx, |ui| {
            if self.current_pdf.is_some() {
                let available = ui.available_size();
                let panel_width = available.x * 0.5;
                
                if self.pdf_texture.is_none() && self.pdf_bytes.is_some() {
                    self.load_pdf_page(ctx, panel_width);
                }
                
                ui.horizontal(|ui| {
                    // Left panel - PDF
                    ui.allocate_ui(Vec2::new(panel_width - 2.0, available.y), |ui| {
                        ScrollArea::both().id_salt("pdf_scroll").show(ui, |ui| {
                            if let Some(texture) = &self.pdf_texture {
                                ui.image(texture);
                            } else {
                                ui.centered_and_justified(|ui| {
                                    ui.label(RichText::new("Loading...").color(Color32::GRAY).size(14.0));
                                });
                            }
                        });
                    });
                    
                    ui.separator();
                    
                    // Right panel - Extracted content
                    ui.allocate_ui(Vec2::new(panel_width - 2.0, available.y), |ui| {
                        // White background for content area
                        ui.painter().rect_filled(
                            ui.available_rect_before_wrap(),
                            0.0,
                            Color32::WHITE
                        );
                        
                        if let Some(data) = self.extracted_data.clone() {
                            use crate::skia_renderer::SkiaDocumentCanvas;
                            
                            let document_state = self.convert_to_document_state(&data);
                            
                            // Wrap canvas in scroll area to prevent overflow
                            ScrollArea::both()
                                .id_salt("extracted_content_scroll")
                                .auto_shrink([false, false])
                                .show(ui, |ui| {
                                    let canvas = SkiaDocumentCanvas::new(document_state)
                                        .with_zoom(self.zoom_level);
                                    
                                    let canvas_response = ui.add(canvas);
                                    
                                    // Handle zoom with mouse wheel
                                    if canvas_response.hovered() {
                                        ui.input(|i| {
                                            // Check for Ctrl/Cmd + scroll for zoom
                                            if i.modifiers.command {
                                                let scroll_delta = i.raw_scroll_delta.y;
                                                if scroll_delta != 0.0 {
                                                    // Positive scroll = zoom in, negative = zoom out
                                                    let zoom_factor = 1.0 + (scroll_delta * 0.001);
                                                    self.zoom_level = (self.zoom_level * zoom_factor).clamp(0.5, 3.0);
                                                }
                                            } else {
                                                // Regular scroll for panning
                                                self.pan_offset += i.raw_scroll_delta;
                                            }
                                        });
                                    }
                                    
                                    // Handle panning with mouse drag
                                    if canvas_response.dragged() {
                                        self.pan_offset += canvas_response.drag_delta();
                                    }
                                });
                        } else {
                            ui.centered_and_justified(|ui| {
                                if self.is_extracting {
                                    ui.vertical_centered(|ui| {
                                        ui.label(RichText::new("🐹").size(48.0));
                                        ui.label(RichText::new("*chomp chomp*").size(16.0).color(TEAL));
                                    });
                                } else {
                                    ui.label(RichText::new("No content extracted yet").color(Color32::GRAY).size(14.0));
                                }
                            });
                        }
                    });
                });
            } else {
                // Welcome screen
                ui.vertical_centered(|ui| {
                    ui.add_space(100.0);
                    ui.label(RichText::new("🐹").size(64.0));
                    ui.add_space(20.0);
                    ui.label(RichText::new("Welcome to CHONKER3!").size(24.0).color(TEAL));
                    ui.add_space(20.0);
                    ui.label(RichText::new(&self.status_message).size(18.0));
                });
            }
        });
    }
}

fn main() -> Result<(), eframe::Error> {
    env_logger::init();
    
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1200.0, 800.0])
            .with_min_inner_size([800.0, 600.0])
            .with_icon(load_icon()),
        ..Default::default()
    };
    
    eframe::run_native(
        "CHONKER3 - Sacred Document Chomper",
        options,
        Box::new(|cc| {
            egui_extras::install_image_loaders(&cc.egui_ctx);
            Ok(Box::new(Chonker3App::new(cc)))
        }),
    )
}

fn load_icon() -> egui::IconData {
    // Create a hamster face icon like the Google emoji
    let mut rgba = vec![0u8; 32 * 32 * 4];
    
    // Fill with transparency first
    for i in (0..rgba.len()).step_by(4) {
        rgba[i + 3] = 0; // Alpha = 0 (transparent)
    }
    
    // Orange-brown color for hamster
    let hamster_color = (255, 178, 102); // #FFB266
    let inner_ear_color = (255, 204, 153); // #FFCC99
    let eye_color = (0, 0, 0); // Black
    let nose_color = (51, 51, 51); // Dark gray
    
    // Draw main head (wider oval)
    let center_x = 16;
    let center_y = 17;
    
    for y in 0..32 {
        for x in 0..32 {
            let dx = (x as f32 - center_x as f32) / 1.2;
            let dy = y as f32 - center_y as f32;
            let dist_sq = dx * dx + dy * dy;
            
            if dist_sq <= 100.0 { // radius ~10 adjusted for oval
                let idx = (y * 32 + x) * 4;
                rgba[idx] = hamster_color.0;
                rgba[idx + 1] = hamster_color.1;
                rgba[idx + 2] = hamster_color.2;
                rgba[idx + 3] = 255;
            }
        }
    }
    
    // Draw ears (rounded triangles)
    for (ear_x, ear_y) in [(9, 9), (23, 9)] {
        // Outer ear
        for y in 0..32 {
            for x in 0..32 {
                let dx = x as i32 - ear_x;
                let dy = y as i32 - ear_y;
                let dist_sq = dx * dx + dy * dy;
                
                if dist_sq <= 25 && y < ear_y as usize { // radius = 5, only upper half
                    let idx = (y * 32 + x) * 4;
                    rgba[idx] = hamster_color.0;
                    rgba[idx + 1] = hamster_color.1;
                    rgba[idx + 2] = hamster_color.2;
                    rgba[idx + 3] = 255;
                }
            }
        }
        
        // Inner ear (smaller, lighter circle)
        for y in 0..32 {
            for x in 0..32 {
                let dx = x as i32 - ear_x;
                let dy = y as i32 - ear_y;
                let dist_sq = dx * dx + dy * dy;
                
                if dist_sq <= 9 && y < ear_y as usize { // radius = 3
                    let idx = (y * 32 + x) * 4;
                    rgba[idx] = inner_ear_color.0;
                    rgba[idx + 1] = inner_ear_color.1;
                    rgba[idx + 2] = inner_ear_color.2;
                    rgba[idx + 3] = 255;
                }
            }
        }
    }
    
    // Draw eyes (black dots)
    for (eye_x, eye_y) in [(12, 16), (20, 16)] {
        for y in 0..32 {
            for x in 0..32 {
                let dx = x as i32 - eye_x;
                let dy = y as i32 - eye_y;
                let dist_sq = dx * dx + dy * dy;
                
                if dist_sq <= 4 { // radius = 2
                    let idx = (y * 32 + x) * 4;
                    rgba[idx] = eye_color.0;
                    rgba[idx + 1] = eye_color.1;
                    rgba[idx + 2] = eye_color.2;
                    rgba[idx + 3] = 255;
                }
            }
        }
    }
    
    // Draw nose (small oval)
    let nose_x = 16;
    let nose_y = 20;
    for y in 0..32 {
        for x in 0..32 {
            let dx = x as i32 - nose_x;
            let dy = (y as i32 - nose_y) * 2; // Make it wider
            let dist_sq = dx * dx + dy * dy;
            
            if dist_sq <= 4 { // Small nose
                let idx = (y * 32 + x) * 4;
                rgba[idx] = nose_color.0;
                rgba[idx + 1] = nose_color.1;
                rgba[idx + 2] = nose_color.2;
                rgba[idx + 3] = 255;
            }
        }
    }
    
    // Draw white cheek patches
    for (cheek_x, cheek_y) in [(7, 19), (25, 19)] {
        for y in 0..32 {
            for x in 0..32 {
                let dx = x as i32 - cheek_x;
                let dy = y as i32 - cheek_y;
                let dist_sq = dx * dx + dy * dy;
                
                if dist_sq <= 16 { // radius = 4
                    let idx = (y * 32 + x) * 4;
                    // Mix with existing color for a lighter patch
                    rgba[idx] = ((rgba[idx] as u16 + 255) / 2) as u8;
                    rgba[idx + 1] = ((rgba[idx + 1] as u16 + 255) / 2) as u8;
                    rgba[idx + 2] = ((rgba[idx + 2] as u16 + 255) / 2) as u8;
                }
            }
        }
    }
    
    egui::IconData {
        rgba,
        width: 32,
        height: 32,
    }
}