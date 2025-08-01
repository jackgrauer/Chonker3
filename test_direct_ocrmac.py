#!/usr/bin/env python3
"""
Test ocrmac directly vs through Docling
"""
from ocrmac.ocrmac import text_from_image
from PIL import Image
import sys

# Test image path
if len(sys.argv) > 1:
    image_path = sys.argv[1]
else:
    # First convert PDF page to image
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument("/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf")
    page = pdf[0]
    bitmap = page.render(scale=4.0)  # High resolution
    image = bitmap.to_pil()
    image.save("/tmp/test_page.png")
    image_path = "/tmp/test_page.png"
    pdf.close()

print(f"Testing OCR on: {image_path}")

# Test with ocrmac directly
print("\n=== Direct ocrmac (Apple Vision) ===")
results = text_from_image(image_path, recognition_level="accurate", detail=True)
print(f"Total items recognized: {len(results)}")

# Results are tuples of (text, confidence, bbox)
all_text = []
for text, confidence, bbox in results:
    all_text.append(text)
    if 'University' in text or 'Philadelphia' in text or '19104' in text:
        print(f"\nFound address component:")
        print(f"  Text: '{text}'")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  BBox: {bbox}")

# Join all text to see full extraction
full_text = ' '.join(all_text)
print(f"\nFull extracted text length: {len(full_text)} chars")

# Also test with just the address region
print("\n=== Testing specific regions ===")
img = Image.open(image_path)
width, height = img.size

# Top right region where address should be
address_region = img.crop((width//2, 0, width, height//4))
address_region.save("/tmp/address_region.png")
address_results = text_from_image("/tmp/address_region.png")
address_text = ' '.join([t[0] for t in address_results])
print(f"Address region text:\n{address_text}")