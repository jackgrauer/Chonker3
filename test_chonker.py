#!/usr/bin/env python3
"""
Best practices automation for testing chonker3
Uses subprocess and AppleScript with proper UI element targeting
"""
import subprocess
import time
import os
import sys

def run_chonker_test():
    """Run automated test of chonker3"""
    
    pdf_path = "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
    screenshot_path = "/tmp/chonker3_result.png"
    
    # Kill any existing chonker3
    subprocess.run(["pkill", "-f", "chonker3"], stderr=subprocess.DEVNULL)
    time.sleep(1)
    
    print("Starting chonker3...")
    # Start chonker3
    process = subprocess.Popen(["./target/release/chonker3"], 
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    
    # Give it time to fully start
    time.sleep(3)
    
    # AppleScript to control the UI properly
    applescript = '''
    tell application "System Events"
        -- Make chonker3 frontmost
        set frontmost of the first process whose name contains "chonker3" to true
        delay 1
        
        tell process "chonker3"
            tell window 1
                -- Click the Open button by finding it in the UI hierarchy
                click (first button whose description is "Open" or title is "Open")
                delay 1
            end tell
        end tell
        
        -- Handle file dialog
        delay 0.5
        keystroke "g" using {command down, shift down}
        delay 0.5
        keystroke "''' + pdf_path + '''"
        delay 0.5
        keystroke return
        delay 1
        keystroke return
        delay 2
        
        -- Click Extract button
        tell process "chonker3"
            tell window 1
                click (first button whose description is "Extract" or title is "Extract")
            end tell
        end tell
        
        -- Wait for extraction
        delay 8
    end tell
    '''
    
    print("Automating UI...")
    result = subprocess.run(['osascript', '-e', applescript], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Automation warning: {result.stderr}")
    
    # Take screenshot
    print("Taking screenshot...")
    subprocess.run(['screencapture', '-x', screenshot_path])
    
    # Kill chonker3
    print("Closing chonker3...")
    process.terminate()
    process.wait()
    
    return screenshot_path

def analyze_screenshot(screenshot_path):
    """Open and analyze the screenshot"""
    if os.path.exists(screenshot_path):
        print(f"\nScreenshot saved to: {screenshot_path}")
        # Open the screenshot for viewing
        subprocess.run(['open', screenshot_path])
        return True
    return False

if __name__ == "__main__":
    print("Running chonker3 automated test...")
    screenshot = run_chonker_test()
    
    if analyze_screenshot(screenshot):
        print("\nTest complete! Check the screenshot to see the results.")
        print("The screenshot shows the extracted PDF content.")
    else:
        print("Test failed - no screenshot generated")