//! Document canvas widget for egui

use egui::{Widget, Response, Ui, Sense, Color32, FontId, Pos2, Align2};
use crate::types::DocumentState;

pub struct DocumentCanvas {
    document_state: DocumentState,
    selected_text: String,
}

impl DocumentCanvas {
    pub fn new(document_state: DocumentState) -> Self {
        Self {
            document_state,
            selected_text: String::new(),
        }
    }
    
    pub fn with_zoom(mut self, zoom: f32) -> Self {
        self.document_state.zoom = zoom;
        self
    }
}

impl Widget for DocumentCanvas {
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
            
            // Draw status overlay
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
                format!("📄 {} items | Zoom: {:.0}%", 
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
            
            // Render text items
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

impl DocumentCanvas {
    fn render_text_overlay(&self, ui: &mut Ui, rect: egui::Rect) {
        // Calculate scale and offset
        let scale = (rect.width() / 612.0).min(rect.height() / 792.0) * self.document_state.zoom;
        let offset = self.document_state.offset;
        let base_offset = (20.0 + offset.0, 50.0 + offset.1);
        
        // Render each text item
        for (idx, item) in self.document_state.items.iter().enumerate() {
            // Push unique ID for this item to avoid widget ID collisions
            ui.push_id(format!("text_item_{}_{}", item.id, idx), |ui| {
                // Apply any custom offset for this item
                let item_offset = self.document_state.item_offsets.get(&item.id)
                    .copied()
                    .unwrap_or((0.0, 0.0));
                
                // Calculate screen position relative to the canvas
                let x = base_offset.0 + (item.bbox.left as f32 * scale) + item_offset.0;
                // PDF coordinates are bottom-left origin, convert to top-left for screen
                let pdf_y = 792.0 - item.bbox.top as f32;
                let y = base_offset.1 + (pdf_y * scale) + item_offset.1;
                let width = item.bbox.width as f32 * scale;
                let height = item.bbox.height.abs() as f32 * scale;
                
                // Skip if outside visible area
                if x + width < 0.0 || x > rect.width() ||
                   y + height < 0.0 || y > rect.height() {
                    return;
                }
                
                // Check if this item is in search results
                let is_search_match = self.document_state.search_results.contains(&item.id);
                
                // Use different color for search matches
                let color = if is_search_match {
                    Color32::from_rgb(255, 165, 0) // Orange for highlights
                } else {
                    Color32::from_gray(20)
                };
                
                // Choose font size
                let font_size = (item.font_size * scale).clamp(8.0, 100.0);
                let font_id = match &item.item_type {
                    crate::types::ItemType::Title => FontId::proportional(font_size * 1.2),
                    crate::types::ItemType::Header => FontId::proportional(font_size * 1.1),
                    _ => FontId::proportional(font_size),
                };
                
                // Get text to display (with overrides)
                let text = self.document_state.item_text_overrides.get(&item.id)
                    .cloned()
                    .unwrap_or_else(|| item.content.clone());
                
                // Create clipped painter with proper padding to prevent text clipping
                // PDF bounding boxes are often too tight for actual rendered text
                let horizontal_padding = 5.0; // Fixed padding for sides
                let vertical_padding = height * 0.2; // 20% padding for height to handle descenders
                let extra_width = width * 0.1; // 10% extra width for italics and font variations
                
                let clip_rect = egui::Rect::from_min_size(
                    Pos2::new(x + rect.left() - horizontal_padding, y + rect.top() - vertical_padding),
                    egui::Vec2::new(width + extra_width + horizontal_padding * 2.0, height + vertical_padding * 2.0)
                );
                let clipped_painter = ui.painter().with_clip_rect(clip_rect);
                
                // Draw highlight background if this is a search match
                if is_search_match {
                    clipped_painter.rect_filled(
                        clip_rect,
                        0.0,
                        Color32::from_rgba_premultiplied(255, 255, 0, 60) // Yellow highlight
                    );
                }
                
                // Layout and render text
                let galley = clipped_painter.layout(
                    text,
                    font_id,
                    color,
                    width,
                );
                
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
            let item_offset = self.document_state.item_offsets.get(&item.id)
                .copied()
                .unwrap_or((0.0, 0.0));
            
            let x = base_offset.0 + (item.bbox.left as f32 * scale) + rect.left() + item_offset.0;
            let pdf_y = 792.0 - item.bbox.top as f32;
            let y = base_offset.1 + (pdf_y * scale) + rect.top() + item_offset.1;
            let width = item.bbox.width as f32 * scale;
            let height = item.bbox.height.abs() as f32 * scale;
            
            // Use the same expanded bounds for click detection
            let horizontal_padding = 5.0;
            let vertical_padding = height * 0.2;
            let extra_width = width * 0.1;
            
            let item_rect = egui::Rect::from_min_size(
                Pos2::new(x - horizontal_padding, y - vertical_padding),
                egui::Vec2::new(width + extra_width + horizontal_padding * 2.0, height + vertical_padding * 2.0)
            );
            
            if item_rect.contains(click_pos) {
                // Get text (with overrides)
                let text = self.document_state.item_text_overrides.get(&item.id)
                    .cloned()
                    .unwrap_or_else(|| item.content.clone());
                
                // Copy text to clipboard
                self.selected_text = text.clone();
                ui.ctx().copy_text(text);
                
                // Clear the notification after a delay
                ui.ctx().request_repaint_after(std::time::Duration::from_secs(2));
                break;
            }
        }
    }
}