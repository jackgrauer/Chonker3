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
        // Calculate the actual size needed for the PDF page
        let page_width = self.document_state.page_size.0 * self.document_state.zoom;
        let page_height = self.document_state.page_size.1 * self.document_state.zoom;
        
        // Add some padding
        let canvas_size = egui::Vec2::new(
            page_width + 40.0,  // 20px padding on each side
            page_height + 80.0  // Extra padding for status text
        );
        
        // Allocate the full size needed for the page
        let (rect, response) = ui.allocate_exact_size(
            canvas_size, 
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
                let scale = self.document_state.zoom;
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
        // Use zoom directly as scale since we're allocating the proper size
        let scale = self.document_state.zoom;
        let offset = self.document_state.offset;
        let base_offset = (20.0 + offset.0, 50.0 + offset.1);
        
        for (idx, item) in self.document_state.items.iter().enumerate() {
            ui.push_id(format!("text_item_{}_{}", item.id, idx), |ui| {
                // Apply any custom offset for this item
                let item_offset = self.document_state.item_offsets.get(&item.id)
                    .copied()
                    .unwrap_or((0.0, 0.0));
                
                // Calculate position - coordinates are already in top-left origin
                let x = base_offset.0 + (item.bbox.left as f32 * scale) + item_offset.0;
                let y = base_offset.1 + (item.bbox.top as f32 * scale) + item_offset.1;
                
                // Determine if this needs wrapping
                let needs_wrapping = item.content.len() > 50 || 
                                    item.content.contains(". ") ||
                                    item.content.contains("must be signed");
                
                // Calculate max width for text
                let available_width = rect.width() - x - 20.0; // Leave right margin
                
                // Use bbox width directly for more accurate positioning
                let bbox_width = item.bbox.width as f32 * scale;
                let max_width = if needs_wrapping {
                    // For long text that needs wrapping
                    bbox_width.max(400.0)
                } else {
                    // For normal text, use the bbox width with some flexibility
                    // This helps maintain the original PDF layout
                    bbox_width * 1.1
                };
                
                // Check if this item is in search results
                let is_search_match = self.document_state.search_results.contains(&item.id);
                
                // Font setup with bold/italic support and form-specific styling
                // Use a more reasonable font size calculation
                let base_font_size_raw = if item.font_size > 0.0 {
                    item.font_size * scale
                } else {
                    12.0 * scale // Default font size
                };
                
                let font_size = base_font_size_raw.clamp(10.0, 24.0); // More reasonable range
                let base_font_size = match &item.item_type {
                    crate::types::ItemType::Title => font_size * 1.2,
                    crate::types::ItemType::Header => font_size * 1.1,
                    crate::types::ItemType::FormLabel => font_size,
                    crate::types::ItemType::FormField => font_size * 0.95,
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
                    match &item.item_type {
                        crate::types::ItemType::FormLabel => Color32::from_rgb(0, 0, 139), // Dark blue for form labels
                        crate::types::ItemType::FormField => Color32::from_gray(60), // Dark gray for form fields
                        crate::types::ItemType::Checkbox => Color32::from_gray(40), // Darker for checkboxes
                        _ => Color32::from_gray(20),
                    }
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
                job.wrap.max_rows = 10; // Allow text to wrap to multiple lines
                
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
                
                // Special rendering for checkboxes
                if matches!(item.item_type, crate::types::ItemType::Checkbox) {
                    // Draw checkbox as a square
                    let checkbox_size = base_font_size * 0.8;
                    let checkbox_rect = egui::Rect::from_min_size(
                        Pos2::new(x + rect.left(), y + rect.top()),
                        egui::Vec2::splat(checkbox_size)
                    );
                    
                    // Draw checkbox outline
                    ui.painter().rect_stroke(
                        checkbox_rect,
                        2.0,
                        egui::Stroke::new(1.5, color)
                    );
                    
                    // Draw checkmark if checked
                    if item.content.contains('x') || item.content.contains('X') || 
                       item.content.contains('☑') || item.content.contains('■') {
                        // Draw checkmark
                        let check_points = vec![
                            Pos2::new(checkbox_rect.left() + checkbox_size * 0.2, 
                                     checkbox_rect.center().y),
                            Pos2::new(checkbox_rect.center().x - checkbox_size * 0.1, 
                                     checkbox_rect.bottom() - checkbox_size * 0.3),
                            Pos2::new(checkbox_rect.right() - checkbox_size * 0.2, 
                                     checkbox_rect.top() + checkbox_size * 0.3),
                        ];
                        ui.painter().line_segment(
                            [check_points[0], check_points[1]],
                            egui::Stroke::new(2.0, color)
                        );
                        ui.painter().line_segment(
                            [check_points[1], check_points[2]],
                            egui::Stroke::new(2.0, color)
                        );
                    }
                } else {
                    // Draw the text normally
                    ui.painter().galley(
                        Pos2::new(x + rect.left(), y + rect.top()),
                        galley.clone(),
                        color,
                    );
                }
                
                // Add some padding to prevent overlapping
                let padding = 2.0;
                
                // Always allow interaction
                let item_rect = egui::Rect::from_min_size(
                    Pos2::new(x + rect.left(), y + rect.top()),
                    egui::Vec2::new(galley.rect.width() + padding * 2.0, text_height + padding * 2.0)
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