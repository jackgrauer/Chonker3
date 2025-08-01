//! Shared types for document rendering

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentItem {
    pub id: String,
    pub bbox: BoundingBox,           // PDF coordinates
    pub content: String,
    pub font_size: f32,
    pub color: (u8, u8, u8), // RGB
    pub item_type: ItemType,
    pub bold: bool,
    pub italic: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundingBox {
    pub left: f64,
    pub top: f64,
    pub width: f64,
    pub height: f64,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ItemType {
    Text,
    Title,
    Header,
    Table,
    FormLabel,
    FormField,
    Checkbox,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentState {
    pub items: Vec<DocumentItem>,
    pub page_size: (f32, f32),
    pub zoom: f32,
    pub offset: (f32, f32),
    pub selected_item: Option<String>,
    pub editing_item: Option<String>,
    pub search_query: String,
    pub search_results: Vec<String>, // IDs of matching items
    pub item_offsets: std::collections::HashMap<String, (f32, f32)>,
    pub item_text_overrides: std::collections::HashMap<String, String>,
    pub text_padding_factor: f32, // Multiplier for text bounds padding
    pub edit_mode: bool,
    pub dragging_item: Option<String>, // ID of item being dragged
    pub column_count: usize,
    pub column_boundaries: Vec<f32>, // X coordinates of column boundaries
}

impl Default for DocumentState {
    fn default() -> Self {
        Self {
            items: vec![],
            page_size: (612.0, 792.0),
            zoom: 1.0,
            offset: (0.0, 0.0),
            selected_item: None,
            editing_item: None,
            search_query: String::new(),
            search_results: Vec::new(),
            item_offsets: std::collections::HashMap::new(),
            item_text_overrides: std::collections::HashMap::new(),
            text_padding_factor: 1.0, // Default padding factor
            edit_mode: false,
            dragging_item: None,
            column_count: 1,
            column_boundaries: Vec::new(),
        }
    }
}

