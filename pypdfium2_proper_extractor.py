#!/usr/bin/env python3
"""
Better pypdfium2 extractor using actual text object API
"""
import sys
import json
import tempfile
from pathlib import Path
import pypdfium2 as pdfium

def extract_pdf_with_proper_bounds(pdf_path):
    """Extract PDF with actual text positions using pypdfium2"""
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
        
        # Get page dimensions
        width = page.get_width()
        height = page.get_height()
        
        document_data['pages'].append({
            'page_number': page_num + 1,
            'width': width,
            'height': height
        })
        
        # Get text page
        textpage = page.get_textpage()
        
        # Try to extract structured text
        # This approach uses the page object model
        page_objects = page.get_objects()
        
        for obj in page_objects:
            # Check if it's a text object
            if hasattr(obj, 'type') and obj.type == pdfium.FPDF_PAGEOBJ_TEXT:
                # Get the text content
                text = obj.get_text()
                if not text or not text.strip():
                    continue
                
                # Get bounding box
                bbox = obj.get_bounds()
                
                item = {
                    'index': item_index,
                    'type': 'TextItem',
                    'content': text.strip(),
                    'bbox': {
                        'left': float(bbox.left),
                        'top': float(height - bbox.top),  # Convert to top-left origin
                        'width': float(bbox.right - bbox.left),
                        'height': float(bbox.top - bbox.bottom),
                        'coord_origin': 'TOPLEFT'
                    },
                    'page': page_num + 1,
                    'attributes': {
                        'style': {
                            'font_size': 12.0  # Would need more work to get actual font size
                        }
                    }
                }
                
                # Simple form detection
                if text.strip().endswith(':'):
                    item['type'] = 'FormLabel'
                elif text.strip() in ['[ ]', '[X]', '[x]', '☐', '☑']:
                    item['type'] = 'Checkbox'
                
                document_data['items'].append(item)
                item_index += 1
        
        # If page objects don't work, fall back to text extraction by chunks
        if item_index == 0:
            # Get all text and try to segment it
            full_text = textpage.get_text_range()
            if full_text and full_text.strip():
                # At least split by lines
                lines = full_text.strip().split('\n')
                for i, line in enumerate(lines):
                    if not line.strip():
                        continue
                    
                    item = {
                        'index': item_index,
                        'type': 'TextItem',
                        'content': line.strip(),
                        'bbox': {
                            'left': 50,
                            'top': 50 + (i * 20),
                            'width': width - 100,
                            'height': 18,
                            'coord_origin': 'TOPLEFT'
                        },
                        'page': page_num + 1,
                        'attributes': {'style': {'font_size': 12.0}}
                    }
                    
                    document_data['items'].append(item)
                    item_index += 1
    
    return document_data

if __name__ == '__main__':
    try:
        pdf_path = sys.argv[1]
        data = extract_pdf_with_proper_bounds(pdf_path)
        
        temp_json = tempfile.mktemp(suffix='_chonker3.json')
        with open(temp_json, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(json.dumps({
            'success': True,
            'json_path': temp_json,
            'items': len(data['items']),
            'pages': len(data['pages'])
        }))
        
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))