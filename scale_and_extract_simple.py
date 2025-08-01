#!/usr/bin/env python3
"""
Simple approach: Convert PDF to images at 2x resolution, then back to PDF
"""
import subprocess
import sys
from pathlib import Path
import tempfile
import shutil

def scale_pdf_simple(input_pdf, scale_factor=2.0):
    """Scale PDF by converting to high-res images and back"""
    input_path = Path(input_pdf)
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        print(f"📐 Scaling PDF by {scale_factor}x using high-res conversion...")
        
        # Calculate DPI (standard PDF is 72 DPI, so 2x = 144 DPI)
        dpi = int(72 * scale_factor)
        
        # Use sips (built into macOS) to convert PDF pages to images
        # First, convert PDF to images at high resolution
        print(f"  Converting at {dpi} DPI...")
        
        # Try using sips first (macOS built-in)
        result = subprocess.run([
            'sips', '-s', 'format', 'png', 
            '--resampleHeightWidthMax', str(int(2000 * scale_factor)),
            str(input_pdf),
            '--out', str(temp_dir / 'page.png')
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            # Fallback: Use Python to render at higher resolution
            print("  Using Python PDF rendering...")
            
            # Import pypdfium2 from venv
            sys.path.insert(0, '.venv/lib/python3.13/site-packages')
            import pypdfium2 as pdfium
            
            pdf = pdfium.PdfDocument(str(input_pdf))
            
            # Save each page as high-res image
            for i in range(len(pdf)):
                page = pdf[i]
                
                # Render at higher scale
                bitmap = page.render(scale=scale_factor)
                image = bitmap.to_pil()
                image.save(temp_dir / f'page_{i:03d}.png')
                print(f"    ✓ Rendered page {i+1} at {scale_factor}x")
            
            pdf.close()
        
        # Create output path
        output_pdf = input_path.parent / f"{input_path.stem}_scaled_{scale_factor}x.pdf"
        
        # Convert images back to PDF (images will maintain their resolution)
        print(f"  Converting back to PDF...")
        
        # Get all PNG files
        png_files = sorted(temp_dir.glob('*.png'))
        
        if png_files:
            # Use sips to create PDF from images
            subprocess.run([
                'sips', '-s', 'format', 'pdf',
                str(png_files[0]),
                '--out', str(output_pdf)
            ], capture_output=True)
            
            print(f"💾 Saved scaled PDF to: {output_pdf}")
            return str(output_pdf)
        else:
            print("❌ No images were created")
            return None
            
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

def extract_and_analyze(pdf_path):
    """Extract with Docling and analyze results"""
    print(f"\n🔍 Extracting with Docling (OCR enabled)...")
    
    output_json = f"scaled_extraction.json"
    
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
        
        # Look for specific problematic text
        print(f"\n🔍 Checking key text:")
        
        for item in data['items']:
            content = item.get('content', '')
            
            # Check address
            if 'University' in content:
                print(f"  📍 Address: '{content}'")
                # Check if there's more address info nearby
                bbox = item.get('bbox', {})
                if bbox:
                    for other in data['items']:
                        other_bbox = other.get('bbox', {})
                        if (other_bbox and 
                            abs(other_bbox.get('left', 0) - bbox.get('left', 0)) < 50 and
                            abs(other_bbox.get('top', 0) - bbox.get('top', 0)) < 30 and
                            other != item):
                            print(f"     → Nearby: '{other.get('content', '')}'")
            
            # Check registration text
            if 'REGISTRAT' in content.upper():
                print(f"  📝 Registration: '{content}'")
        
        return output_json
    else:
        print(f"❌ Extraction failed: {result.stderr}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python scale_and_extract_simple.py <input.pdf> [scale_factor]")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    scale_factor = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    
    # Scale the PDF
    scaled_pdf = scale_pdf_simple(input_pdf, scale_factor)
    
    if scaled_pdf:
        # Extract and analyze
        extract_and_analyze(scaled_pdf)
    else:
        print("❌ Failed to scale PDF")

if __name__ == "__main__":
    main()