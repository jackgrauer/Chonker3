#!/usr/bin/env python3
"""
Scale PDF pages by rendering them at higher resolution
This improves OCR quality for scanned PDFs
"""
import sys
from PIL import Image
import fitz  # PyMuPDF
from pathlib import Path
import tempfile

def scale_pdf_pages(input_path, output_path, scale_factor=2.0):
    """Scale PDF by rendering pages at higher resolution"""
    print(f"📐 Scaling PDF by {scale_factor}x...")
    
    # Open the PDF
    pdf_doc = fitz.open(input_path)
    new_doc = fitz.open()  # Create new PDF
    
    for page_num in range(len(pdf_doc)):
        page = pdf_doc[page_num]
        
        # Get page dimensions
        rect = page.rect
        width = rect.width
        height = rect.height
        
        # Render page at higher resolution
        mat = fitz.Matrix(scale_factor, scale_factor)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # Create new page with scaled dimensions
        new_page = new_doc.new_page(width=width * scale_factor, height=height * scale_factor)
        
        # Insert the high-res image
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Insert image to fill the page
        new_page.insert_image(new_page.rect, stream=img_bytes.read())
        
        print(f"  ✓ Scaled page {page_num + 1}: {width:.0f}x{height:.0f} → {width*scale_factor:.0f}x{height*scale_factor:.0f}")
    
    # Save the new PDF
    new_doc.save(output_path)
    new_doc.close()
    pdf_doc.close()
    
    print(f"💾 Saved scaled PDF to: {output_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python scale_pdf.py <input.pdf> [scale_factor]")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    scale_factor = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    
    # Output path
    input_path = Path(input_pdf)
    output_path = input_path.parent / f"{input_path.stem}_scaled_{scale_factor}x.pdf"
    
    try:
        import io
        scale_pdf_pages(input_pdf, str(output_path), scale_factor)
        
        # Now extract with Docling
        print(f"\n🔍 Extracting scaled PDF with Docling...")
        import subprocess
        result = subprocess.run([
            sys.executable, 
            "chonker2.py", 
            str(output_path), 
            "-o", 
            f"scaled_extraction_{scale_factor}x.json"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Extraction complete!")
            
            # Analyze results
            import json
            with open(f"scaled_extraction_{scale_factor}x.json") as f:
                data = json.load(f)
            
            print(f"\n📊 Results:")
            print(f"  - Total items: {len(data['items'])}")
            print(f"  - Total characters: {sum(len(item.get('content', '')) for item in data['items'])}")
            
            # Check specific text
            for item in data['items']:
                content = item.get('content', '')
                if 'University' in content:
                    print(f"\n🏢 Address text: '{content}'")
                if 'REGISTRATI' in content:
                    print(f"📝 Registration text: '{content}'")
        else:
            print(f"❌ Extraction failed: {result.stderr}")
            
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install PyMuPDF pillow")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()