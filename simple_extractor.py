#!/usr/bin/env python3
"""
FIXED PDF extractor using pypdfium2 with proper text bounds
"""
import sys
import json
import tempfile
from pathlib import Path
import pypdfium2 as pdfium

def extract_pdf_with_fonts(pdf_path):
    """Extract PDF with proper individual text element bounding boxes"""
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
            'page_number': page_num + 1,
            'width': width,
            'height': height
        })
        
        # Try different extraction method - get all text first
        full_text = textpage.get_text_range()
        
        if not full_text or not full_text.strip():
            print(f"DEBUG: Page {page_num} has no text", file=sys.stderr)
            continue
            
        print(f"DEBUG: Page {page_num} has text: {len(full_text)} chars", file=sys.stderr)
        
        # Split text into lines and search for each line's position
        lines = full_text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Search for this line to get its position
            searcher = textpage.search(line, match_case=True, match_whole_word=False)
            
            if searcher:
                # Get first match (should be exact since we're searching extracted text)
                first_match = searcher.get_next()
                
                if first_match:
                    # Get bounding rectangles for this match
                    rect_count = first_match.count_rects()
                    
                    if rect_count > 0:
                        # Combine all rectangles
                        rects = []
                        for i in range(rect_count):
                            rect = first_match.get_rect(i)
                            if rect:
                                rects.append(rect)
                        
                        if rects:
                            # Get overall bounds
                            left = min(r[0] for r in rects)
                            bottom = min(r[1] for r in rects)  
                            right = max(r[2] for r in rects)
                            top = max(r[3] for r in rects)
                            
                            # Convert PDF coordinates (bottom-left origin) to screen coordinates (top-left origin)
                            item = {
                                'index': item_index,
                                'type': 'TextItem',
                                'level': 1,
                                'content': line,
                                'bbox': {
                                    'left': float(left),
                                    'top': float(height - top),  # Flip Y coordinate
                                    'right': float(right),
                                    'bottom': float(height - bottom),  # Flip Y coordinate
                                    'width': float(right - left),
                                    'height': float(top - bottom),
                                    'coord_origin': 'TOPLEFT'  # After conversion
                                },
                                'page': page_num + 1,
                                'attributes': {
                                    'style': {
                                        'font_size': 12.0  # Would need character-level API for actual size
                                    }
                                }
                            }
                            
                            # Simple form detection
                            if line.endswith(':'):
                                item['type'] = 'FormLabel'
                            elif line in ['[ ]', '[X]', '[x]', '☐', '☑']:
                                item['type'] = 'Checkbox'
                            
                            document_data['items'].append(item)
                            item_index += 1
                            
                            if item_index < 5:  # Debug first few items
                                print(f"DEBUG: Item {item_index}: '{line[:30]}...' at ({left:.1f}, {top:.1f})", file=sys.stderr)
    
    return document_data

if __name__ == '__main__':
    try:
        pdf_path = sys.argv[1]
        
        # Extract with proper bounds
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
        import traceback
        print(json.dumps({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), file=sys.stderr)