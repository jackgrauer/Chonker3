#!/usr/bin/env python3
"""
Enhanced Chonker2 configured to use Apple Vision OCR
"""
import sys
import os

# Force Docling to prefer ocrmac
os.environ['DOCLING_OCR_ENGINE'] = 'ocrmac'

# Import the enhanced chonker2
from enhanced_chonker2 import EnhancedChonker2, main

# Create a version that logs which OCR engine is used
class AppleVisionChonker2(EnhancedChonker2):
    def __init__(self, verbose: bool = False, preprocess: bool = True):
        super().__init__(verbose, preprocess)
        self.logger.info("Configured to prefer Apple Vision (ocrmac) for OCR")
    
    def _init_docling(self):
        """Initialize Docling with Apple Vision preference"""
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions,
                TableFormerMode
            )
            from docling.document_converter import PdfFormatOption
            
            # Configure pipeline with OCR engine preference
            pipeline_options = PdfPipelineOptions(
                do_ocr=True,
                do_table_structure=True,
                table_structure_options={
                    "mode": TableFormerMode.ACCURATE
                },
                ocr_options={
                    "engine_preference": ["ocrmac", "tesseract", "easyocr"],  # Prefer ocrmac
                    "lang": ["en"],
                    "force_full_page_ocr": False
                }
            )
            
            # Import DocumentConverter here
            from docling.document_converter import DocumentConverter
            
            # Initialize with optimized settings
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )
            self.logger.info("Docling converter initialized with Apple Vision preference")
        except Exception as e:
            # Fall back to parent implementation
            super()._init_docling()

if __name__ == '__main__':
    # Replace main to use our Apple Vision version
    import argparse
    parser = argparse.ArgumentParser(
        description='Enhanced Chonker2 with Apple Vision OCR'
    )
    parser.add_argument('input', help='PDF file to process')
    parser.add_argument('-o', '--output', help='Output JSON file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--no-preprocess', action='store_true', help='Disable preprocessing')
    
    args = parser.parse_args()
    
    # Create enhanced extractor with Apple Vision
    extractor = AppleVisionChonker2(
        verbose=args.verbose,
        preprocess=not args.no_preprocess
    )
    
    # Process file
    extractor.extract_to_json(args.input, args.output)