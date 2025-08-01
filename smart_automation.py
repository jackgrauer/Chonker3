#!/usr/bin/env python3
"""
Advanced automation with code modification capabilities
This script can automatically apply code changes suggested by Claude
"""

import subprocess
import time
import os
import json
import re
from pathlib import Path
from datetime import datetime
import difflib

class CodeModifier:
    """Handles automatic code modifications based on Claude's suggestions"""
    
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.backup_dir = self.project_dir / "code_backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    def backup_file(self, file_path):
        """Create a backup of a file before modifying it"""
        file_path = Path(file_path)
        if not file_path.exists():
            return None
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"{file_path.name}.{timestamp}.bak"
        
        import shutil
        shutil.copy2(file_path, backup_path)
        return backup_path
        
    def apply_code_change(self, file_path, change_description):
        """Apply a code change based on description"""
        file_path = self.project_dir / file_path
        
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return False
            
        # Backup the file first
        backup = self.backup_file(file_path)
        if backup:
            print(f"📦 Backed up to: {backup.name}")
            
        # Read current content
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Parse change description for patterns
        # Look for patterns like "change X to Y" or "replace X with Y"
        modified = False
        
        # Pattern 1: Replace exact matches
        replace_pattern = r"replace\s+['\"`](.+?)['\"`]\s+with\s+['\"`](.+?)['\"`]"
        matches = re.findall(replace_pattern, change_description, re.IGNORECASE | re.DOTALL)
        for old_text, new_text in matches:
            if old_text in content:
                content = content.replace(old_text, new_text)
                modified = True
                print(f"✅ Replaced '{old_text[:50]}...' with '{new_text[:50]}...'")
                
        # Pattern 2: Change function/variable names
        rename_pattern = r"rename\s+(\w+)\s+to\s+(\w+)"
        matches = re.findall(rename_pattern, change_description, re.IGNORECASE)
        for old_name, new_name in matches:
            # Use word boundaries to avoid partial replacements
            pattern = r'\b' + re.escape(old_name) + r'\b'
            if re.search(pattern, content):
                content = re.sub(pattern, new_name, content)
                modified = True
                print(f"✅ Renamed {old_name} to {new_name}")
                
        # Pattern 3: Add code at specific locations
        add_pattern = r"add\s+['\"`](.+?)['\"`]\s+after\s+['\"`](.+?)['\"`]"
        matches = re.findall(add_pattern, change_description, re.IGNORECASE | re.DOTALL)
        for new_code, location in matches:
            if location in content:
                content = content.replace(location, location + "\n" + new_code)
                modified = True
                print(f"✅ Added code after '{location[:50]}...'")
                
        # Pattern 4: Modify specific values
        value_pattern = r"change\s+(\w+)\s*=\s*(.+?)\s+to\s+(.+?)(?:\s|$)"
        matches = re.findall(value_pattern, change_description, re.IGNORECASE)
        for var_name, old_value, new_value in matches:
            pattern = f"{var_name}\\s*=\\s*{re.escape(old_value)}"
            replacement = f"{var_name} = {new_value}"
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                modified = True
                print(f"✅ Changed {var_name} from {old_value} to {new_value}")
        
        if modified:
            # Write modified content
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"💾 Modified: {file_path}")
            return True
        else:
            print(f"⚠️  No changes applied to: {file_path}")
            return False
            
    def show_diff(self, file_path, original_content, modified_content):
        """Show a diff of the changes"""
        diff = difflib.unified_diff(
            original_content.splitlines(keepends=True),
            modified_content.splitlines(keepends=True),
            fromfile=f"{file_path} (original)",
            tofile=f"{file_path} (modified)"
        )
        print("📝 Changes:")
        print(''.join(diff))

class SmartChonkerAutomation:
    """Enhanced automation that can apply code changes"""
    
    def __init__(self, pdf_path=None):
        self.project_dir = Path("/Users/jack/chonker3-new")
        self.pdf_path = pdf_path or "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
        self.screenshot_dir = self.project_dir / "smart_automation"
        self.screenshot_dir.mkdir(exist_ok=True)
        self.code_modifier = CodeModifier(self.project_dir)
        self.iteration = 0
        
    def run_test_and_capture(self):
        """Run test and capture screenshot"""
        self.iteration += 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = self.screenshot_dir / f"iteration_{self.iteration}_{timestamp}.png"
        
        # Build
        print(f"\n🔄 Iteration {self.iteration}")
        print("🔨 Building...")
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Build failed: {result.stderr}")
            return None
            
        # Run and automate
        print("🚀 Running Chonker3...")
        process = subprocess.Popen(
            ["./target/release/chonker3"],
            cwd=self.project_dir
        )
        
        time.sleep(3)
        
        # Automate interaction
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
        
        subprocess.run(['osascript', '-e', applescript], capture_output=True)
        
        # Screenshot
        print("📸 Capturing screenshot...")
        subprocess.run(['screencapture', '-w', str(screenshot_path)])
        time.sleep(2)
        
        process.terminate()
        process.wait()
        
        if screenshot_path.exists():
            print(f"✅ Screenshot saved: {screenshot_path}")
            return screenshot_path
        return None
        
    def create_analysis_prompt(self, screenshot_path):
        """Create a prompt for manual analysis"""
        prompt_file = self.screenshot_dir / f"analyze_iteration_{self.iteration}.txt"
        
        prompt = f"""Please analyze the screenshot: {screenshot_path.name}

The screenshot shows Chonker3, a PDF extraction application.
- Left panel: Original PDF
- Right panel: Extracted and rendered content

Please provide specific code changes in this format:

For src/main.rs:
1. Replace "old code" with "new code"
2. Change variable_name = old_value to new_value
3. Add "new code" after "existing code"

Focus on:
- Text positioning accuracy
- Font sizes and styles
- Layout preservation
- Form field rendering
- Table structure

Be very specific with exact code snippets that can be automatically applied.
"""
        
        with open(prompt_file, 'w') as f:
            f.write(prompt)
            
        print(f"📝 Analysis prompt saved to: {prompt_file}")
        return prompt_file
        
    def apply_manual_changes(self, changes_file):
        """Apply changes from a manual analysis file"""
        if not changes_file.exists():
            print(f"❌ Changes file not found: {changes_file}")
            return False
            
        with open(changes_file, 'r') as f:
            content = f.read()
            
        # Parse file paths and changes
        current_file = None
        for line in content.split('\n'):
            # Check for file specification
            if line.strip().startswith("For ") and line.strip().endswith(":"):
                current_file = line.strip()[4:-1]
                continue
                
            # Apply changes for current file
            if current_file and line.strip():
                if line.strip()[0].isdigit() and '. ' in line:
                    # Extract the change description
                    change = line.split('. ', 1)[1] if '. ' in line else line
                    self.code_modifier.apply_code_change(current_file, change)
                    
        return True
        
    def run_interactive_loop(self, max_iterations=5):
        """Run an interactive improvement loop"""
        print("🚀 Starting Interactive Chonker3 Improvement Loop")
        print(f"📄 PDF: {self.pdf_path}")
        
        for i in range(max_iterations):
            # Run test
            screenshot = self.run_test_and_capture()
            if not screenshot:
                print("❌ Test failed")
                continue
                
            # Create analysis prompt
            prompt_file = self.create_analysis_prompt(screenshot)
            
            # Open screenshot and prompt for manual analysis
            subprocess.run(["open", str(screenshot)])
            subprocess.run(["open", str(prompt_file)])
            
            # Wait for user to create changes file
            changes_file = self.screenshot_dir / f"changes_iteration_{self.iteration}.txt"
            print(f"\n⏳ Waiting for changes file: {changes_file}")
            print("Create this file with specific code changes and press Enter to continue...")
            input()
            
            # Apply changes if file exists
            if changes_file.exists():
                print("📝 Applying changes...")
                self.apply_manual_changes(changes_file)
            else:
                print("⏭️  No changes file found, continuing...")
                
            if i < max_iterations - 1:
                print("\n🔄 Ready for next iteration? Press Enter to continue or Ctrl+C to stop...")
                input()
                
        print("\n✅ Improvement loop complete!")
        subprocess.run(["open", str(self.screenshot_dir)])

def main():
    import sys
    
    pdf_path = None
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        
    automation = SmartChonkerAutomation(pdf_path)
    
    try:
        automation.run_interactive_loop()
    except KeyboardInterrupt:
        print("\n⚠️  Stopped by user")

if __name__ == "__main__":
    main()
