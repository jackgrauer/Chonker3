#!/usr/bin/env python3
"""
Extract and analyze - helps identify if issues are in extraction or rendering
"""

import subprocess
import sys
import json
import time
from pathlib import Path
from datetime import datetime

def run_extraction(pdf_path):
    """Run the extraction and return JSON path"""
    print(f"📄 Extracting: {pdf_path}")
    
    # Find extractor
    extractors = [
        "pypdfium2_proper_extractor.py",
        "simple_extractor_fixed.py",
        "simple_extractor.py"
    ]
    
    for extractor_name in extractors:
        extractor = Path(extractor_name)
        if extractor.exists():
            print(f"🔧 Using extractor: {extractor_name}")
            
            result = subprocess.run(
                [sys.executable, str(extractor), pdf_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Parse output for JSON path
                output = result.stdout
                print(f"✅ Extraction successful")
                
                # Look for json_path in output
                for line in output.split('\n'):
                    if 'json_path' in line and '.json' in line:
                        import re
                        match = re.search(r'["\']([^"\']*\.json)["\']', line)
                        if match:
                            json_path = match.group(1)
                            print(f"📋 JSON saved to: {json_path}")
                            return json_path
                            
                # If not found in output, check temp directory
                import tempfile
                import os
                temp_dir = tempfile.gettempdir()
                for file in os.listdir(temp_dir):
                    if file.endswith('_chonker3.json') and file.startswith('tmp'):
                        full_path = os.path.join(temp_dir, file)
                        # Check if recent (within last minute)
                        if time.time() - os.path.getmtime(full_path) < 60:
                            print(f"📋 Found JSON: {full_path}")
                            return full_path
                            
            else:
                print(f"❌ Extraction failed: {result.stderr}")
                
    print("❌ No working extractor found")
    return None

def analyze_json(json_path):
    """Quick analysis of the JSON"""
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    print("\n📊 EXTRACTION SUMMARY")
    print("=" * 50)
    
    items = data.get('items', [])
    pages = data.get('pages', [])
    
    print(f"Total items: {len(items)}")
    print(f"Total pages: {len(pages)}")
    
    # Check for common issues
    issues = []
    
    # 1. Check if extraction worked at all
    if len(items) == 0:
        issues.append("❌ NO ITEMS EXTRACTED - Complete extraction failure")
    elif len(items) < 10:
        issues.append("⚠️  Very few items extracted")
        
    # 2. Check coordinate systems
    coord_systems = set()
    for item in items:
        bbox = item.get('bbox', {})
        coord_systems.add(bbox.get('coord_origin', 'UNKNOWN'))
        
    if len(coord_systems) > 1:
        issues.append(f"⚠️  Mixed coordinate systems: {coord_systems}")
        
    # 3. Check for empty content
    empty_count = sum(1 for item in items if not item.get('content', '').strip())
    if empty_count > 0:
        issues.append(f"⚠️  {empty_count} items have empty content")
        
    # 4. Check for overlaps (simple check)
    overlap_count = 0
    items_by_page = {}
    for item in items:
        page = item.get('page', 1)
        if page not in items_by_page:
            items_by_page[page] = []
        items_by_page[page].append(item)
        
    for page_items in items_by_page.values():
        for i, item1 in enumerate(page_items):
            for item2 in page_items[i+1:]:
                bbox1 = item1.get('bbox', {})
                bbox2 = item2.get('bbox', {})
                
                # Simple overlap check
                if (abs(bbox1.get('left', 0) - bbox2.get('left', 0)) < 5 and
                    abs(bbox1.get('top', 0) - bbox2.get('top', 0)) < 5):
                    overlap_count += 1
                    
    if overlap_count > 10:
        issues.append(f"⚠️  Many overlapping items ({overlap_count})")
        
    # 5. Sample content
    print("\n📝 Sample extracted text:")
    print("-" * 30)
    for i, item in enumerate(items[:5]):
        content = item.get('content', '').strip()
        if content:
            print(f"{i+1}. {content[:60]}{'...' if len(content) > 60 else ''}")
            
    # Print issues
    if issues:
        print("\n⚠️  ISSUES FOUND:")
        print("-" * 30)
        for issue in issues:
            print(issue)
            
        print("\n🔍 DIAGNOSIS:")
        if any("NO ITEMS" in issue for issue in issues):
            print("→ EXTRACTION PROBLEM: The PDF extraction is completely failing")
            print("  Possible solutions:")
            print("  - Try a different PDF library (pymupdf, pdfplumber)")
            print("  - Check if PDF has text layer or is just images")
        elif any("coordinate" in issue.lower() for issue in issues):
            print("→ EXTRACTION PROBLEM: Coordinate system issues in extraction")
            print("  The extractor is producing inconsistent coordinates")
        elif any("overlap" in issue.lower() for issue in issues):
            print("→ EXTRACTION PROBLEM: Text detection/grouping issues")
            print("  Text blocks are being incorrectly identified")
        else:
            print("→ Likely RENDERING PROBLEM in Chonker3")
            print("  The extraction looks OK, issues are in display")
    else:
        print("\n✅ EXTRACTION LOOKS GOOD!")
        print("→ Any issues are likely in Chonker3's rendering code")
        
    return len(issues) == 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_and_analyze.py <pdf_file>")
        return
        
    pdf_path = sys.argv[1]
    
    # Extract
    json_path = run_extraction(pdf_path)
    if not json_path:
        print("❌ Extraction failed")
        return
        
    # Analyze
    print(f"\n🔍 Analyzing extraction...")
    is_good = analyze_json(json_path)
    
    # Run detailed analyzer
    print(f"\n📊 Running detailed analysis...")
    analyzer_script = Path("extraction_analyzer.py")
    if analyzer_script.exists():
        subprocess.run([sys.executable, str(analyzer_script), json_path])
    else:
        print("⚠️  Detailed analyzer not found")
        
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    if is_good:
        print("✅ Extraction is working correctly")
        print("→ Focus on fixing Chonker3's rendering code")
    else:
        print("❌ Extraction has issues")
        print("→ Fix the extraction first before debugging rendering")
        
    print(f"\nJSON file: {json_path}")

if __name__ == "__main__":
    main()
