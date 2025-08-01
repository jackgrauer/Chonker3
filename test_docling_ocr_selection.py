#!/usr/bin/env python3
"""
Test how Docling selects OCR engines
"""
import logging
logging.basicConfig(level=logging.DEBUG)

# Check which OCR engines are available and their priority
try:
    from docling.models import ocr_utils
    print("Available in ocr_utils:", dir(ocr_utils))
except:
    pass

try:
    from docling.backend import ocr_backend
    print("Available in ocr_backend:", dir(ocr_backend))
except:
    pass

try:
    # Look for OCR engine registry or factory
    from docling.models.factories import ModelFactory
    factory = ModelFactory()
    print("\nOCR Engines from factory:", factory.get_ocr_engines())
    
    # Try to see the selection logic
    import docling.models.ocr_utils as ocr_utils
    if hasattr(ocr_utils, 'get_ocr_engine'):
        print("Has get_ocr_engine function")
except Exception as e:
    print(f"Error: {e}")

# Check if we can influence the selection
import os
os.environ['DOCLING_OCR_ENGINE'] = 'ocrmac'
os.environ['DOCLING_PREFER_OCRMAC'] = '1'

from docling.document_converter import DocumentConverter
converter = DocumentConverter()

print("\nEnvironment set to prefer ocrmac")
print("Now running conversion to see which OCR is used...")