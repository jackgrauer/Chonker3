#!/usr/bin/env python3
"""
Improved automation script with better UI control and debugging
"""

import subprocess
import time
import os
from datetime import datetime
from pathlib import Path
import sys

class RobustChonkerTest:
    def __init__(self, pdf_path=None):
        self.project_dir = Path("/Users/jack/chonker3-new")
        self.pdf_path = pdf_path or "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
        self.screenshot_dir = self.project_dir / "test_screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        
    def check_accessibility_permissions(self):
        """Check if we have accessibility permissions"""
        print("🔍 Checking accessibility permissions...")
        
        # Try a simple AppleScript test
        test_script = '''
        tell application "System Events"
            return (name of first process whose frontmost is true)
        end tell
        '''
        
        result = subprocess.run(['osascript', '-e', test_script], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print("⚠️  No accessibility permissions!")
            print("Please grant Terminal accessibility permissions:")
            print("System Preferences > Security & Privacy > Privacy > Accessibility")
            print("Add Terminal (or your terminal app) and check the box")
            return False
        else:
            print("✅ Accessibility permissions OK")
            return True
            
    def wait_for_window(self, app_name="chonker3", timeout=10):
        """Wait for application window to appear"""
        print(f"⏳ Waiting for {app_name} window...")
        
        check_script = f'''
        tell application "System Events"
            if exists (process "{app_name}") then
                return exists (window 1 of process "{app_name}")
            else
                return false
            end if
        end tell
        '''
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = subprocess.run(['osascript', '-e', check_script], 
                                  capture_output=True, text=True)
            if result.stdout.strip() == "true":
                print("✅ Window found!")
                return True
            time.sleep(0.5)
            
        print("❌ Window not found within timeout")
        return False
        
    def debug_ui_elements(self):
        """Debug what UI elements are visible"""
        debug_script = '''
        tell application "System Events"
            tell process "chonker3"
                set allElements to {}
                
                -- Get window info
                if exists window 1 then
                    set windowName to name of window 1
                    set windowPosition to position of window 1
                    set windowSize to size of window 1
                    
                    -- Get all buttons
                    set buttonList to every button of window 1
                    repeat with btn in buttonList
                        set btnName to name of btn
                        set btnDesc to description of btn
                        set end of allElements to "Button: " & btnName & " (" & btnDesc & ")"
                    end repeat
                    
                    -- Get all UI elements
                    set uiElements to every UI element of window 1
                    repeat with elem in uiElements
                        set elemClass to class of elem
                        set elemDesc to description of elem
                        set end of allElements to "Element: " & (elemClass as string) & " - " & elemDesc
                    end repeat
                    
                    return "Window: " & windowName & " at " & (windowPosition as string) & " size " & (windowSize as string) & return & return & (allElements as string)
                else
                    return "No window found"
                end if
            end tell
        end tell
        '''
        
        result = subprocess.run(['osascript', '-e', debug_script], 
                              capture_output=True, text=True)
        print("🔍 UI Elements found:")
        print(result.stdout)
        
    def run_test_manual_assist(self):
        """Run test with manual assistance for UI interaction"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = self.screenshot_dir / f"test_{timestamp}.png"
        
        # Build
        print("🔨 Building Chonker3...")
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
        
        # Wait for window
        if not self.wait_for_window():
            print("❌ Window didn't appear")
            process.terminate()
            return None
            
        # Make it frontmost
        focus_script = '''
        tell application "System Events"
            set frontmost of process "chonker3" to true
        end tell
        '''
        subprocess.run(['osascript', '-e', focus_script])
        time.sleep(1)
        
        # Debug UI
        self.debug_ui_elements()
        
        print("\n" + "="*50)
        print("📋 MANUAL STEPS REQUIRED:")
        print("1. Click the 'Open' button in Chonker3")
        print("2. Navigate to and select this PDF:")
        print(f"   {self.pdf_path}")
        print("3. Click the 'Extract' button")
        print("4. Wait for extraction to complete")
        print("5. Press Enter here when ready to take screenshot...")
        print("="*50)
        
        input()
        
        # Take screenshot using window ID
        print("📸 Taking screenshot...")
        
        # Method 1: Get window ID and capture
        window_id_script = '''
        tell application "System Events"
            tell process "chonker3"
                return id of window 1
            end tell
        end tell
        '''
        
        result = subprocess.run(['osascript', '-e', window_id_script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            window_id = result.stdout.strip()
            print(f"Window ID: {window_id}")
            
            # Take screenshot of specific window
            screenshot_result = subprocess.run(
                ['screencapture', '-o', '-l', window_id, str(screenshot_path)],
                capture_output=True, text=True
            )
            
            if screenshot_result.returncode != 0:
                print("Window screenshot failed, trying interactive mode...")
                subprocess.run(['screencapture', '-i', str(screenshot_path)])
        else:
            print("Couldn't get window ID, using interactive screenshot...")
            print("Click and drag to select the Chonker3 window")
            subprocess.run(['screencapture', '-i', str(screenshot_path)])
        
        time.sleep(1)
        
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
            
    def run_test_with_keyboard(self):
        """Alternative approach using keyboard navigation"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = self.screenshot_dir / f"test_keyboard_{timestamp}.png"
        
        # Build
        print("🔨 Building Chonker3...")
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Build failed: {result.stderr}")
            return None
            
        # Start the app
        print("🚀 Starting Chonker3...")
        process = subprocess.Popen(
            ["./target/release/chonker3"],
            cwd=self.project_dir
        )
        
        # Wait for window
        if not self.wait_for_window():
            process.terminate()
            return None
            
        # Try keyboard navigation approach
        keyboard_script = f'''
        tell application "System Events"
            tell process "chonker3"
                set frontmost to true
                delay 1
                
                -- Try to click Open button with different methods
                try
                    click button "Open" of window 1
                on error
                    -- If direct click fails, try keyboard navigation
                    repeat 10 times
                        key code 48 -- Tab
                        delay 0.1
                    end repeat
                    key code 49 -- Space to "click"
                end try
                
                delay 2
                
                -- In file dialog, paste path
                keystroke "g" using {{shift down, command down}}
                delay 0.5
                keystroke "{self.pdf_path}"
                delay 0.5
                keystroke return
                delay 1
                keystroke return
                delay 3
                
                -- Try to click Extract
                try
                    click button "Extract" of window 1
                on error
                    repeat 5 times
                        key code 48 -- Tab
                        delay 0.1
                    end repeat
                    key code 49 -- Space
                end try
            end tell
        end tell
        '''
        
        print("🤖 Attempting keyboard automation...")
        result = subprocess.run(['osascript', '-e', keyboard_script], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Automation had issues: {result.stderr}")
            print("You may need to complete the steps manually")
            
        # Wait for extraction
        print("⏳ Waiting for extraction to complete...")
        time.sleep(8)
        
        # Take screenshot
        print("📸 Taking screenshot...")
        subprocess.run(['screencapture', '-w', str(screenshot_path)])
        print("Click on the Chonker3 window...")
        time.sleep(3)
        
        # Close
        process.terminate()
        process.wait()
        
        if screenshot_path.exists():
            print(f"✅ Screenshot saved: {screenshot_path}")
            subprocess.run(["open", str(screenshot_path)])
            return str(screenshot_path)
        return None

def main():
    import sys
    
    pdf_path = None
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    
    tester = RobustChonkerTest(pdf_path)
    
    # Check permissions first
    if not tester.check_accessibility_permissions():
        print("\n⚠️  Please fix accessibility permissions and try again")
        return
    
    print("\nChoose automation method:")
    print("1. Manual assist (recommended) - You control the UI")
    print("2. Keyboard automation - Tries to use keyboard shortcuts")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        result = tester.run_test_manual_assist()
    elif choice == "2":
        result = tester.run_test_with_keyboard()
    else:
        print("Exiting...")
        return
    
    if result:
        print(f"\n📁 Screenshots directory: {tester.screenshot_dir}")
        print("You can now analyze the screenshot and make improvements")

if __name__ == "__main__":
    main()
