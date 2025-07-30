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
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentState {
    pub items: Vec<DocumentItem>,
    pub page_size: (f32, f32),
    pub zoom: f32,
    pub offset: (f32, f32),
    pub selected_item: Option<String>,
    pub editing_item: Option<String>,
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
        }
    }
}

