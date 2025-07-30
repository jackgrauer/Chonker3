//! Skia document canvas widget for egui

use egui::{Widget, Response, Ui, Sense, Color32, FontId, Pos2, Align2};
use crate::types::DocumentState;
use super::pdf_renderer::SkiaRenderer;

pub struct SkiaDocumentCanvas {
    document_state: DocumentState,
    renderer: Option<SkiaRenderer>,
    selected_text: String,
}

impl SkiaDocumentCanvas {
    pub fn new(document_state: DocumentState) -> Self {
        Self {
            document_state,
            renderer: None,
            selected_text: String::new(),
        }
    }
    
    pub fn with_zoom(mut self, zoom: f32) -> Self {
        self.document_state.zoom = zoom;
        self
    }
}

impl Widget for SkiaDocumentCanvas {
    fn ui(mut self, ui: &mut Ui) -> Response {
        let (rect, response) = ui.allocate_exact_size(
            ui.available_size(), 
            Sense::hover().union(Sense::drag()).union(Sense::click())
        );
        
        if ui.is_rect_visible(rect) {
            // Draw white background
            ui.painter().rect_filled(
                rect,
                0.0,
                Color32::from_gray(250),
            );
            
            let width = rect.width() as u32;
            let height = rect.height() as u32;
            
            // Skip if size is too small
            if width < 10 || height < 10 {
                return response;
            }
            
            // Create renderer if needed
            if self.renderer.is_none() {
                self.renderer = Some(SkiaRenderer::new(width, height));
            }
            
            
            // Render the document
            if let Some(renderer) = &mut self.renderer {
                // Calculate scale to fit content
                let scale = (rect.width() / 612.0).min(rect.height() / 792.0) * self.document_state.zoom;
                renderer.set_scale(scale);
                
                // Set pan offset from document state
                let offset = self.document_state.offset;
                
                // Add base offset plus pan offset
                renderer.set_offset((20.0 + offset.0, 50.0 + offset.1));
                
                // Skip the skia rendering entirely - we'll just use egui for text
                // This gives us a clean white background
            }
            
            // Draw status overlay with interaction feedback
            let status_color = if response.dragged() {
                Color32::from_rgb(59, 130, 246) // Blue when dragging
            } else if response.hovered() {
                Color32::from_gray(80) // Darker when hovering
            } else {
                Color32::from_gray(100) // Normal
            };
            
            ui.painter().text(
                Pos2::new(rect.left() + 10.0, rect.top() + 10.0),
                Align2::LEFT_TOP,
                format!("🎨 Skia Renderer - {} items | Zoom: {:.0}%", 
                    self.document_state.items.len(),
                    self.document_state.zoom * 100.0),
                FontId::proportional(12.0),
                status_color,
            );
            
            // Show drag hint when hovering
            if response.hovered() && !response.dragged() {
                ui.painter().text(
                    Pos2::new(rect.left() + 10.0, rect.top() + 25.0),
                    Align2::LEFT_TOP,
                    "Drag to pan • Cmd+scroll to zoom",
                    FontId::proportional(10.0),
                    Color32::from_gray(120),
                );
            }
            
            // Render actual text on top of the rectangles
            self.render_text_overlay(ui, rect);
            
            // Handle text selection
            if response.clicked() {
                if let Some(pos) = response.interact_pointer_pos() {
                    self.handle_click(ui, rect, pos);
                }
            }
            
            // Show copied text notification
            if !self.selected_text.is_empty() {
                ui.painter().text(
                    Pos2::new(rect.center().x, rect.bottom() - 30.0),
                    Align2::CENTER_BOTTOM,
                    format!("📋 Copied: {}", self.selected_text),
                    FontId::proportional(12.0),
                    Color32::from_rgb(16, 185, 129),
                );
            }
        }
        
        response
    }
}

impl SkiaDocumentCanvas {
    fn render_text_overlay(&self, ui: &mut Ui, rect: egui::Rect) {
        // Calculate scale and offset
        let scale = (rect.width() / 612.0).min(rect.height() / 792.0) * self.document_state.zoom;
        
        let offset = self.document_state.offset;
        
        let base_offset = (20.0 + offset.0, 50.0 + offset.1);
        
        // Render each text item
        for (idx, item) in self.document_state.items.iter().enumerate() {
            // Push unique ID for this item to avoid widget ID collisions
            ui.push_id(format!("text_item_{}_{}", item.id, idx), |ui| {
                // Calculate screen position relative to the canvas
                let x = base_offset.0 + (item.bbox.left as f32 * scale);
                // PDF coordinates are bottom-left origin, convert to top-left for screen
                // Assume standard page height of 792 points (US Letter)
                let pdf_y = 792.0 - item.bbox.top as f32; // Convert from bottom-left to top-left
                let y = base_offset.1 + (pdf_y * scale);
                let width = item.bbox.width as f32 * scale;
                let height = item.bbox.height.abs() as f32 * scale; // Use absolute value since height can be negative
                
                // Skip if outside visible area (x,y are relative to canvas origin)
                if x + width < 0.0 || x > rect.width() ||
                   y + height < 0.0 || y > rect.height() {
                    return;
                }
                
                // Use black for all text for now - we can add colors later
                let color = Color32::from_gray(20);
                
                // Choose font size
                let font_size = (item.font_size * scale).clamp(8.0, 100.0);
                let font_id = match &item.item_type {
                    crate::types::ItemType::Title => FontId::proportional(font_size * 1.2),
                    crate::types::ItemType::Header => FontId::proportional(font_size * 1.1),
                    _ => FontId::proportional(font_size),
                };
                
                
                // Draw the text with wrapping and clipping
                let max_width = width;
                
                // Create clipped painter to ensure text stays in bounds
                // Use a slightly larger clip rect to prevent cutting off descenders/ascenders
                let text_padding = 3.0; // Extra space for text rendering
                let clip_rect = egui::Rect::from_min_size(
                    Pos2::new(x + rect.left(), y + rect.top() - text_padding),
                    egui::Vec2::new(width, height + text_padding * 2.0)
                );
                let clipped_painter = ui.painter().with_clip_rect(clip_rect);
                
                // Layout text with proper line spacing
                let galley = clipped_painter.layout(
                    item.content.clone(),
                    font_id,
                    color,
                    max_width,
                );
                
                // Render the text - position slightly lower to center in expanded area
                clipped_painter.galley(
                    Pos2::new(x + rect.left(), y + rect.top()),
                    galley,
                    color,
                );
            });
        }
    }
    
    fn handle_click(&mut self, ui: &Ui, rect: egui::Rect, click_pos: Pos2) {
        // Calculate scale and offset
        let scale = (rect.width() / 612.0).min(rect.height() / 792.0) * self.document_state.zoom;
        
        let offset = self.document_state.offset;
        
        let base_offset = (20.0 + offset.0, 50.0 + offset.1);
        
        // Check which text item was clicked
        for item in &self.document_state.items {
            let x = base_offset.0 + (item.bbox.left as f32 * scale) + rect.left();
            // PDF coordinates are bottom-left origin, convert to top-left for screen
            let pdf_y = 792.0 - item.bbox.top as f32;
            let y = base_offset.1 + (pdf_y * scale) + rect.top();
            let width = item.bbox.width as f32 * scale;
            let height = item.bbox.height.abs() as f32 * scale;
            
            let item_rect = egui::Rect::from_min_size(
                Pos2::new(x, y),
                egui::Vec2::new(width, height)
            );
            
            if item_rect.contains(click_pos) {
                // Copy text to clipboard
                self.selected_text = item.content.clone();
                ui.ctx().copy_text(item.content.clone());
                
                // Clear the notification after a delay
                ui.ctx().request_repaint_after(std::time::Duration::from_secs(2));
                break;
            }
        }
    }
}