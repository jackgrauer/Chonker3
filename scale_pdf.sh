#!/bin/bash
# Simple PDF scaling using command line tools

if [ $# -lt 1 ]; then
    echo "Usage: $0 <pdf_file> [scale_factor]"
    echo "Example: $0 document.pdf 2"
    exit 1
fi

INPUT_PDF="$1"
SCALE=${2:-2}
OUTPUT_PDF="${INPUT_PDF%.pdf}_scaled_${SCALE}x.pdf"

echo "📄 Scaling PDF by ${SCALE}x..."
echo "Input: $INPUT_PDF"
echo "Output: $OUTPUT_PDF"

# Method 1: Try Ghostscript (most reliable)
if command -v gs &> /dev/null; then
    echo "🔧 Using Ghostscript..."
    
    # Calculate new dimensions (assuming letter size, adjust as needed)
    WIDTH=$(echo "612 * $SCALE" | bc)
    HEIGHT=$(echo "792 * $SCALE" | bc)
    
    gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
       -dDEVICEWIDTHPOINTS=$WIDTH \
       -dDEVICEHEIGHTPOINTS=$HEIGHT \
       -dFIXEDMEDIA -dPDFFitPage \
       -sOutputFile="$OUTPUT_PDF" \
       "$INPUT_PDF"
       
    if [ $? -eq 0 ]; then
        echo "✅ Scaling successful!"
        echo "🔍 Now extract from: $OUTPUT_PDF"
        
        # Try to run extraction
        if [ -f "pypdfium2_proper_extractor.py" ]; then
            echo "📊 Running extraction..."
            python3 pypdfium2_proper_extractor.py "$OUTPUT_PDF"
        fi
        exit 0
    else
        echo "❌ Ghostscript failed"
    fi
fi

# Method 2: Try ImageMagick
if command -v convert &> /dev/null; then
    echo "🔧 Using ImageMagick..."
    
    # Higher density for better quality
    DENSITY=$(echo "150 * $SCALE" | bc)
    PERCENT=$(echo "$SCALE * 100" | bc)
    
    convert -density $DENSITY "$INPUT_PDF" -resize ${PERCENT}% "$OUTPUT_PDF"
    
    if [ $? -eq 0 ]; then
        echo "✅ Scaling successful!"
        exit 0
    else
        echo "❌ ImageMagick failed"
    fi
fi

# Method 3: Try pdfjam (if available)
if command -v pdfjam &> /dev/null; then
    echo "🔧 Using pdfjam..."
    
    pdfjam --outfile "$OUTPUT_PDF" --paper "letter" --scale $SCALE "$INPUT_PDF"
    
    if [ $? -eq 0 ]; then
        echo "✅ Scaling successful!"
        exit 0
    else
        echo "❌ pdfjam failed"
    fi
fi

echo "❌ No PDF scaling tools found!"
echo "Please install one of: ghostscript, imagemagick, or pdfjam"
echo ""
echo "On macOS:"
echo "  brew install ghostscript"
echo "  brew install imagemagick"
echo "  brew install mactex  # for pdfjam"
