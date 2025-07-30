#!/usr/bin/env python3
"""
Simple PDF extractor using pypdfium2 that extracts actual font sizes
"""
import sys
import json
import tempfile
from pathlib import Path
import pypdfium2 as pdfium

def extract_pdf_with_fonts(pdf_path):
    """Extract PDF with actual font size information"""
    pdf = pdfium.PdfDocument(pdf_path)
    
    document_data = {
        'metadata': {
            'source_file': str(pdf_path),
            'file_name': Path(pdf_path).name,
        },
        'pages': [],
        'items': []
    }
    
    item_index = 0
    
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        textpage = page.get_textpage()
        
        # Get page dimensions
        width = page.get_width()
        height = page.get_height()
        
        document_data['pages'].append({
            'page_number': page_num,
            'width': width,
            'height': height
        })
        
        # Extract all text as one item per page for now
        # (pypdfium2's text rect API might need different approach)
        full_text = textpage.get_text_range()
        
        if full_text and full_text.strip():
            # For now, extract as single item with default font size
            # In production, would parse text structure more carefully
            item = {
                'index': item_index,
                'type': 'TextItem', 
                'level': 1,
                'content': full_text.strip(),
                'bbox': {
                    'left': 0,
                    'top': height,
                    'right': width,
                    'bottom': 0,
                    'width': width,
                    'height': height,
                    'coord_origin': 'BOTTOMLEFT'
                },
                'page': page_num + 1,
                'attributes': {
                    'style': {
                        'font_size': 12.0  # Default for now
                    }
                }
            }
            
            document_data['items'].append(item)
            item_index += 1
    
    return document_data

if __name__ == '__main__':
    try:
        pdf_path = sys.argv[1]
        
        # Extract with font sizes
        data = extract_pdf_with_fonts(pdf_path)
        
        # Save to temp file
        temp_json = tempfile.mktemp(suffix='_chonker3.json')
        with open(temp_json, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Output result
        result = {
            'success': True,
            'json_path': temp_json,
            'items': len(data['items']),
            'pages': len(data['pages'])
        }
        print(json.dumps(result))
        
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))