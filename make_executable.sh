#!/bin/bash
# Make automation scripts executable

chmod +x automated_dev_loop.py
chmod +x simple_test_automation.py
chmod +x smart_automation.py

echo "✅ Scripts are now executable"
echo ""
echo "Usage:"
echo "  ./simple_test_automation.py        - Run a simple test and take screenshot"
echo "  ./smart_automation.py             - Interactive improvement loop"
echo "  ./automated_dev_loop.py           - Full Claude-powered automation (requires API key)"
echo ""
echo "For Claude automation, set your API key:"
echo "  export ANTHROPIC_API_KEY=your-key-here"
