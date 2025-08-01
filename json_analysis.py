#!/usr/bin/env python3
"""
Alternative automation that analyzes the extracted JSON directly
This bypasses UI automation issues
"""

import subprocess
import json
import time
import os
from pathlib import Path
from datetime import datetime
import tempfile

class JSONAnalysisAutomation:
    def __init__(self, pdf_path=None):
        self.project_dir = Path("/Users/jack/chonker3-new")
        self.pdf_path = pdf_path or "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
        self.results_dir = self.project_dir / "extraction_results"
        self.results_dir.mkdir(exist_ok=True)
        
    def extract_pdf_directly(self):
        """Run the Python extractor directly"""
        print("🔍 Extracting PDF directly...")
        
        # Use the pypdfium2 extractor
        extractor_script = self.project_dir / "pypdfium2_proper_extractor.py"
        
        if not extractor_script.exists():
            print("❌ Extractor script not found")
            return None
            
        # Run the extractor
        result = subprocess.run(
            [sys.executable, str(extractor_script), str(self.pdf_path)],
            capture_output=True,
            text=True,
            cwd=self.project_dir
        )
        
        if result.returncode != 0:
            print(f"❌ Extraction failed: {result.stderr}")
            return None
            
        # Parse the output to find JSON path
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines:
            if "json_path" in line:
                # Extract JSON path from the output
                try:
                    import re
                    match = re.search(r'"json_path":\s*"([^"]+)"', line)
                    if match:
                        json_path = match.group(1)
                        print(f"✅ Extracted to: {json_path}")
                        return json_path
                except:
                    pass
                    
        print("❌ Could not find JSON output path")
        return None
        
    def analyze_extraction(self, json_path):
        """Analyze the extracted JSON data"""
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        analysis_path = self.results_dir / f"analysis_{timestamp}.txt"
        
        with open(analysis_path, 'w') as f:
            f.write("CHONKER3 EXTRACTION ANALYSIS\n")
            f.write("=" * 50 + "\n\n")
            
            # Summary stats
            f.write(f"PDF: {self.pdf_path}\n")
            f.write(f"Total items extracted: {len(data.get('items', []))}\n")
            f.write(f"Pages: {len(data.get('pages', []))}\n\n")
            
            # Analyze item types
            item_types = {}
            for item in data.get('items', []):
                item_type = item.get('type', 'Unknown')
                item_types[item_type] = item_types.get(item_type, 0) + 1
                
            f.write("Item Types:\n")
            for itype, count in sorted(item_types.items()):
                f.write(f"  - {itype}: {count}\n")
            f.write("\n")
            
            # Analyze text quality
            f.write("Sample Text Items:\n")
            f.write("-" * 30 + "\n")
            
            for i, item in enumerate(data.get('items', [])[:10]):
                content = item.get('content', '').strip()
                if content:
                    bbox = item.get('bbox', {})
                    f.write(f"\nItem {i+1}:\n")
                    f.write(f"  Type: {item.get('type', 'Unknown')}\n")
                    f.write(f"  Position: ({bbox.get('left', 0):.1f}, {bbox.get('top', 0):.1f})\n")
                    f.write(f"  Size: {bbox.get('width', 0):.1f} x {bbox.get('height', 0):.1f}\n")
                    f.write(f"  Text: {content[:100]}{'...' if len(content) > 100 else ''}\n")
                    
            # Check for common issues
            f.write("\n\nPotential Issues:\n")
            f.write("-" * 30 + "\n")
            
            issues = []
            
            # Check for overlapping text
            items_by_page = {}
            for item in data.get('items', []):
                page = item.get('page', 1)
                if page not in items_by_page:
                    items_by_page[page] = []
                items_by_page[page].append(item)
                
            for page, page_items in items_by_page.items():
                for i, item1 in enumerate(page_items):
                    bbox1 = item1.get('bbox', {})
                    for item2 in page_items[i+1:]:
                        bbox2 = item2.get('bbox', {})
                        
                        # Check overlap
                        if (bbox1.get('left', 0) < bbox2.get('left', 0) + bbox2.get('width', 0) and
                            bbox1.get('left', 0) + bbox1.get('width', 0) > bbox2.get('left', 0) and
                            bbox1.get('top', 0) < bbox2.get('top', 0) + bbox2.get('height', 0) and
                            bbox1.get('top', 0) + bbox1.get('height', 0) > bbox2.get('top', 0)):
                            issues.append(f"Overlapping text on page {page}")
                            break
                            
            # Check for missing content
            total_text_length = sum(len(item.get('content', '')) for item in data.get('items', []))
            if total_text_length < 100:
                issues.append("Very little text extracted")
                
            # Check for coordinate system issues
            for item in data.get('items', []):
                bbox = item.get('bbox', {})
                if bbox.get('top', 0) > 1000:  # Assuming standard page height
                    issues.append("Possible coordinate system issue (very large Y values)")
                    break
                    
            if issues:
                for issue in set(issues):  # Remove duplicates
                    f.write(f"  ⚠️  {issue}\n")
            else:
                f.write("  ✅ No major issues detected\n")
                
        print(f"📊 Analysis saved to: {analysis_path}")
        return analysis_path
        
    def create_visual_test(self, json_path):
        """Create a simple HTML visualization of the extraction"""
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_path = self.results_dir / f"visual_test_{timestamp}.html"
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Chonker3 Extraction Visualization</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px;
            background: #f0f0f0;
        }
        .page {
            background: white;
            width: 816px;
            height: 1056px;
            margin: 20px auto;
            position: relative;
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .item {
            position: absolute;
            border: 1px solid rgba(0,0,0,0.2);
            padding: 2px;
            font-size: 12px;
            overflow: hidden;
            cursor: pointer;
        }
        .item:hover {
            background: rgba(26, 188, 156, 0.2);
            border-color: #1ABC9C;
        }
        .TextItem { background: rgba(255,255,255,0.8); }
        .TitleItem { background: rgba(52, 152, 219, 0.2); font-weight: bold; }
        .SectionHeaderItem { background: rgba(41, 128, 185, 0.2); font-weight: bold; }
        .TableItem { background: rgba(231, 76, 60, 0.1); }
        .FormField { background: rgba(46, 204, 113, 0.2); }
        .info {
            position: fixed;
            top: 10px;
            right: 10px;
            background: white;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            max-width: 300px;
        }
    </style>
</head>
<body>
    <div class="info">
        <h3>Extraction Info</h3>
        <p>Total items: <span id="total-items">0</span></p>
        <p>Click on items to see details</p>
        <div id="item-details"></div>
    </div>
"""
        
        # Group items by page
        items_by_page = {}
        for item in data.get('items', []):
            page = item.get('page', 1) - 1  # 0-indexed
            if page not in items_by_page:
                items_by_page[page] = []
            items_by_page[page].append(item)
            
        # Create page divs
        for page_num in range(len(data.get('pages', [1]))):
            html_content += f'<div class="page" id="page-{page_num}">\n'
            html_content += f'<div style="position:absolute;top:5px;left:5px;color:#999;">Page {page_num + 1}</div>\n'
            
            # Add items for this page
            for item in items_by_page.get(page_num, []):
                bbox = item.get('bbox', {})
                content = item.get('content', '').strip()
                item_type = item.get('type', 'TextItem')
                
                # Scale coordinates to fit standard page size
                left = bbox.get('left', 0) * 1.33
                top = bbox.get('top', 0) * 1.33
                width = bbox.get('width', 100) * 1.33
                height = bbox.get('height', 20) * 1.33
                
                # Handle coordinate system
                coord_origin = bbox.get('coord_origin', 'TOPLEFT')
                if 'BOTTOMLEFT' in coord_origin:
                    # Convert from bottom-left to top-left
                    page_height = 792  # Standard US Letter
                    top = page_height - top - height
                    
                style = f"left:{left}px;top:{top}px;width:{width}px;height:{height}px;"
                
                html_content += f'<div class="item {item_type}" style="{style}" '
                html_content += f'data-content="{content[:100]}" data-type="{item_type}">'
                html_content += f'{content[:50]}{"..." if len(content) > 50 else ""}'
                html_content += '</div>\n'
                
            html_content += '</div>\n'
            
        html_content += """
<script>
    // Count total items
    document.getElementById('total-items').textContent = document.querySelectorAll('.item').length;
    
    // Item click handler
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('item')) {
            const details = document.getElementById('item-details');
            details.innerHTML = '<h4>Item Details:</h4>' +
                '<p><strong>Type:</strong> ' + e.target.dataset.type + '</p>' +
                '<p><strong>Content:</strong> ' + e.target.dataset.content + '</p>' +
                '<p><strong>Position:</strong> ' + e.target.style.left + ', ' + e.target.style.top + '</p>';
        }
    });
</script>
</body>
</html>
"""
        
        with open(html_path, 'w') as f:
            f.write(html_content)
            
        print(f"🎨 Visual test saved to: {html_path}")
        return html_path
        
    def run_analysis(self):
        """Run the complete analysis workflow"""
        print("🚀 Starting Chonker3 JSON Analysis")
        print(f"📄 PDF: {self.pdf_path}\n")
        
        # Extract PDF
        json_path = self.extract_pdf_directly()
        if not json_path:
            return
            
        # Analyze extraction
        analysis_path = self.analyze_extraction(json_path)
        
        # Create visual test
        visual_path = self.create_visual_test(json_path)
        
        # Open results
        subprocess.run(["open", str(analysis_path)])
        subprocess.run(["open", str(visual_path)])
        
        print("\n✅ Analysis complete!")
        print(f"📁 Results saved in: {self.results_dir}")
        
        # Also copy the JSON for easy access
        import shutil
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_copy = self.results_dir / f"extracted_{timestamp}.json"
        shutil.copy2(json_path, json_copy)
        print(f"📋 JSON copied to: {json_copy}")

def main():
    import sys
    
    pdf_path = None
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        
    analyzer = JSONAnalysisAutomation(pdf_path)
    analyzer.run_analysis()

if __name__ == "__main__":
    main()
