#!/usr/bin/env python3
"""
Simple check of which OCR engine Docling uses
"""
import sys
import logging

# Enable all debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Silence some noisy loggers
for logger_name in ['urllib3', 'httpx', 'httpcore']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

from docling.document_converter import DocumentConverter

# Create converter
converter = DocumentConverter()

# Process PDF
pdf_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
print(f"\nProcessing: {pdf_path}")

# Convert and look for OCR logs
result = converter.convert(pdf_path)

print(f"\nExtracted {len(result.document.texts)} text items")