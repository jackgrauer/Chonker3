#!/usr/bin/env python3
"""
Enhanced Chonker2 with preprocessing and post-processing for better OCR
"""
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

# Import the original chonker2
sys.path.insert(0, str(Path(__file__).parent))
from chonker2 import Chonker2

class EnhancedChonker2(Chonker2):
    """Enhanced version with preprocessing for better OCR"""
    
    def __init__(self, verbose: bool = False, preprocess: bool = True):
        super().__init__(verbose)
        self.preprocess = preprocess
        
        # Set up more detailed logging
        if verbose:
            import logging
            # Configure root logger to show more details
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                force=True
            )
    
    def enhance_image(self, image_path, output_path):
        """Apply image enhancement for better OCR"""
        img = Image.open(image_path)
        
        # Convert to grayscale if not already
        if img.mode != 'L':
            img = img.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)
        
        # Apply unsharp mask for edge enhancement
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        
        # Convert to numpy array for processing
        img_array = np.array(img)
        
        # Simple adaptive thresholding
        threshold = np.mean(img_array) - 10
        img_array = ((img_array > threshold) * 255).astype(np.uint8)
        
        img = Image.fromarray(img_array)
        
        # Save enhanced image
        img.save(output_path, dpi=(300, 300))
        
        return output_path
    
    def preprocess_pdf(self, input_pdf):
        """Preprocess PDF for better OCR"""
        if not self.preprocess:
            return input_pdf
            
        input_path = Path(input_pdf)
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            self.logger.info("Preprocessing PDF for enhanced OCR...")
            
            # Import pypdfium2
            import pypdfium2 as pdfium
            
            pdf = pdfium.PdfDocument(str(input_pdf))
            enhanced_images = []
            
            # Process each page
            for i in range(len(pdf)):
                page = pdf[i]
                
                # Render at high resolution (300 DPI = ~4.17x scale)
                bitmap = page.render(scale=4.17)
                image = bitmap.to_pil()
                
                # Save original high-res image
                orig_path = temp_dir / f'page_{i:03d}_orig.png'
                image.save(orig_path)
                
                # Enhance the image
                enhanced_path = temp_dir / f'page_{i:03d}_enhanced.png'
                self.enhance_image(orig_path, enhanced_path)
                enhanced_images.append(enhanced_path)
                
                self.logger.info(f"Enhanced page {i+1}")
            
            pdf.close()
            
            # Convert enhanced images back to PDF
            self.logger.info("Creating enhanced PDF...")
            
            if enhanced_images:
                # Use PIL to create PDF from images
                images = [Image.open(img_path) for img_path in enhanced_images]
                
                # Create temp enhanced PDF
                enhanced_pdf = temp_dir / f"{input_path.stem}_enhanced.pdf"
                
                # Save as PDF
                images[0].save(
                    enhanced_pdf,
                    "PDF",
                    save_all=True,
                    append_images=images[1:] if len(images) > 1 else [],
                    resolution=300.0
                )
                
                # Copy to a persistent location before cleanup
                output_pdf = input_path.parent / f"{input_path.stem}_enhanced.pdf"
                shutil.copy2(enhanced_pdf, output_pdf)
                
                self.logger.info(f"Created enhanced PDF: {output_pdf}")
                return str(output_pdf)
            
        except Exception as e:
            self.logger.error(f"Preprocessing failed: {e}")
            return input_pdf
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def merge_nearby_text(self, items, merge_threshold=20):
        """Merge text items that are close together"""
        if not items:
            return items
            
        # Sort items by page, then by top position, then by left position
        sorted_items = sorted(items, key=lambda x: (
            x.get('page', 0),
            -x.get('bbox', {}).get('top', 0),
            x.get('bbox', {}).get('left', 0)
        ))
        
        merged_items = []
        current_group = [sorted_items[0]]
        
        for i in range(1, len(sorted_items)):
            item = sorted_items[i]
            last_item = current_group[-1]
            
            # Check if items should be merged
            if (item.get('page') == last_item.get('page') and
                item.get('bbox') and last_item.get('bbox')):
                
                # Calculate vertical and horizontal distance
                v_dist = abs(item['bbox']['top'] - last_item['bbox']['top'])
                h_dist = item['bbox']['left'] - (last_item['bbox']['right'])
                
                # Merge if on same line (small vertical distance) and close horizontally
                if v_dist < 5 and 0 <= h_dist < merge_threshold:
                    current_group.append(item)
                else:
                    # Process current group
                    if len(current_group) > 1:
                        merged_items.append(self.merge_group(current_group))
                    else:
                        merged_items.append(current_group[0])
                    current_group = [item]
            else:
                # Different page or no bbox info
                if len(current_group) > 1:
                    merged_items.append(self.merge_group(current_group))
                else:
                    merged_items.append(current_group[0])
                current_group = [item]
        
        # Process last group
        if len(current_group) > 1:
            merged_items.append(self.merge_group(current_group))
        else:
            merged_items.append(current_group[0])
        
        return merged_items
    
    def merge_group(self, group):
        """Merge a group of items into a single item"""
        # Combine content with spaces
        content = ' '.join(item.get('content', '') for item in group)
        
        # Calculate combined bbox
        left = min(item['bbox']['left'] for item in group if item.get('bbox'))
        right = max(item['bbox']['right'] for item in group if item.get('bbox'))
        top = max(item['bbox']['top'] for item in group if item.get('bbox'))
        bottom = min(item['bbox']['bottom'] for item in group if item.get('bbox'))
        
        # Use first item as template
        merged = group[0].copy()
        merged['content'] = content
        merged['bbox'] = {
            'left': left,
            'top': top,
            'right': right,
            'bottom': bottom,
            'width': right - left,
            'height': abs(top - bottom),
            'coord_origin': group[0]['bbox'].get('coord_origin', 'BOTTOMLEFT')
        }
        
        return merged
    
    def extract_to_json(self, pdf_path: str, output_path: str = None):
        """Extract with preprocessing and post-processing"""
        # Preprocess PDF if enabled
        processed_pdf = self.preprocess_pdf(pdf_path)
        
        # Add extra logging for OCR engine detection
        import logging
        # Temporarily increase logging level to see OCR details
        docling_logger = logging.getLogger('docling')
        original_level = docling_logger.level
        docling_logger.setLevel(logging.DEBUG)
        
        # Also log pypdftools and other OCR-related modules
        for logger_name in ['docling.backend', 'docling.pipeline', 'pypdfium2', 'ocrmac', 'tesseract', 'rapidocr', 'easyocr']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
        
        # Extract using parent class
        result = super().extract_to_json(processed_pdf, output_path)
        
        # Restore original logging level
        docling_logger.setLevel(original_level)
        
        # Post-process to merge nearby text
        if result and 'items' in result:
            self.logger.info(f"Merging nearby text items...")
            original_count = len(result['items'])
            result['items'] = self.merge_nearby_text(result['items'])
            merged_count = len(result['items'])
            self.logger.info(f"Merged {original_count - merged_count} items")
        
        return result

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Enhanced Chonker2 with preprocessing for better OCR'
    )
    parser.add_argument('input', help='PDF file to process')
    parser.add_argument('-o', '--output', help='Output JSON file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--no-preprocess', action='store_true', help='Disable preprocessing')
    
    args = parser.parse_args()
    
    # Create enhanced extractor
    extractor = EnhancedChonker2(
        verbose=args.verbose,
        preprocess=not args.no_preprocess
    )
    
    # Process file
    extractor.extract_to_json(args.input, args.output)

if __name__ == '__main__':
    main()