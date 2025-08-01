#!/usr/bin/env python3
"""
Force Apple Vision by temporarily hiding EasyOCR
"""
import sys
import os

# Hide easyocr from import
class HideEasyOCR:
    def find_module(self, fullname, path=None):
        if fullname == 'easyocr' or fullname.startswith('easyocr.'):
            return self
        return None
    
    def load_module(self, fullname):
        raise ImportError(f"EasyOCR hidden to force Apple Vision usage")

# Install the import hook
sys.meta_path.insert(0, HideEasyOCR())

# Now import and run enhanced_chonker2
from enhanced_chonker2 import EnhancedChonker2

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Enhanced Chonker2 forced to use Apple Vision'
    )
    parser.add_argument('input', help='PDF file to process')
    parser.add_argument('-o', '--output', help='Output JSON file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--no-preprocess', action='store_true', help='Disable preprocessing')
    
    args = parser.parse_args()
    
    # Create enhanced extractor (will use Apple Vision since EasyOCR is hidden)
    extractor = EnhancedChonker2(
        verbose=args.verbose,
        preprocess=not args.no_preprocess
    )
    
    # Process file
    extractor.extract_to_json(args.input, args.output)

if __name__ == '__main__':
    main()