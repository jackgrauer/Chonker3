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
        """Initialize Docling converter with optimized settings"""
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions,
                TableFormerMode,
                OCRMode
            )
            from docling.document_converter import PdfFormatOption
            
            # Configure pipeline for maximum accuracy
            pipeline_options = PdfPipelineOptions(
                do_ocr=OCRMode.AUTO,  # Auto-detect when OCR is needed
                do_table_structure=True,  # Extract table structures
                table_structure_options={
                    "mode": TableFormerMode.ACCURATE  # Use accurate mode
                }
            )
            
            # Initialize with optimized settings
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )
            self.logger.info("Docling converter initialized with optimized settings")
        except ImportError:
            # Fallback for older Docling versions
            self.converter = DocumentConverter()
            self.logger.info("Docling converter initialized (default settings)")
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
            if hasattr(result.document, 'pages') and result.document.pages:
                for page_idx, page in enumerate(result.document.pages):
                    # Debug what attributes the page has
                    if page_idx == 0:
                        self.logger.debug(f"Page attributes: {[attr for attr in dir(page) if not attr.startswith('_')]}")
                    
                    # Try different attribute names
                    width = getattr(page, 'width', None) or getattr(page, 'size', {}).get('width', 612.0)
                    height = getattr(page, 'height', None) or getattr(page, 'size', {}).get('height', 792.0)
                    
                    # Ensure we have valid dimensions
                    if width == 0 or width is None:
                        width = 612.0
                    if height == 0 or height is None:
                        height = 792.0
                        
                    page_info = {
                        'page_number': getattr(page, 'page_no', page_idx) + 1,  # 1-based page numbers
                        'width': float(width),
                        'height': float(height)
                    }
                    document_data['pages'].append(page_info)
            else:
                # Add default page if no page info available
                self.logger.warning("No page information available, using default US Letter size")
                document_data['pages'].append({
                    'page_number': 1,
                    'width': 612.0,
                    'height': 792.0
                })
            
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
        """Extract data from a single document item with enhanced form detection"""
        try:
            item_type = type(item).__name__
            
            # Log the actual types Docling provides for debugging
            self.logger.debug(f"Docling item type: {item_type}")
            
            
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
            
            # Enhanced form field detection
            content = item_data['content'].strip()
            content_lower = content.lower()
            
            # Detect form labels (text ending with colon)
            if content.endswith(':'):
                item_data['type'] = 'FormLabel'
                item_data['attributes']['form_type'] = 'label'
            
            # Detect checkboxes
            elif content in ['[ ]', '[X]', '[x]', '☐', '☑', '□', '■', '▢', '▣']:
                item_data['type'] = 'Checkbox'
                item_data['attributes']['checked'] = content in ['[X]', '[x]', '☑', '■', '▣']
            
            # Detect form field indicators
            elif any(indicator in content_lower for indicator in [
                'name:', 'date:', 'address:', 'phone:', 'email:', 'signature:', 
                'id:', 'no.', 'number:', 'title:', 'ssn:', 'dob:', 'zip:'
            ]):
                item_data['attributes']['possible_form_field'] = True
                item_data['type'] = 'FormLabel'
            
            # Detect underlined areas (common in forms)
            elif content == '_' * len(content) or content == '-' * len(content):
                item_data['type'] = 'FormField'
                item_data['attributes']['field_type'] = 'text_input'
            
            # Extract spatial information
            if hasattr(item, 'prov') and item.prov and len(item.prov) > 0:
                prov = item.prov[0]
                
                # Page number
                if hasattr(prov, 'page_no'):
                    item_data['page'] = prov.page_no
                
                # Bounding box with validation
                if hasattr(prov, 'bbox'):
                    bbox = prov.bbox
                    # Validate bbox values
                    if all(hasattr(bbox, attr) for attr in ['l', 't', 'r', 'b']):
                        left = float(bbox.l)
                        top = float(bbox.t)
                        right = float(bbox.r)
                        bottom = float(bbox.b)
                        
                        # Ensure valid dimensions
                        # For BOTTOMLEFT origin: top > bottom (top is higher Y value)
                        # For TOPLEFT origin: bottom > top (bottom is higher Y value)
                        coord_origin = str(getattr(bbox, 'coord_origin', 'BOTTOMLEFT'))
                        
                        if 'BOTTOMLEFT' in coord_origin:
                            valid_bbox = right > left and top > bottom
                        else:
                            valid_bbox = right > left and bottom > top
                            
                        if valid_bbox:
                            item_data['bbox'] = {
                                'left': left,
                                'top': top,
                                'right': right,
                                'bottom': bottom,
                                'width': right - left,
                                'height': abs(top - bottom),
                                'coord_origin': coord_origin
                            }
                        else:
                            self.logger.warning(f"Invalid bbox dimensions for item {index}: {bbox}")
                    
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
            style_info = {}
            
            # Check direct style attribute
            if hasattr(item, 'style'):
                if hasattr(item.style, 'font_name'):
                    style_info['font'] = str(item.style.font_name)
                if hasattr(item.style, 'font_size'):
                    style_info['font_size'] = float(item.style.font_size)
                if hasattr(item.style, 'bold'):
                    style_info['bold'] = bool(item.style.bold)
                if hasattr(item.style, 'italic'):
                    style_info['italic'] = bool(item.style.italic)
            
            # Also check for text_style attribute (some Docling versions)
            if hasattr(item, 'text_style'):
                if hasattr(item.text_style, 'is_bold'):
                    style_info['bold'] = bool(item.text_style.is_bold)
                if hasattr(item.text_style, 'is_italic'):
                    style_info['italic'] = bool(item.text_style.is_italic)
                if hasattr(item.text_style, 'font_size'):
                    style_info['font_size'] = float(item.text_style.font_size)
            
            # Check in provenance data for style info
            if hasattr(item, 'prov') and item.prov:
                for prov in item.prov:
                    if hasattr(prov, 'text_style'):
                        ts = prov.text_style
                        if hasattr(ts, 'font_size') and 'font_size' not in style_info:
                            style_info['font_size'] = float(ts.font_size)
                        if hasattr(ts, 'font_weight') and 'bold' not in style_info:
                            # Font weight > 400 typically indicates bold
                            style_info['bold'] = ts.font_weight > 400
                        if hasattr(ts, 'font_style') and 'italic' not in style_info:
                            style_info['italic'] = ts.font_style == 'italic'
            
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
            
            # Get items with valid bounding boxes
            items_with_bbox = [item for item in page_items if item.get('bbox')]
            
            if len(items_with_bbox) < 5:
                continue
                
            # Analyze x-coordinate distribution to detect columns
            x_positions = [item['bbox']['left'] for item in items_with_bbox]
            x_positions.sort()
            
            # Find gaps between x-positions to identify column boundaries
            gaps = []
            column_threshold = 50  # Minimum gap to consider as column boundary
            
            for i in range(1, len(x_positions)):
                gap_size = x_positions[i] - x_positions[i-1]
                if gap_size > column_threshold:
                    gaps.append((x_positions[i-1] + gap_size/2, gap_size))
            
            # If we found significant gaps, we have columns
            if gaps:
                # Define column boundaries
                column_boundaries = [0]  # Start of first column
                column_boundaries.extend([gap[0] for gap in gaps])
                column_boundaries.append(float('inf'))  # End of last column
                
                # Assign items to columns and sort by reading order
                for item in items_with_bbox:
                    x = item['bbox']['left']
                    
                    # Find which column this item belongs to
                    for col_idx in range(len(column_boundaries) - 1):
                        if column_boundaries[col_idx] <= x < column_boundaries[col_idx + 1]:
                            item['attributes']['column'] = col_idx
                            break
                
                # Re-sort items: by row first (using y-coordinate bands), then by column
                # This ensures proper reading order for multi-column layouts
                row_height_estimate = 20  # Approximate line height
                
                for item in items_with_bbox:
                    item['attributes']['row_band'] = int(item['bbox']['top'] / row_height_estimate)
                
                # Sort by row band first, then by column
                items_with_bbox.sort(key=lambda x: (
                    x['attributes'].get('row_band', 0),
                    x['attributes'].get('column', 0)
                ))
                
                # Update reading order
                for idx, item in enumerate(items_with_bbox):
                    item['attributes']['reading_order'] = idx
                
                self.logger.info(f"Page {page_no}: Detected {len(gaps) + 1} columns")
                
                # Add column info to page metadata
                if page_no < len(document_data['pages']):
                    document_data['pages'][page_no]['columns'] = len(gaps) + 1
                    document_data['pages'][page_no]['column_boundaries'] = column_boundaries[:-1]
    
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