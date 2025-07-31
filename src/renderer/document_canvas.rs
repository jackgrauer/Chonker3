//! Document canvas widget for egui

use egui::{Widget, Response, Ui, Sense, Color32, FontId, Pos2, Align2};
use crate::types::DocumentState;

pub struct DocumentCanvas {
    document_state: DocumentState,
    copied_text: Option<String>,
}

impl DocumentCanvas {
    pub fn new(document_state: DocumentState) -> Self {
        Self {
            document_state,
            copied_text: None,
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
            Sense::hover()
        );
        
        if ui.is_rect_visible(rect) {
            // Draw white background
            ui.painter().rect_filled(
                rect,
                0.0,
                Color32::from_gray(250),
            );
            
            // Draw status overlay
            let status_color = if response.hovered() {
                Color32::from_gray(80) // Darker when hovering
            } else {
                Color32::from_gray(100) // Normal
            };
            
            // Show column info in status
            let column_info = if self.document_state.column_count > 1 {
                format!(" | {} columns", self.document_state.column_count)
            } else {
                String::new()
            };
            
            ui.painter().text(
                Pos2::new(rect.left() + 10.0, rect.top() + 10.0),
                Align2::LEFT_TOP,
                format!("📄 {} items | Zoom: {:.0}%{}", 
                    self.document_state.items.len(),
                    self.document_state.zoom * 100.0,
                    column_info),
                FontId::proportional(12.0),
                status_color,
            );
            
            // Draw column boundaries if in multi-column layout
            if self.document_state.column_count > 1 && !self.document_state.column_boundaries.is_empty() {
                let scale = (rect.width() / 612.0).min(rect.height() / 792.0) * self.document_state.zoom;
                let base_offset = (20.0 + self.document_state.offset.0, 50.0 + self.document_state.offset.1);
                
                for boundary_x in &self.document_state.column_boundaries {
                    let x = base_offset.0 + (boundary_x * scale) + rect.left();
                    
                    // Draw subtle vertical line
                    ui.painter().line_segment(
                        [
                            Pos2::new(x, rect.top() + 50.0),
                            Pos2::new(x, rect.bottom() - 20.0)
                        ],
                        egui::Stroke::new(1.0, Color32::from_rgba_premultiplied(59, 130, 246, 60))
                    );
                }
            }
            
            // Show interaction hint when hovering
            if response.hovered() {
                ui.painter().text(
                    Pos2::new(rect.left() + 10.0, rect.top() + 25.0),
                    Align2::LEFT_TOP,
                    "Click to copy • Cmd+scroll to zoom",
                    FontId::proportional(10.0),
                    Color32::from_gray(120),
                );
            }
            
            // Render text items
            self.render_text_overlay(ui, rect);
            
            // Show copied text notification
            if let Some(copy_text) = &self.copied_text {
                let preview = if copy_text.len() > 50 {
                    format!("{}...", &copy_text[..50])
                } else {
                    copy_text.clone()
                };
                
                ui.painter().text(
                    Pos2::new(rect.center().x, rect.bottom() - 30.0),
                    Align2::CENTER_BOTTOM,
                    format!("📋 Copied: {}", preview),
                    FontId::proportional(12.0),
                    Color32::from_rgb(16, 185, 129),
                );
            }
        }
        
        response
    }
}

impl DocumentCanvas {
    fn render_text_overlay(&mut self, ui: &mut Ui, rect: egui::Rect) {
        let scale = (rect.width() / 612.0).min(rect.height() / 792.0) * self.document_state.zoom;
        let offset = self.document_state.offset;
        let base_offset = (20.0 + offset.0, 50.0 + offset.1);
        
        for (idx, item) in self.document_state.items.iter().enumerate() {
            ui.push_id(format!("text_item_{}_{}", item.id, idx), |ui| {
                // Apply any custom offset for this item
                let item_offset = self.document_state.item_offsets.get(&item.id)
                    .copied()
                    .unwrap_or((0.0, 0.0));
                
                // Calculate position
                let x = base_offset.0 + (item.bbox.left as f32 * scale) + item_offset.0;
                let pdf_y = 792.0 - item.bbox.top as f32;
                let y = base_offset.1 + (pdf_y * scale) + item_offset.1;
                
                // Determine if this needs wrapping
                let needs_wrapping = item.content.len() > 50 || 
                                    item.content.contains(". ") ||
                                    item.content.contains("must be signed");
                
                // Calculate max width for text
                let available_width = rect.width() - x - 20.0; // Leave right margin
                let max_width = if needs_wrapping {
                    available_width.min(500.0) // Force wrap at reasonable width
                } else {
                    (item.bbox.width as f32 * scale * 1.2).max(available_width)
                };
                
                // Check if this item is in search results
                let is_search_match = self.document_state.search_results.contains(&item.id);
                
                // Font setup with bold/italic support
                let font_size = (item.font_size * scale).clamp(8.0, 100.0);
                let base_font_size = match &item.item_type {
                    crate::types::ItemType::Title => font_size * 1.2,
                    crate::types::ItemType::Header => font_size * 1.1,
                    _ => font_size,
                };
                
                // Apply font style
                let font_id = if item.bold && item.italic {
                    FontId::new(base_font_size, egui::FontFamily::Proportional)
                } else if item.bold {
                    FontId::new(base_font_size, egui::FontFamily::Proportional)
                } else if item.italic {
                    FontId::new(base_font_size, egui::FontFamily::Proportional)
                } else {
                    FontId::proportional(base_font_size)
                };
                let color = if is_search_match {
                    Color32::from_rgb(255, 165, 0) // Orange for highlights
                } else {
                    Color32::from_gray(20)
                };
                
                // Get text to display (with overrides)
                let text = self.document_state.item_text_overrides.get(&item.id)
                    .cloned()
                    .unwrap_or_else(|| item.content.clone());
                
                // Create a layout job for styled text
                let mut job = egui::text::LayoutJob::single_section(
                    text.clone(),
                    egui::text::TextFormat {
                        font_id: font_id.clone(),
                        color,
                        // Apply text decorations
                        italics: item.italic,
                        // Note: egui doesn't have a direct bold property in TextFormat
                        // Bold is handled through font selection
                        ..Default::default()
                    }
                );
                job.wrap.max_width = max_width;
                job.wrap.break_anywhere = false;
                
                // Layout text - this will calculate the actual height needed
                let galley = ui.fonts(|f| f.layout_job(job));
                
                // Get the actual height the text needs
                let text_height = galley.rect.height();
                
                // Draw highlight background if this is a search match
                if is_search_match {
                    ui.painter().rect_filled(
                        egui::Rect::from_min_size(
                            Pos2::new(x + rect.left(), y + rect.top()),
                            egui::Vec2::new(galley.rect.width(), text_height)
                        ),
                        0.0,
                        Color32::from_rgba_premultiplied(255, 255, 0, 60) // Yellow highlight
                    );
                }
                
                // Draw the text - no clipping, let it use the space it needs
                ui.painter().galley(
                    Pos2::new(x + rect.left(), y + rect.top()),
                    galley.clone(),
                    color,
                );
                
                // Always allow interaction
                let item_rect = egui::Rect::from_min_size(
                    Pos2::new(x + rect.left(), y + rect.top()),
                    egui::Vec2::new(galley.rect.width(), text_height)
                );
                
                // Check if pointer is over this item
                let response = ui.interact(item_rect, ui.id().with(item.id.clone()), Sense::click());
                
                // Handle click - copy text
                if response.clicked() {
                    // Get text (with overrides)
                    let text = self.document_state.item_text_overrides.get(&item.id)
                        .cloned()
                        .unwrap_or_else(|| item.content.clone());
                    
                    // Copy text to clipboard
                    ui.ctx().copy_text(text.clone());
                    self.copied_text = Some(text);
                    
                    // Visual feedback
                    ui.ctx().request_repaint_after(std::time::Duration::from_secs(2));
                }
                
                // Draw hover effect
                if response.hovered() {
                    ui.painter().rect_stroke(
                        item_rect.expand(2.0),
                        4.0,
                        egui::Stroke::new(1.0, Color32::from_rgb(59, 130, 246))
                    );
                    
                    // Show pointer cursor
                    ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
                }
            });
        }
    }
}