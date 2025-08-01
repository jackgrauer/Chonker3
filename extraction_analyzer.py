#!/usr/bin/env python3
"""
Comprehensive JSON extraction analyzer
Helps identify if issues are in extraction (Docling) or rendering (Chonker3)
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import subprocess
import math

class ExtractionAnalyzer:
    def __init__(self, json_path):
        self.json_path = Path(json_path)
        self.data = None
        self.issues = []
        self.warnings = []
        self.stats = {}
        
    def load_json(self):
        """Load and validate JSON"""
        try:
            with open(self.json_path, 'r') as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            print(f"❌ Failed to load JSON: {e}")
            return False
            
    def analyze(self):
        """Run all analysis checks"""
        if not self.load_json():
            return
            
        print(f"📄 Analyzing: {self.json_path}")
        print("=" * 60)
        
        # Run all checks
        self.check_structure()
        self.check_coordinates()
        self.check_text_content()
        self.check_overlaps()
        self.check_ordering()
        self.check_types()
        self.check_font_info()
        self.check_page_info()
        
        # Generate report
        self.generate_report()
        
    def check_structure(self):
        """Check JSON structure"""
        print("\n🔍 Checking JSON structure...")
        
        required_fields = ['items', 'pages']
        for field in required_fields:
            if field not in self.data:
                self.issues.append(f"Missing required field: {field}")
            else:
                self.stats[f"{field}_count"] = len(self.data.get(field, []))
                
        # Check item structure
        items = self.data.get('items', [])
        if items:
            sample_item = items[0]
            expected_fields = ['content', 'bbox', 'page', 'type']
            for field in expected_fields:
                if field not in sample_item:
                    self.warnings.append(f"Items missing field: {field}")
                    
        print(f"  ✓ Found {len(items)} items")
        print(f"  ✓ Found {len(self.data.get('pages', []))} pages")
        
    def check_coordinates(self):
        """Check coordinate system and values"""
        print("\n🔍 Checking coordinates...")
        
        items = self.data.get('items', [])
        if not items:
            return
            
        # Track coordinate stats
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        coord_systems = set()
        negative_coords = []
        huge_coords = []
        
        for i, item in enumerate(items):
            bbox = item.get('bbox', {})
            if not bbox:
                self.issues.append(f"Item {i} missing bbox")
                continue
                
            left = bbox.get('left', 0)
            top = bbox.get('top', 0)
            width = bbox.get('width', 0)
            height = bbox.get('height', 0)
            
            # Track coordinate system
            coord_origin = bbox.get('coord_origin', 'UNKNOWN')
            coord_systems.add(coord_origin)
            
            # Check for negative coordinates
            if left < 0 or top < 0:
                negative_coords.append(f"Item {i}: left={left}, top={top}")
                
            # Check for huge coordinates (likely errors)
            if left > 1000 or top > 2000:
                huge_coords.append(f"Item {i}: left={left}, top={top}")
                
            # Track bounds
            min_x = min(min_x, left)
            min_y = min(min_y, top)
            max_x = max(max_x, left + width)
            max_y = max(max_y, top + height)
            
        print(f"  ✓ Coordinate systems found: {coord_systems}")
        print(f"  ✓ Bounds: X({min_x:.1f} - {max_x:.1f}), Y({min_y:.1f} - {max_y:.1f})")
        
        if len(coord_systems) > 1:
            self.issues.append(f"Mixed coordinate systems: {coord_systems}")
            
        if negative_coords:
            self.issues.append(f"Found {len(negative_coords)} items with negative coordinates")
            
        if huge_coords:
            self.warnings.append(f"Found {len(huge_coords)} items with very large coordinates")
            
    def check_text_content(self):
        """Check text extraction quality"""
        print("\n🔍 Checking text content...")
        
        items = self.data.get('items', [])
        empty_items = []
        total_chars = 0
        suspicious_chars = []
        
        for i, item in enumerate(items):
            content = item.get('content', '').strip()
            
            if not content:
                empty_items.append(i)
                continue
                
            total_chars += len(content)
            
            # Check for common extraction issues
            if '�' in content:
                suspicious_chars.append(f"Item {i}: replacement character found")
            if content.count(' ') > len(content) * 0.5:
                suspicious_chars.append(f"Item {i}: excessive spaces")
            if all(c == content[0] for c in content) and len(content) > 3:
                suspicious_chars.append(f"Item {i}: repeated character: '{content[:20]}...'")
                
        print(f"  ✓ Total characters extracted: {total_chars}")
        print(f"  ✓ Average chars per item: {total_chars/len(items):.1f}" if items else "")
        
        if empty_items:
            self.warnings.append(f"Found {len(empty_items)} empty text items")
            
        if suspicious_chars:
            self.warnings.append(f"Found {len(suspicious_chars)} items with suspicious characters")
            
        if total_chars < 100:
            self.issues.append("Very little text extracted - possible extraction failure")
            
    def check_overlaps(self):
        """Check for overlapping items"""
        print("\n🔍 Checking for overlaps...")
        
        items = self.data.get('items', [])
        overlaps = []
        
        # Group by page
        pages = {}
        for item in items:
            page = item.get('page', 1)
            if page not in pages:
                pages[page] = []
            pages[page].append(item)
            
        # Check overlaps per page
        for page, page_items in pages.items():
            for i, item1 in enumerate(page_items):
                bbox1 = item1.get('bbox', {})
                if not bbox1:
                    continue
                    
                for j, item2 in enumerate(page_items[i+1:], i+1):
                    bbox2 = item2.get('bbox', {})
                    if not bbox2:
                        continue
                        
                    # Check if bboxes overlap
                    if self._boxes_overlap(bbox1, bbox2):
                        overlap_area = self._overlap_area(bbox1, bbox2)
                        area1 = bbox1.get('width', 0) * bbox1.get('height', 0)
                        area2 = bbox2.get('width', 0) * bbox2.get('height', 0)
                        
                        # Only report significant overlaps
                        if overlap_area > min(area1, area2) * 0.5:
                            overlaps.append({
                                'page': page,
                                'items': (i, j),
                                'overlap_percent': (overlap_area / min(area1, area2)) * 100
                            })
                            
        print(f"  ✓ Found {len(overlaps)} significant overlaps")
        
        if len(overlaps) > 10:
            self.issues.append(f"Many overlapping items ({len(overlaps)}) - possible extraction issue")
            
    def _boxes_overlap(self, bbox1, bbox2):
        """Check if two bounding boxes overlap"""
        return not (bbox1.get('left', 0) + bbox1.get('width', 0) <= bbox2.get('left', 0) or
                   bbox2.get('left', 0) + bbox2.get('width', 0) <= bbox1.get('left', 0) or
                   bbox1.get('top', 0) + bbox1.get('height', 0) <= bbox2.get('top', 0) or
                   bbox2.get('top', 0) + bbox2.get('height', 0) <= bbox1.get('top', 0))
                   
    def _overlap_area(self, bbox1, bbox2):
        """Calculate overlap area between two boxes"""
        x1 = max(bbox1.get('left', 0), bbox2.get('left', 0))
        y1 = max(bbox1.get('top', 0), bbox2.get('top', 0))
        x2 = min(bbox1.get('left', 0) + bbox1.get('width', 0),
                 bbox2.get('left', 0) + bbox2.get('width', 0))
        y2 = min(bbox1.get('top', 0) + bbox1.get('height', 0),
                 bbox2.get('top', 0) + bbox2.get('height', 0))
        
        if x2 > x1 and y2 > y1:
            return (x2 - x1) * (y2 - y1)
        return 0
        
    def check_ordering(self):
        """Check if items are in reading order"""
        print("\n🔍 Checking item ordering...")
        
        items = self.data.get('items', [])
        if not items:
            return
            
        # Check if items are roughly in top-to-bottom, left-to-right order
        order_issues = 0
        
        for i in range(1, len(items)):
            prev = items[i-1]
            curr = items[i]
            
            # Skip if different pages
            if prev.get('page', 1) != curr.get('page', 1):
                continue
                
            prev_bbox = prev.get('bbox', {})
            curr_bbox = curr.get('bbox', {})
            
            prev_y = prev_bbox.get('top', 0)
            curr_y = curr_bbox.get('top', 0)
            
            # If current item is significantly above previous (more than a line height)
            if curr_y < prev_y - 20:
                order_issues += 1
                
        print(f"  ✓ Found {order_issues} potential ordering issues")
        
        if order_issues > len(items) * 0.1:
            self.warnings.append(f"Many ordering issues ({order_issues}) - items may not be in reading order")
            
    def check_types(self):
        """Check item type distribution"""
        print("\n🔍 Checking item types...")
        
        items = self.data.get('items', [])
        type_counts = {}
        
        for item in items:
            item_type = item.get('type', 'Unknown')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
        print("  ✓ Type distribution:")
        for item_type, count in sorted(type_counts.items()):
            print(f"    - {item_type}: {count}")
            
        # Check if types make sense
        if 'Unknown' in type_counts and type_counts['Unknown'] > len(items) * 0.5:
            self.warnings.append("Many items have unknown type - classification may be failing")
            
    def check_font_info(self):
        """Check font information"""
        print("\n🔍 Checking font information...")
        
        items = self.data.get('items', [])
        items_with_font = 0
        font_sizes = []
        
        for item in items:
            if 'attributes' in item and 'style' in item['attributes']:
                style = item['attributes']['style']
                if 'font_size' in style:
                    items_with_font += 1
                    font_sizes.append(style['font_size'])
                    
        print(f"  ✓ Items with font info: {items_with_font}/{len(items)}")
        
        if font_sizes:
            print(f"  ✓ Font size range: {min(font_sizes):.1f} - {max(font_sizes):.1f}")
            
        if items_with_font < len(items) * 0.5:
            self.warnings.append("Many items missing font information")
            
    def check_page_info(self):
        """Check page information"""
        print("\n🔍 Checking page information...")
        
        pages = self.data.get('pages', [])
        if not pages:
            self.issues.append("No page information found")
            return
            
        for i, page in enumerate(pages):
            print(f"  ✓ Page {i+1}:")
            print(f"    - Size: {page.get('width', 'unknown')} x {page.get('height', 'unknown')}")
            print(f"    - Columns: {page.get('columns', 'unknown')}")
            
    def generate_report(self):
        """Generate analysis report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.json_path.parent / f"extraction_analysis_{timestamp}.txt"
        
        with open(report_path, 'w') as f:
            f.write("EXTRACTION ANALYSIS REPORT\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"JSON file: {self.json_path}\n")
            f.write(f"Analysis time: {datetime.now()}\n\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total items: {self.stats.get('items_count', 0)}\n")
            f.write(f"Total pages: {self.stats.get('pages_count', 0)}\n")
            f.write(f"Issues found: {len(self.issues)}\n")
            f.write(f"Warnings: {len(self.warnings)}\n\n")
            
            # Issues
            if self.issues:
                f.write("CRITICAL ISSUES (likely extraction problems)\n")
                f.write("-" * 30 + "\n")
                for issue in self.issues:
                    f.write(f"❌ {issue}\n")
                f.write("\n")
                
            # Warnings
            if self.warnings:
                f.write("WARNINGS (may affect quality)\n")
                f.write("-" * 30 + "\n")
                for warning in self.warnings:
                    f.write(f"⚠️  {warning}\n")
                f.write("\n")
                
            # Recommendations
            f.write("RECOMMENDATIONS\n")
            f.write("-" * 30 + "\n")
            
            if self.issues:
                f.write("The extraction has critical issues that need to be fixed:\n")
                for issue in self.issues:
                    if "coordinate" in issue.lower():
                        f.write("- Check coordinate system conversion in the extractor\n")
                    elif "text" in issue.lower():
                        f.write("- Review text extraction logic, may need different PDF library\n")
                    elif "overlap" in issue.lower():
                        f.write("- Text blocks may be incorrectly merged or split\n")
            else:
                f.write("✅ Extraction appears to be working correctly!\n")
                f.write("   Any display issues are likely in the rendering (Chonker3) side.\n")
                
        print(f"\n📄 Report saved to: {report_path}")
        
        # Also create a visual HTML report
        self.create_visual_report()
        
        return report_path
        
    def create_visual_report(self):
        """Create HTML visualization of the extraction"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_path = self.json_path.parent / f"extraction_visual_{timestamp}.html"
        
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Extraction Visualization</title>
    <style>
        body { font-family: Arial; margin: 20px; }
        .page { 
            position: relative; 
            border: 2px solid #333; 
            margin: 20px auto;
            background: white;
        }
        .item {
            position: absolute;
            border: 1px solid rgba(0,0,0,0.3);
            font-size: 10px;
            overflow: hidden;
            cursor: pointer;
        }
        .item:hover { background: rgba(255,255,0,0.3); }
        .TextItem { background: rgba(0,0,0,0.05); }
        .TitleItem { background: rgba(0,0,255,0.1); font-weight: bold; }
        .TableItem { background: rgba(255,0,0,0.1); }
        #info {
            position: fixed;
            right: 20px;
            top: 20px;
            width: 300px;
            background: #f0f0f0;
            padding: 15px;
            border: 1px solid #ccc;
        }
        .issue { color: red; }
        .warning { color: orange; }
    </style>
</head>
<body>
    <div id="info">
        <h3>Extraction Info</h3>
        <div id="details"></div>
    </div>
"""
        
        # Add pages
        pages = self.data.get('pages', [{'width': 612, 'height': 792}])
        items = self.data.get('items', [])
        
        # Group items by page
        items_by_page = {}
        for item in items:
            page = item.get('page', 1) - 1
            if page not in items_by_page:
                items_by_page[page] = []
            items_by_page[page].append(item)
            
        for i, page in enumerate(pages):
            page_width = page.get('width', 612)
            page_height = page.get('height', 792)
            
            # Scale to fit screen
            scale = min(800 / page_width, 1000 / page_height)
            
            html += f'<div class="page" style="width:{page_width*scale}px;height:{page_height*scale}px;">\n'
            html += f'<div style="position:absolute;top:5px;left:5px;color:#999;">Page {i+1}</div>\n'
            
            # Add items
            for item in items_by_page.get(i, []):
                bbox = item.get('bbox', {})
                content = item.get('content', '').strip()[:50]
                item_type = item.get('type', 'TextItem')
                
                left = bbox.get('left', 0) * scale
                top = bbox.get('top', 0) * scale
                width = bbox.get('width', 100) * scale
                height = bbox.get('height', 20) * scale
                
                # Handle coordinate system
                if 'BOTTOMLEFT' in bbox.get('coord_origin', ''):
                    top = (page_height - bbox.get('top', 0) - bbox.get('height', 0)) * scale
                    
                html += f'<div class="item {item_type}" '
                html += f'style="left:{left}px;top:{top}px;width:{width}px;height:{height}px;" '
                html += f'data-info="{content}" onclick="showInfo(this)">{content}</div>\n'
                
            html += '</div>\n'
            
        html += """
<script>
function showInfo(elem) {
    document.getElementById('details').innerHTML = 
        '<strong>Content:</strong> ' + elem.dataset.info + '<br>' +
        '<strong>Position:</strong> ' + elem.style.left + ', ' + elem.style.top;
}
</script>
</body>
</html>"""
        
        with open(html_path, 'w') as f:
            f.write(html)
            
        print(f"🎨 Visual report saved to: {html_path}")
        subprocess.run(["open", str(html_path)])

def main():
    if len(sys.argv) < 2:
        print("Usage: python extraction_analyzer.py <json_file>")
        print("\nThis will analyze the extraction JSON to identify issues.")
        return
        
    json_path = sys.argv[1]
    analyzer = ExtractionAnalyzer(json_path)
    analyzer.analyze()

if __name__ == "__main__":
    main()
