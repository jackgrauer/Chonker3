#!/usr/bin/env python3
"""
Automated Development Loop for Chonker3
This script automates the process of:
1. Building and running the app
2. Loading a PDF and extracting content
3. Taking a screenshot
4. Sending to Claude for analysis
5. Getting and applying improvements
6. Repeating the cycle
"""

import subprocess
import time
import os
import sys
import json
import base64
from datetime import datetime
import requests
from pathlib import Path
import tempfile
import shutil

class ChonkerAutomation:
    def __init__(self, pdf_path=None):
        self.project_dir = Path("/Users/jack/chonker3-new")
        self.pdf_path = pdf_path or "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
        self.screenshot_dir = self.project_dir / "automation_screenshots"
        self.iteration_count = 0
        self.max_iterations = 5
        self.results_log = []
        
        # Create screenshot directory
        self.screenshot_dir.mkdir(exist_ok=True)
        
        # Claude API endpoint (using local completion)
        self.claude_api_url = "https://api.anthropic.com/v1/messages"
        
    def build_app(self):
        """Build the Rust application"""
        print("🔨 Building Chonker3...")
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Build failed: {result.stderr}")
            return False
        print("✅ Build successful")
        return True
    
    def run_test_cycle(self):
        """Run one complete test cycle"""
        self.iteration_count += 1
        print(f"\n🔄 Starting iteration {self.iteration_count}")
        
        # Build the app
        if not self.build_app():
            return False
        
        # Run the app and automate interaction
        screenshot_path = self.screenshot_dir / f"iteration_{self.iteration_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        print("🚀 Starting Chonker3...")
        process = subprocess.Popen(
            ["./target/release/chonker3"],
            cwd=self.project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
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
            
            -- Make chonker3 frontmost
            tell process "chonker3"
                set frontmost to true
                delay 0.5
                
                -- Click Open button
                click button "Open" of window 1
                delay 1
            end tell
        end tell
        
        -- Handle file dialog
        tell application "System Events"
            keystroke "g" using {{shift down, command down}}
            delay 0.5
            keystroke "{self.pdf_path}"
            delay 0.5
            keystroke return
            delay 0.5
            keystroke return
            delay 2
            
            -- Click Extract button
            tell process "chonker3"
                click button "Extract" of window 1
            end tell
            
            -- Wait for extraction to complete
            delay 8
        end tell
        '''
        
        print("🤖 Automating UI interaction...")
        result = subprocess.run(['osascript', '-e', applescript], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"⚠️  AppleScript warning: {result.stderr}")
        
        # Take screenshot of the window
        print("📸 Taking screenshot...")
        # First get the window ID
        window_id_script = 'tell app "chonker3" to id of window 1'
        try:
            window_id_result = subprocess.run(['osascript', '-e', window_id_script], 
                                            capture_output=True, text=True)
            if window_id_result.returncode == 0:
                window_id = window_id_result.stdout.strip()
                # Take screenshot of specific window
                subprocess.run(['screencapture', '-l', window_id, str(screenshot_path)])
            else:
                # Fallback to window capture
                subprocess.run(['screencapture', '-w', str(screenshot_path)])
                time.sleep(1)  # Give user time to click
        except:
            # Final fallback
            subprocess.run(['screencapture', '-i', str(screenshot_path)])
        
        time.sleep(1)
        
        # Kill chonker3
        print("🛑 Closing Chonker3...")
        process.terminate()
        process.wait()
        
        # Verify screenshot exists
        if not screenshot_path.exists():
            print("❌ Screenshot failed")
            return False
            
        print(f"✅ Screenshot saved: {screenshot_path}")
        return str(screenshot_path)
    
    def analyze_with_claude(self, screenshot_path):
        """Send screenshot to Claude for analysis"""
        print("🤔 Analyzing with Claude...")
        
        # Read and encode the screenshot
        with open(screenshot_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        # Prepare the prompt
        prompt = f"""You are analyzing a screenshot of the Chonker3 PDF extraction application.

This is iteration {self.iteration_count} of an automated development loop.

Please analyze the screenshot and provide:
1. What's working well in the current implementation
2. Specific issues or improvements needed (focus on visual rendering, text extraction quality, UI/UX)
3. Concrete code changes to implement (be specific about files and line numbers if possible)

The main source file is at src/main.rs. Focus on practical improvements that will make the extracted content more readable and accurate.

Important context:
- The left panel shows the original PDF
- The right panel shows the extracted and rendered content
- We want the extracted content to closely match the PDF layout
- Text should be properly positioned and styled
- Forms, tables, and special formatting should be preserved

Please provide your analysis in JSON format:
{{
  "working_well": ["list of things working well"],
  "issues": ["list of specific issues"],
  "improvements": [
    {{
      "description": "what to improve",
      "file": "which file to modify",
      "changes": "specific code changes to make"
    }}
  ],
  "overall_score": 0-10
}}

IMPORTANT: Your response must be ONLY the JSON object, no other text."""

        try:
            # Make API call to Claude
            response = requests.post(
                self.claude_api_url,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 2000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_data
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Claude API error: {response.status_code} - {response.text}")
                return None
                
            # Parse response
            api_response = response.json()
            content = api_response.get("content", [{}])[0].get("text", "{}")
            
            # Try to parse JSON from the response
            try:
                analysis = json.loads(content)
                return analysis
            except json.JSONDecodeError:
                print(f"❌ Failed to parse Claude's response as JSON: {content}")
                return None
                
        except Exception as e:
            print(f"❌ Error calling Claude API: {e}")
            return None
    
    def apply_improvements(self, analysis):
        """Apply the suggested improvements"""
        if not analysis or "improvements" not in analysis:
            return False
            
        print(f"📝 Applying {len(analysis['improvements'])} improvements...")
        
        for improvement in analysis["improvements"]:
            print(f"  - {improvement['description']}")
            
            # Here you would implement the actual code changes
            # For now, we'll just log them
            self.results_log.append({
                "iteration": self.iteration_count,
                "improvement": improvement,
                "timestamp": datetime.now().isoformat()
            })
        
        # Save improvements to a file for manual review
        improvements_file = self.project_dir / f"improvements_iteration_{self.iteration_count}.json"
        with open(improvements_file, "w") as f:
            json.dump(analysis, f, indent=2)
        
        print(f"💾 Improvements saved to: {improvements_file}")
        return True
    
    def run_automated_loop(self):
        """Run the complete automated development loop"""
        print("🚀 Starting Automated Development Loop for Chonker3")
        print(f"📄 Using PDF: {self.pdf_path}")
        print(f"🔄 Max iterations: {self.max_iterations}")
        
        # Check if API key is set
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("⚠️  Warning: ANTHROPIC_API_KEY not set. Claude analysis will be skipped.")
            print("Set it with: export ANTHROPIC_API_KEY=your-key-here")
        
        while self.iteration_count < self.max_iterations:
            # Run test cycle
            screenshot = self.run_test_cycle()
            if not screenshot:
                print("❌ Test cycle failed")
                break
            
            # Analyze with Claude (if API key is available)
            if os.environ.get("ANTHROPIC_API_KEY"):
                analysis = self.analyze_with_claude(screenshot)
                if analysis:
                    print(f"📊 Overall score: {analysis.get('overall_score', 'N/A')}/10")
                    
                    # Log results
                    self.results_log.append({
                        "iteration": self.iteration_count,
                        "screenshot": screenshot,
                        "analysis": analysis,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Check if we've reached a good score
                    if analysis.get("overall_score", 0) >= 9:
                        print("🎉 Achieved high quality score! Stopping iterations.")
                        break
                    
                    # Apply improvements
                    self.apply_improvements(analysis)
                else:
                    print("⚠️  Skipping improvements due to analysis failure")
            else:
                print("⏭️  Skipping Claude analysis (no API key)")
            
            # Wait before next iteration
            if self.iteration_count < self.max_iterations:
                print(f"⏳ Waiting 5 seconds before next iteration...")
                time.sleep(5)
        
        # Save final results
        self.save_results()
        print("✅ Automation complete!")
    
    def save_results(self):
        """Save all results to a summary file"""
        summary_file = self.project_dir / f"automation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, "w") as f:
            json.dump({
                "total_iterations": self.iteration_count,
                "pdf_path": str(self.pdf_path),
                "results": self.results_log
            }, f, indent=2)
        print(f"📊 Summary saved to: {summary_file}")
        
        # Open the screenshots directory
        subprocess.run(["open", str(self.screenshot_dir)])

def main():
    # Parse command line arguments
    pdf_path = None
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        if not os.path.exists(pdf_path):
            print(f"❌ PDF file not found: {pdf_path}")
            sys.exit(1)
    
    # Create and run automation
    automation = ChonkerAutomation(pdf_path)
    
    try:
        automation.run_automated_loop()
    except KeyboardInterrupt:
        print("\n⚠️  Automation interrupted by user")
    except Exception as e:
        print(f"❌ Automation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
