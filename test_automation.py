#!/usr/bin/env python3
"""
Automated testing script for chonker3
Opens the app, loads a PDF, extracts, takes screenshot, and closes
"""
import subprocess
import time
import os
import sys

def run_test_cycle():
    """Run one test cycle of chonker3"""
    pdf_path = "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
    screenshot_path = "/tmp/chonker3_screenshot.png"
    
    print("Starting chonker3...")
    # Start chonker3 in background
    process = subprocess.Popen(["./target/release/chonker3"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    
    # Give it time to start
    time.sleep(3)
    
    # Use AppleScript to control the app
    applescript = f'''
    tell application "System Events"
        -- Wait for chonker3 window
        repeat 10 times
            if exists (window 1 of process "chonker3") then
                exit repeat
            end if
            delay 0.5
        end repeat
        
        -- Click Open button
        tell process "chonker3"
            set frontmost to true
            delay 0.5
            
            -- Click the Open button (it's in the top right)
            click button "Open" of window 1
            delay 1
        end tell
    end tell
    
    -- Handle file dialog
    tell application "System Events"
        keystroke "g" using {{shift down, command down}}
        delay 0.5
        keystroke "{pdf_path}"
        delay 0.5
        keystroke return
        delay 0.5
        keystroke return
        delay 1
        
        -- Click Extract button
        tell process "chonker3"
            click button "Extract" of window 1
        end tell
        
        -- Wait for extraction to complete
        delay 5
    end tell
    '''
    
    print("Running AppleScript to control app...")
    result = subprocess.run(['osascript', '-e', applescript], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"AppleScript error: {result.stderr}")
        # Try to continue anyway
    
    # Take screenshot
    print("Taking screenshot...")
    subprocess.run(['screencapture', '-w', screenshot_path])
    time.sleep(1)
    
    # Kill chonker3
    print("Closing chonker3...")
    process.terminate()
    process.wait()
    
    return screenshot_path

if __name__ == "__main__":
    screenshot = run_test_cycle()
    print(f"Screenshot saved to: {screenshot}")
    print("Opening screenshot for analysis...")
    subprocess.run(['open', screenshot])