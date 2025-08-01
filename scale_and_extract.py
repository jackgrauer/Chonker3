#!/usr/bin/env python3
"""
Scale PDF up before extraction to improve quality
"""

import subprocess
import sys
import os
from pathlib import Path
import tempfile
import json

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import RectangleObject, Transformation
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
    
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

class PDFScaler:
    def __init__(self, scale_factor=2.0):
        self.scale_factor = scale_factor
        
    def scale_with_pymupdf(self, input_path, output_path):
        """Scale PDF using PyMuPDF (best quality)"""
        print(f"🔍 Scaling with PyMuPDF (factor: {self.scale_factor}x)...")
        
        doc = fitz.open(input_path)
        writer = fitz.open()
        
        for page_num, page in enumerate(doc):
            # Get original dimensions
            rect = page.rect
            width = rect.width
            height = rect.height
            
            # Create new page with scaled dimensions
            new_width = width * self.scale_factor
            new_height = height * self.scale_factor
            new_page = writer.new_page(width=new_width, height=new_height)
            
            # Create a matrix for scaling
            mat = fitz.Matrix(self.scale_factor, self.scale_factor)
            
            # Render the original page to a pixmap at higher resolution
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Insert the pixmap into the new page
            new_page.insert_image(new_page.rect, pixmap=pix)
            
            print(f"  ✓ Scaled page {page_num + 1}: {width}x{height} → {new_width}x{new_height}")
            
        writer.save(output_path)
        writer.close()
        doc.close()
        
        return True
        
    def scale_with_pypdf(self, input_path, output_path):
        """Scale PDF using pypdf (may have limitations)"""
        print(f"🔍 Scaling with pypdf (factor: {self.scale_factor}x)...")
        
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        for page_num, page in enumerate(reader.pages):
            # Get page dimensions
            mediabox = page.mediabox
            width = float(mediabox.width)
            height = float(mediabox.height)
            
            # Scale the page
            page.scale_by(self.scale_factor)
            
            # Update media box
            new_width = width * self.scale_factor
            new_height = height * self.scale_factor
            page.mediabox = RectangleObject([0, 0, new_width, new_height])
            
            writer.add_page(page)
            
            print(f"  ✓ Scaled page {page_num + 1}: {width}x{height} → {new_width}x{new_height}")
            
        with open(output_path, 'wb') as f:
            writer.write(f)
            
        return True
        
    def scale_with_ghostscript(self, input_path, output_path):
        """Scale PDF using Ghostscript (most reliable)"""
        print(f"🔍 Scaling with Ghostscript (factor: {self.scale_factor}x)...")
        
        # First get page size
        try:
            result = subprocess.run([
                'gs', '-q', '-dNODISPLAY', '-dBATCH',
                '-c', f'({input_path}) (r) file runpdfbegin 1 1 pdfpagecount {{pdfgetpage /MediaBox get == exit}} for',
            ], capture_output=True, text=True)
            
            # Parse MediaBox output (rough parsing)
            import re
            numbers = re.findall(r'[\d.]+', result.stdout)
            if len(numbers) >= 4:
                width = float(numbers[2])
                height = float(numbers[3])
                new_width = width * self.scale_factor
                new_height = height * self.scale_factor
                
                print(f"  Original size: {width}x{height}")
                print(f"  New size: {new_width}x{new_height}")
            else:
                # Default to letter size
                new_width = 612 * self.scale_factor
                new_height = 792 * self.scale_factor
                
        except:
            # Default to letter size
            new_width = 612 * self.scale_factor
            new_height = 792 * self.scale_factor
        
        # Scale the PDF
        gs_command = [
            'gs',
            '-q',
            '-dNOPAUSE',
            '-dBATCH',
            '-sDEVICE=pdfwrite',
            f'-dDEVICEWIDTHPOINTS={new_width}',
            f'-dDEVICEHEIGHTPOINTS={new_height}',
            '-dFIXEDMEDIA',
            '-dPDFFitPage',
            f'-sOutputFile={output_path}',
            input_path
        ]
        
        result = subprocess.run(gs_command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✓ Scaling successful")
            return True
        else:
            print(f"  ✗ Scaling failed: {result.stderr}")
            return False
            
    def scale_with_imagemagick(self, input_path, output_path):
        """Scale PDF using ImageMagick (converts to images then back)"""
        print(f"🔍 Scaling with ImageMagick (factor: {self.scale_factor}x)...")
        
        density = int(150 * self.scale_factor)  # Base DPI * scale
        
        convert_command = [
            'convert',
            '-density', str(density),
            input_path,
            '-resize', f'{int(self.scale_factor * 100)}%',
            output_path
        ]
        
        result = subprocess.run(convert_command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✓ Scaling successful")
            return True
        else:
            print(f"  ✗ Scaling failed: {result.stderr}")
            return False
            
    def scale_pdf(self, input_path, output_path=None):
        """Scale PDF using best available method"""
        input_path = Path(input_path)
        
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_scaled_{self.scale_factor}x.pdf"
            
        print(f"📄 Input: {input_path}")
        print(f"📤 Output: {output_path}")
        
        # Try methods in order of preference
        methods = []
        
        if HAS_PYMUPDF:
            methods.append(("PyMuPDF", self.scale_with_pymupdf))
        else:
            print("ℹ️  PyMuPDF not installed (best quality scaling)")
            
        # Check for Ghostscript
        if subprocess.run(['which', 'gs'], capture_output=True).returncode == 0:
            methods.append(("Ghostscript", self.scale_with_ghostscript))
        else:
            print("ℹ️  Ghostscript not installed")
            
        if HAS_PYPDF:
            methods.append(("pypdf", self.scale_with_pypdf))
        else:
            print("ℹ️  pypdf not installed")
            
        # Check for ImageMagick
        if subprocess.run(['which', 'convert'], capture_output=True).returncode == 0:
            methods.append(("ImageMagick", self.scale_with_imagemagick))
        else:
            print("ℹ️  ImageMagick not installed")
            
        if not methods:
            print("❌ No PDF scaling tools available!")
            print("Install one of: PyMuPDF, Ghostscript, pypdf, or ImageMagick")
            return None
            
        # Try each method
        for name, method in methods:
            print(f"\n🔧 Trying {name}...")
            try:
                if method(str(input_path), str(output_path)):
                    print(f"✅ Successfully scaled with {name}")
                    return output_path
            except Exception as e:
                print(f"❌ {name} failed: {e}")
                
        print("❌ All scaling methods failed")
        return None

def extract_scaled_pdf(pdf_path, scale_factor=2.0):
    """Scale PDF and extract"""
    scaler = PDFScaler(scale_factor)
    
    # Scale the PDF
    scaled_path = scaler.scale_pdf(pdf_path)
    if not scaled_path:
        print("❌ Failed to scale PDF")
        return None
        
    # Extract from scaled PDF
    print(f"\n📊 Extracting from scaled PDF...")
    
    # Find extractor
    extractors = [
        "pypdfium2_proper_extractor.py",
        "simple_extractor_fixed.py",
        "simple_extractor.py"
    ]
    
    for extractor_name in extractors:
        extractor = Path(extractor_name)
        if extractor.exists():
            print(f"🔧 Using extractor: {extractor_name}")
            
            result = subprocess.run(
                [sys.executable, str(extractor), str(scaled_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Extraction successful")
                
                # Find JSON path in output
                for line in result.stdout.split('\n'):
                    if 'json_path' in line and '.json' in line:
                        import re
                        match = re.search(r'["\']([^"\']*\.json)["\']', line)
                        if match:
                            json_path = match.group(1)
                            
                            # Adjust coordinates back to original scale
                            print(f"\n🔧 Adjusting coordinates back to original scale...")
                            adjust_json_coordinates(json_path, scale_factor)
                            
                            return json_path, scaled_path
                            
            else:
                print(f"❌ Extraction failed: {result.stderr}")
                
    return None, scaled_path

def adjust_json_coordinates(json_path, scale_factor):
    """Adjust coordinates in JSON back to original scale"""
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    # Adjust all bbox coordinates
    for item in data.get('items', []):
        if 'bbox' in item:
            bbox = item['bbox']
            bbox['left'] = bbox.get('left', 0) / scale_factor
            bbox['top'] = bbox.get('top', 0) / scale_factor
            bbox['width'] = bbox.get('width', 0) / scale_factor
            bbox['height'] = bbox.get('height', 0) / scale_factor
            
    # Adjust page dimensions
    for page in data.get('pages', []):
        if 'width' in page:
            page['width'] = page['width'] / scale_factor
        if 'height' in page:
            page['height'] = page['height'] / scale_factor
            
    # Save adjusted JSON
    adjusted_path = Path(json_path).parent / f"{Path(json_path).stem}_adjusted.json"
    with open(adjusted_path, 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"📋 Adjusted JSON saved to: {adjusted_path}")
    
    # Also save a copy of the original
    import shutil
    original_path = Path(json_path).parent / f"{Path(json_path).stem}_scaled_original.json"
    shutil.copy2(json_path, original_path)
    
    # Overwrite original with adjusted
    shutil.copy2(adjusted_path, json_path)

def main():
    if len(sys.argv) < 2:
        print("Usage: python scale_and_extract.py <pdf_file> [scale_factor]")
        print("\nExample:")
        print("  python scale_and_extract.py document.pdf 2.0")
        print("\nThis will:")
        print("1. Scale the PDF up by the factor (default 2x)")
        print("2. Extract from the scaled PDF")
        print("3. Adjust coordinates back to original scale")
        return
        
    pdf_path = sys.argv[1]
    scale_factor = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    
    print(f"🚀 Scale and Extract Pipeline")
    print(f"📄 PDF: {pdf_path}")
    print(f"🔍 Scale factor: {scale_factor}x")
    print("=" * 60)
    
    # Run extraction
    json_path, scaled_pdf = extract_scaled_pdf(pdf_path, scale_factor)
    
    if json_path:
        print(f"\n✅ Success!")
        print(f"📄 Scaled PDF: {scaled_pdf}")
        print(f"📋 Extraction JSON: {json_path}")
        
        # Run analyzer
        analyzer_script = Path("extraction_analyzer.py")
        if analyzer_script.exists():
            print(f"\n🔍 Running analysis...")
            subprocess.run([sys.executable, str(analyzer_script), json_path])
    else:
        print("\n❌ Extraction failed")

if __name__ == "__main__":
    main()
