#!/usr/bin/env python3
"""
Preprocess PDF images to improve OCR quality
Applies image enhancement techniques before extraction
"""
import subprocess
import sys
from pathlib import Path
import tempfile
import shutil
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

def enhance_image(image_path, output_path):
    """Apply image enhancement for better OCR"""
    img = Image.open(image_path)
    
    # Convert to grayscale if not already
    if img.mode != 'L':
        img = img.convert('L')
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)  # Increase contrast
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)  # Sharpen
    
    # Apply unsharp mask for edge enhancement
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    
    # Convert to numpy array for processing
    img_array = np.array(img)
    
    # Simple adaptive thresholding without scipy
    # Use a simple threshold to clean up the image
    threshold = np.mean(img_array) - 10
    img_array = ((img_array > threshold) * 255).astype(np.uint8)
    
    img = Image.fromarray(img_array)
    
    # Save enhanced image
    img.save(output_path, dpi=(300, 300))
    
    return output_path

def preprocess_pdf(input_pdf, output_pdf):
    """Preprocess PDF pages for better OCR"""
    input_path = Path(input_pdf)
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        print("🔍 Preprocessing PDF for enhanced OCR...")
        
        # Import pypdfium2
        sys.path.insert(0, '.venv/lib/python3.13/site-packages')
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
            enhance_image(orig_path, enhanced_path)
            enhanced_images.append(enhanced_path)
            
            print(f"  ✓ Enhanced page {i+1}")
        
        pdf.close()
        
        # Convert enhanced images back to PDF
        print("📄 Creating enhanced PDF...")
        
        if enhanced_images:
            # Use PIL to create PDF from images
            images = [Image.open(img_path) for img_path in enhanced_images]
            
            # Save as PDF
            images[0].save(
                output_pdf,
                "PDF",
                save_all=True,
                append_images=images[1:] if len(images) > 1 else [],
                resolution=300.0
            )
            
            print(f"💾 Saved enhanced PDF to: {output_pdf}")
            return output_pdf
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install scipy")
        return None
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

def extract_and_analyze(pdf_path):
    """Extract with Docling and analyze results"""
    print(f"\n🔍 Extracting enhanced PDF with Docling...")
    
    output_json = "enhanced_extraction.json"
    
    # Run extraction
    result = subprocess.run([
        '.venv/bin/python', 'chonker2.py', 
        pdf_path, '-o', output_json
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        # Analyze the output
        import json
        with open(output_json) as f:
            data = json.load(f)
        
        print(f"\n📊 Extraction Results:")
        print(f"  - Total items: {len(data['items'])}")
        print(f"  - Total characters: {sum(len(item.get('content', '')) for item in data['items'])}")
        
        # Look for specific text
        print(f"\n🔍 Checking key content:")
        
        # Find address components
        address_parts = []
        for item in data['items']:
            content = item.get('content', '').strip()
            
            # Look for address components
            if any(addr in content for addr in ['University', 'Avenue', 'Philadelphia', 'PA', '19104']):
                address_parts.append(content)
                print(f"  📍 Address part: '{content}'")
            
            # Check registration text
            if 'REGISTRAT' in content.upper():
                print(f"  📝 Registration: '{content}'")
            
            # Check for title/company name
            if 'Air Management' in content:
                print(f"  🏢 Company: '{content}'")
        
        # Try to reconstruct full address
        if address_parts:
            print(f"\n📍 Address components found: {len(address_parts)}")
            print("  Full address reconstruction:")
            for part in address_parts:
                print(f"    - {part}")
        
        return output_json
    else:
        print(f"❌ Extraction failed: {result.stderr}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python preprocess_and_extract.py <input.pdf>")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    input_path = Path(input_pdf)
    
    # Output paths
    enhanced_pdf = input_path.parent / f"{input_path.stem}_enhanced.pdf"
    
    # Preprocess the PDF
    result = preprocess_pdf(input_pdf, enhanced_pdf)
    
    if result:
        # Extract and analyze
        extract_and_analyze(result)
    else:
        print("❌ Preprocessing failed")

if __name__ == "__main__":
    main()