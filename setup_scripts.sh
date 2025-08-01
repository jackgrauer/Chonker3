#!/bin/bash
# Make all Python scripts executable

echo "Making scripts executable..."

chmod +x automated_dev_loop.py
chmod +x simple_test_automation.py
chmod +x smart_automation.py
chmod +x robust_test.py
chmod +x json_analysis.py
chmod +x working_test.py

echo "✅ All scripts are now executable"
echo ""
echo "Available test scripts:"
echo "  ./working_test.py      - Interactive test runner (RECOMMENDED)"
echo "  ./json_analysis.py     - Analyze extraction JSON directly"
echo "  ./robust_test.py       - Robust automation with debugging"
echo ""
echo "Quick start:"
echo "  ./working_test.py"
echo "  Then choose option 1 for manual test with commands"
