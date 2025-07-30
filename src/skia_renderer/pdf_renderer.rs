//! PDF rendering with tiny-skia

pub struct SkiaRenderer {
    scale: f32,
    offset: (f32, f32),
}

impl SkiaRenderer {
    pub fn new(_width: u32, _height: u32) -> Self {
        Self {
            scale: 1.0,
            offset: (20.0, 50.0), // Default margin
        }
    }
    
    
    pub fn set_scale(&mut self, scale: f32) {
        self.scale = scale;
    }
    
    pub fn set_offset(&mut self, offset: (f32, f32)) {
        self.offset = offset;
    }
}