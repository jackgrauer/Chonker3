#!/bin/bash
# Make analysis scripts executable

chmod +x extraction_analyzer.py
chmod +x extract_and_analyze.py

echo "✅ Analysis scripts are now executable"
echo ""
echo "To analyze if issues are in extraction or rendering:"
echo "  ./extract_and_analyze.py /path/to/your.pdf"
echo ""
echo "This will:"
echo "1. Extract the PDF to JSON"
echo "2. Analyze the JSON for extraction issues" 
echo "3. Create a visual HTML report"
echo "4. Tell you if the problem is in extraction (Docling) or rendering (Chonker3)"
