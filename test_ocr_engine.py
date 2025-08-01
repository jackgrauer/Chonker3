#!/usr/bin/env python3
"""
Test script to determine which OCR engine Docling is using
"""
import sys
import logging
from pathlib import Path

# Set up comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import Docling components
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TableFormerMode,
        OCRMode
    )
    from docling.document_converter import PdfFormatOption
    
    # Get all OCR-related info
    print("\n=== Docling OCR Configuration ===")
    
    # Check available OCR engines
    try:
        from docling.models.factories import ModelFactory
        factory = ModelFactory()
        print(f"Available OCR engines: {factory.get_ocr_engines()}")
    except:
        pass
    
    # Create pipeline and check OCR settings
    pipeline_options = PdfPipelineOptions(
        do_ocr=OCRMode.AUTO,
        do_table_structure=True,
        table_structure_options={
            "mode": TableFormerMode.ACCURATE
        }
    )
    
    print(f"\nOCR Mode: {pipeline_options.do_ocr}")
    print(f"OCR Options: {pipeline_options.ocr_options}")
    
    # Try to convert a small test and see what OCR engine is used
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(f"\nTesting with PDF: {pdf_path}")
        
        # Create converter with debug logging
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )
        
        # Hook into OCR engine selection if possible
        import docling.backend.pdf_backend
        original_method = None
        selected_engine = None
        
        # Try to intercept OCR engine selection
        if hasattr(docling.backend.pdf_backend, 'PdfPageBackend'):
            backend_class = docling.backend.pdf_backend.PdfPageBackend
            if hasattr(backend_class, '_get_ocr_engine'):
                original_method = backend_class._get_ocr_engine
                
                def patched_get_ocr_engine(self, *args, **kwargs):
                    result = original_method(self, *args, **kwargs)
                    global selected_engine
                    selected_engine = result.__class__.__name__ if result else "None"
                    print(f"\n*** OCR Engine Selected: {selected_engine} ***")
                    return result
                
                backend_class._get_ocr_engine = patched_get_ocr_engine
        
        # Convert a page
        result = converter.convert(pdf_path)
        
        print(f"\nConversion complete.")
        if selected_engine:
            print(f"OCR Engine Used: {selected_engine}")
        
        # Check result for OCR info
        if hasattr(result, 'metadata'):
            print(f"Metadata: {result.metadata}")
    
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()