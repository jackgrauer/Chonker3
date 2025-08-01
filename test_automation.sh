#!/bin/bash
# Automated test script for chonker3

PDF_PATH="/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
SCREENSHOT_PATH="/tmp/chonker3_test.png"

# Kill any existing chonker3
pkill -f chonker3 2>/dev/null

# Start chonker3
echo "Starting chonker3..."
./target/release/chonker3 &
CHONKER_PID=$!

# Wait for app to start
sleep 3

# Use AppleScript to automate the UI
osascript <<EOF
tell application "System Events"
    -- Make sure chonker3 is frontmost
    set frontmost of process "chonker3" to true
    delay 1
    
    -- Click Open button using UI elements
    tell process "chonker3"
        -- Find and click the Open button
        click (first button whose title is "Open") of window 1
    end tell
    delay 1
    
    -- In file dialog, use keyboard shortcut to go to path
    keystroke "g" using {shift down, command down}
    delay 0.5
    keystroke "$PDF_PATH"
    delay 0.5
    keystroke return
    delay 1
    keystroke return -- Select the file
    delay 2
    
    -- Click Extract button
    tell process "chonker3"
        click (first button whose title is "Extract") of window 1
    end tell
    
    -- Wait for extraction
    delay 8
end tell
EOF

# Take a screenshot of the window
echo "Taking screenshot..."
screencapture -l $(osascript -e 'tell app "chonker3" to id of window 1') "$SCREENSHOT_PATH"

# Kill chonker3
kill $CHONKER_PID 2>/dev/null

echo "Screenshot saved to: $SCREENSHOT_PATH"