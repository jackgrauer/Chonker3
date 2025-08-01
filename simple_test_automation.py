#!/usr/bin/env python3
"""
Simplified automation script for Chonker3 testing
This version takes screenshots and saves them for manual analysis
"""

import subprocess
import time
import os
from datetime import datetime
from pathlib import Path

class SimpleChonkerTest:
    def __init__(self, pdf_path=None):
        self.project_dir = Path("/Users/jack/chonker3-new")
        self.pdf_path = pdf_path or "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
        self.screenshot_dir = self.project_dir / "test_screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        
    def run_test(self):
        """Run a single test and capture screenshot"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = self.screenshot_dir / f"test_{timestamp}.png"
        
        print("🔨 Building Chonker3...")
        # Build
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Build failed: {result.stderr}")
            return None
            
        print("✅ Build successful")
        
        # Start the app
        print("🚀 Starting Chonker3...")
        process = subprocess.Popen(
            ["./target/release/chonker3"],
            cwd=self.project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for startup
        time.sleep(3)
        
        # Automate the interaction
        applescript = f'''
        tell application "System Events"
            repeat 10 times
                if exists (window 1 of process "chonker3") then
                    exit repeat
                end if
                delay 0.5
            end repeat
            
            tell process "chonker3"
                set frontmost to true
                delay 0.5
                click button "Open" of window 1
                delay 1
            end tell
        end tell
        
        tell application "System Events"
            keystroke "g" using {{shift down, command down}}
            delay 0.5
            keystroke "{self.pdf_path}"
            delay 0.5
            keystroke return
            delay 0.5
            keystroke return
            delay 2
            
            tell process "chonker3"
                click button "Extract" of window 1
            end tell
            
            delay 8
        end tell
        '''
        
        print("🤖 Running automation...")
        subprocess.run(['osascript', '-e', applescript], capture_output=True)
        
        # Take screenshot
        print("📸 Taking screenshot...")
        # Method 1: Try window-specific capture
        try:
            window_id_script = 'tell app "chonker3" to id of window 1'
            result = subprocess.run(['osascript', '-e', window_id_script], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                window_id = result.stdout.strip()
                subprocess.run(['screencapture', '-l', window_id, str(screenshot_path)])
            else:
                raise Exception("Could not get window ID")
        except:
            # Method 2: Interactive window capture
            print("Click on the Chonker3 window...")
            subprocess.run(['screencapture', '-w', str(screenshot_path)])
            time.sleep(2)
        
        # Close the app
        print("🛑 Closing Chonker3...")
        process.terminate()
        process.wait()
        
        if screenshot_path.exists():
            print(f"✅ Screenshot saved: {screenshot_path}")
            # Open the screenshot
            subprocess.run(["open", str(screenshot_path)])
            return str(screenshot_path)
        else:
            print("❌ Screenshot failed")
            return None

def main():
    import sys
    
    pdf_path = None
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    
    tester = SimpleChonkerTest(pdf_path)
    result = tester.run_test()
    
    if result:
        print(f"\n📁 Screenshots directory: {tester.screenshot_dir}")
        print("You can now analyze the screenshot and make improvements")

if __name__ == "__main__":
    main()
