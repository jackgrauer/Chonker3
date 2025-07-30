#!/usr/bin/env python3
"""
Chonker2 - PDF to JSON extractor using Docling
Extracts content with precise spatial information for rendering in Snyfter
"""

import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    print("Error: Docling not available. Install with: pip install docling")
    sys.exit(1)


class Chonker2:
    """Extract PDF content to JSON with full spatial information"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.setup_logging()
        self._init_docling()
    
    def setup_logging(self):
        """Configure logging"""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _init_docling(self):
        """Initialize Docling converter"""
        try:
            # Initialize with default settings - Docling handles spatial layout internally
            self.converter = DocumentConverter()
            self.logger.info("Docling converter initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Docling: {e}")
            raise
    
    def extract_to_json(self, pdf_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract PDF content to structured JSON
        
        Args:
            pdf_path: Path to input PDF
            output_path: Optional path for JSON output (defaults to pdf_name.json)
            
        Returns:
            Dictionary containing extracted document data
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        self.logger.info(f"Processing: {pdf_path}")
        start_time = datetime.now()
        
        try:
            # Convert document
            result = self.converter.convert(str(pdf_path))
            
            # Build document structure
            document_data = {
                'metadata': {
                    'source_file': str(pdf_path),
                    'file_name': pdf_path.name,
                    'document_id': self._generate_document_id(str(pdf_path)),
                    'extraction_timestamp': datetime.now().isoformat(),
                    'processing_time': 0,  # Will update at end
                    'docling_version': getattr(DocumentConverter, '__version__', 'unknown')
                },
                'pages': [],
                'items': [],
                'tables': []
            }
            
            # Extract page information if available
            if hasattr(result.document, 'pages'):
                for page in result.document.pages:
                    page_info = {
                        'page_number': getattr(page, 'page_no', 0),
                        'width': getattr(page, 'width', 0),
                        'height': getattr(page, 'height', 0)
                    }
                    document_data['pages'].append(page_info)
            
            # Extract all items with spatial information
            item_index = 0
            items_by_page = {}  # Group items by page for better processing
            
            for item, level in result.document.iterate_items():
                item_data = self._extract_item_data(item, level, item_index)
                if item_data:
                    document_data['items'].append(item_data)
                    
                    # Group by page for column detection
                    page_no = item_data.get('page', 0)
                    if page_no not in items_by_page:
                        items_by_page[page_no] = []
                    items_by_page[page_no].append(item_data)
                    
                    # Special handling for tables
                    if item_data['type'] == 'TableItem':
                        table_data = self._extract_table_data(item, item_index)
                        if table_data:
                            document_data['tables'].append(table_data)
                    
                    item_index += 1
            
            # Post-process to detect columns and reading order
            self._detect_columns_and_order(items_by_page, document_data)
            
            # Update processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            document_data['metadata']['processing_time'] = processing_time
            
            # Save to file if output path specified
            if output_path:
                output_file = Path(output_path)
            else:
                output_file = pdf_path.with_suffix('.json')
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Extracted {len(document_data['items'])} items in {processing_time:.2f}s")
            self.logger.info(f"Saved to: {output_file}")
            
            return document_data
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            raise
    
    def _extract_item_data(self, item: Any, level: int, index: int) -> Optional[Dict[str, Any]]:
        """Extract data from a single document item"""
        try:
            item_type = type(item).__name__
            
            # Base item data
            item_data = {
                'index': index,
                'type': item_type,
                'level': level,
                'content': '',
                'bbox': None,
                'page': 0,
                'confidence': getattr(item, 'confidence', 1.0),
                'attributes': {}
            }
            
            # Extract text content
            if hasattr(item, 'text'):
                item_data['content'] = str(item.text)
            elif hasattr(item, 'caption'):
                item_data['content'] = str(item.caption)
            
            # Check if this might be a form field
            content_lower = item_data['content'].lower()
            if any(indicator in content_lower for indicator in ['name:', 'date:', 'address:', 'phone:', 'email:', 'signature:', 'id:', 'no.', 'number:']):
                item_data['attributes']['possible_form_field'] = True
            
            # Extract spatial information
            if hasattr(item, 'prov') and item.prov and len(item.prov) > 0:
                prov = item.prov[0]
                
                # Page number
                if hasattr(prov, 'page_no'):
                    item_data['page'] = prov.page_no
                
                # Bounding box
                if hasattr(prov, 'bbox'):
                    bbox = prov.bbox
                    item_data['bbox'] = {
                        'left': float(bbox.l),
                        'top': float(bbox.t),
                        'right': float(bbox.r),
                        'bottom': float(bbox.b),
                        'width': float(bbox.r - bbox.l),
                        'height': float(bbox.b - bbox.t),
                        'coord_origin': str(getattr(bbox, 'coord_origin', 'unknown'))
                    }
                    
                    # Add relative position for better layout reconstruction
                    # Get page dimensions if available
                    if hasattr(prov, 'page') and hasattr(prov.page, 'width') and hasattr(prov.page, 'height'):
                        page_width = float(prov.page.width) if prov.page.width > 0 else 612  # Default letter size
                        page_height = float(prov.page.height) if prov.page.height > 0 else 792
                        
                        item_data['bbox']['relative'] = {
                            'x_ratio': bbox.l / page_width,
                            'y_ratio': bbox.t / page_height,
                            'width_ratio': (bbox.r - bbox.l) / page_width,
                            'height_ratio': (bbox.b - bbox.t) / page_height
                        }
            
            # Type-specific attributes
            if item_type == 'SectionHeaderItem':
                item_data['attributes']['header_level'] = self._get_header_level(item, level)
            elif item_type == 'ListItem':
                item_data['attributes']['marker'] = getattr(item, 'marker', '')
                item_data['attributes']['list_level'] = getattr(item, 'level', 0)
            elif item_type == 'FigureItem':
                item_data['attributes']['caption'] = getattr(item, 'caption', '')
            
            # Extract font and style information if available
            if hasattr(item, 'style'):
                style_info = {}
                if hasattr(item.style, 'font_name'):
                    style_info['font'] = str(item.style.font_name)
                if hasattr(item.style, 'font_size'):
                    style_info['font_size'] = float(item.style.font_size)
                if hasattr(item.style, 'bold'):
                    style_info['bold'] = bool(item.style.bold)
                if hasattr(item.style, 'italic'):
                    style_info['italic'] = bool(item.style.italic)
                if style_info:
                    item_data['attributes']['style'] = style_info
            
            return item_data
            
        except Exception as e:
            self.logger.warning(f"Failed to extract item {index}: {e}")
            return None
    
    def _extract_table_data(self, table_item: Any, index: int) -> Optional[Dict[str, Any]]:
        """Extract detailed table data"""
        try:
            table_data = {
                'index': index,
                'rows': [],
                'num_rows': 0,
                'num_cols': 0,
                'cells': []
            }
            
            # Try to get table as markdown for structure
            if hasattr(table_item, 'export_to_markdown'):
                markdown = table_item.export_to_markdown()
                if markdown and '|' in markdown:
                    lines = markdown.strip().split('\n')
                    table_data['num_rows'] = len([l for l in lines if '|' in l and '---' not in l])
                    if lines:
                        first_row = [c.strip() for c in lines[0].split('|') if c.strip()]
                        table_data['num_cols'] = len(first_row)
            
            # Try to get individual cells with positions
            if hasattr(table_item, 'table_cells'):
                for cell in table_item.table_cells:
                    cell_data = {
                        'row': getattr(cell, 'row', 0),
                        'col': getattr(cell, 'col', 0),
                        'content': str(getattr(cell, 'text', '')),
                        'rowspan': getattr(cell, 'rowspan', 1),
                        'colspan': getattr(cell, 'colspan', 1)
                    }
                    
                    # Cell bounding box if available
                    if hasattr(cell, 'bbox'):
                        bbox = cell.bbox
                        cell_data['bbox'] = {
                            'left': float(bbox.l),
                            'top': float(bbox.t),
                            'right': float(bbox.r),
                            'bottom': float(bbox.b)
                        }
                    
                    table_data['cells'].append(cell_data)
            
            # Try to export as dataframe for structured data
            if hasattr(table_item, 'export_to_dataframe'):
                try:
                    df = table_item.export_to_dataframe()
                    
                    # Convert to row-based structure
                    for idx, row in df.iterrows():
                        row_data = {
                            'index': idx,
                            'cells': [str(val) for val in row.values]
                        }
                        table_data['rows'].append(row_data)
                    
                    # Add column headers
                    table_data['headers'] = [str(col) for col in df.columns]
                    
                except Exception as e:
                    self.logger.debug(f"Failed to export table as dataframe: {e}")
            
            return table_data
            
        except Exception as e:
            self.logger.warning(f"Failed to extract table data: {e}")
            return None
    
    def _get_header_level(self, item: Any, level: int) -> int:
        """Determine header level (h1-h6)"""
        # Could use font size or other attributes if available
        # For now, use document structure level
        return min(level + 1, 6)
    
    def _generate_document_id(self, pdf_path: str) -> str:
        """Generate unique document ID"""
        return hashlib.sha256(f"{pdf_path}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    
    def _detect_columns_and_order(self, items_by_page: Dict[int, List[Dict]], document_data: Dict):
        """Detect multi-column layouts and fix reading order"""
        for page_no, page_items in items_by_page.items():
            if not page_items:
                continue
                
            # Sort items by vertical position first
            page_items.sort(key=lambda x: (
                x.get('bbox', {}).get('top', 0) if x.get('bbox') else 0,
                x.get('bbox', {}).get('left', 0) if x.get('bbox') else 0
            ))
            
            # Detect potential columns by analyzing x-coordinates
            x_positions = []
            for item in page_items:
                if item.get('bbox') and item['bbox'].get('left') is not None:
                    x_positions.append(item['bbox']['left'])
            
            if len(x_positions) > 10:  # Need enough items to detect pattern
                # Simple column detection: look for gaps in x-distribution
                x_positions.sort()
                gaps = []
                for i in range(1, len(x_positions)):
                    gap = x_positions[i] - x_positions[i-1]
                    if gap > 50:  # Significant gap might indicate column boundary
                        gaps.append((x_positions[i-1], x_positions[i]))
                
                # If we found column gaps, add metadata
                if gaps:
                    self.logger.info(f"Page {page_no}: Detected {len(gaps)+1} potential columns")
                    # Add column info to page metadata
                    if page_no < len(document_data['pages']):
                        document_data['pages'][page_no]['columns'] = len(gaps) + 1
                        document_data['pages'][page_no]['column_gaps'] = gaps
    
    def batch_process(self, pdf_files: List[str], output_dir: Optional[str] = None):
        """Process multiple PDFs"""
        results = []
        
        for pdf_file in pdf_files:
            try:
                if output_dir:
                    output_path = Path(output_dir) / f"{Path(pdf_file).stem}.json"
                else:
                    output_path = None
                
                result = self.extract_to_json(pdf_file, output_path)
                results.append({
                    'file': pdf_file,
                    'success': True,
                    'items': len(result['items']),
                    'tables': len(result['tables'])
                })
            except Exception as e:
                results.append({
                    'file': pdf_file,
                    'success': False,
                    'error': str(e)
                })
        
        # Print summary
        successful = sum(1 for r in results if r['success'])
        print(f"\nProcessed {len(pdf_files)} files: {successful} successful, {len(pdf_files) - successful} failed")
        
        for result in results:
            if result['success']:
                print(f"✓ {result['file']}: {result['items']} items, {result['tables']} tables")
            else:
                print(f"✗ {result['file']}: {result['error']}")


def main():
    parser = argparse.ArgumentParser(
        description='Chonker2 - Extract PDF content to JSON with spatial information'
    )
    parser.add_argument('input', nargs='+', help='PDF file(s) to process')
    parser.add_argument('-o', '--output', help='Output directory for JSON files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = Chonker2(verbose=args.verbose)
    
    # Process files
    if len(args.input) == 1:
        # Single file
        extractor.extract_to_json(args.input[0], args.output)
    else:
        # Batch processing
        extractor.batch_process(args.input, args.output)


if __name__ == '__main__':
    main()