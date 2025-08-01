#!/usr/bin/env python3
"""
Chonker3 Test Automation - Working Version
This uses a combination of approaches to handle egui apps
"""

import subprocess
import time
import os
from pathlib import Path
from datetime import datetime
import sys
import signal

class ChonkerTestRunner:
    def __init__(self, pdf_path=None):
        self.project_dir = Path("/Users/jack/chonker3-new")
        self.pdf_path = pdf_path or "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
        self.results_dir = self.project_dir / "test_results"
        self.results_dir.mkdir(exist_ok=True)
        self.process = None
        
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
            print(f"❌ Build failed: {result.stderr}")
            return False
        print("✅ Build successful")
        return True
        
    def run_direct_extraction(self):
        """Run the Python extractor directly for comparison"""
        print("\n📊 Running direct extraction for comparison...")
        
        # Check if extractor exists
        extractors = [
            "pypdfium2_proper_extractor.py",
            "simple_extractor_fixed.py",
            "simple_extractor.py"
        ]
        
        extractor_path = None
        for extractor in extractors:
            path = self.project_dir / extractor
            if path.exists():
                extractor_path = path
                break
                
        if not extractor_path:
            print("❌ No extractor script found")
            return None
            
        # Run extraction
        result = subprocess.run(
            [sys.executable, str(extractor_path), str(self.pdf_path)],
            capture_output=True,
            text=True,
            cwd=self.project_dir
        )
        
        if result.returncode == 0:
            print("✅ Direct extraction successful")
            # Parse output for JSON path
            for line in result.stdout.split('\n'):
                if 'json_path' in line and '.json' in line:
                    import re
                    match = re.search(r'["\']([^"\']*\.json)["\']', line)
                    if match:
                        json_path = match.group(1)
                        print(f"📄 JSON saved to: {json_path}")
                        return json_path
        else:
            print(f"❌ Direct extraction failed: {result.stderr}")
            
        return None
        
    def run_manual_test(self):
        """Run app with manual interaction"""
        if not self.build_app():
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_base = self.results_dir / f"manual_test_{timestamp}"
        
        print("\n🚀 Starting Chonker3...")
        print("=" * 60)
        print("MANUAL TEST MODE")
        print("=" * 60)
        
        # Start the app
        self.process = subprocess.Popen(
            ["./target/release/chonker3"],
            cwd=self.project_dir
        )
        
        print("\n📋 Please perform these steps manually:")
        print(f"1. Click 'Open' and select: {self.pdf_path}")
        print("2. Click 'Extract' and wait for completion")
        print("3. Try different features (zoom, search, etc.)")
        print("\n🔧 Commands while app is running:")
        print("  s - Take a screenshot")
        print("  a - Run analysis on current state")
        print("  q - Quit and close app")
        print("  h - Show this help again")
        print("\n")
        
        screenshot_count = 0
        
        try:
            while True:
                command = input("Command (s/a/q/h): ").strip().lower()
                
                if command == 'q':
                    break
                elif command == 's':
                    screenshot_count += 1
                    screenshot_path = f"{screenshot_base}_shot{screenshot_count}.png"
                    print("📸 Taking screenshot in 2 seconds...")
                    time.sleep(2)
                    
                    # Try multiple screenshot methods
                    if self._take_screenshot(screenshot_path):
                        print(f"✅ Screenshot saved: {screenshot_path}")
                        subprocess.run(["open", screenshot_path])
                    else:
                        print("❌ Screenshot failed")
                        
                elif command == 'a':
                    print("🔍 Running analysis...")
                    self._analyze_current_state()
                    
                elif command == 'h':
                    print("\n🔧 Commands:")
                    print("  s - Take a screenshot")
                    print("  a - Run analysis on current state")
                    print("  q - Quit and close app")
                    
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted")
        finally:
            self._cleanup()
            
    def _take_screenshot(self, output_path):
        """Try various methods to take a screenshot"""
        methods = [
            # Method 1: Window capture with mouse click
            lambda: subprocess.run(['screencapture', '-w', output_path]).returncode == 0,
            
            # Method 2: Interactive selection
            lambda: subprocess.run(['screencapture', '-i', output_path]).returncode == 0,
            
            # Method 3: Full screen after delay
            lambda: subprocess.run(['screencapture', '-T', '2', output_path]).returncode == 0,
        ]
        
        for i, method in enumerate(methods, 1):
            if i == 1:
                print("Click on the Chonker3 window...")
            elif i == 2:
                print("Click and drag to select the area...")
            elif i == 3:
                print("Taking full screen shot...")
                
            if method() and Path(output_path).exists():
                return True
                
        return False
        
    def _analyze_current_state(self):
        """Analyze the current state of the app"""
        # Look for the most recent JSON output
        temp_dir = Path("/var/folders")
        json_files = []
        
        # Search for recent JSON files
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith("_chonker3.json") and file.startswith("tmp"):
                    full_path = Path(root) / file
                    if full_path.exists():
                        # Check if recent (within last hour)
                        mtime = full_path.stat().st_mtime
                        if time.time() - mtime < 3600:
                            json_files.append((mtime, full_path))
                            
        if json_files:
            # Get most recent
            json_files.sort(reverse=True)
            latest_json = json_files[0][1]
            print(f"📄 Found recent extraction: {latest_json}")
            
            # Run JSON analysis
            analyzer_script = self.project_dir / "json_analysis.py"
            if analyzer_script.exists():
                subprocess.run([sys.executable, str(analyzer_script), str(self.pdf_path)])
            else:
                print("❌ JSON analyzer not found")
        else:
            print("❌ No recent extraction JSON found")
            
    def _cleanup(self):
        """Clean up the running process"""
        if self.process:
            print("\n🛑 Closing Chonker3...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing process...")
                self.process.kill()
                
    def run_automated_sequence(self):
        """Run a semi-automated test sequence"""
        if not self.build_app():
            return
            
        print("\n🤖 Semi-Automated Test Sequence")
        print("This will guide you through a standard test")
        
        # First do direct extraction
        json_path = self.run_direct_extraction()
        
        # Start the app
        print("\n🚀 Starting Chonker3...")
        self.process = subprocess.Popen(
            ["./target/release/chonker3"],
            cwd=self.project_dir
        )
        
        time.sleep(3)
        
        steps = [
            ("Click the 'Open' button", 5),
            (f"Navigate to and select:\n   {self.pdf_path}", 10),
            ("Click the 'Extract' button", 3),
            ("Wait for extraction to complete", 8),
            ("Try zooming in/out with the zoom buttons", 5),
            ("Try searching with Cmd+F", 5),
            ("Navigate pages if multi-page", 5),
        ]
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            for i, (instruction, wait_time) in enumerate(steps, 1):
                print(f"\n📋 Step {i}: {instruction}")
                print(f"⏰ You have {wait_time} seconds...")
                
                for j in range(wait_time, 0, -1):
                    print(f"\r⏳ {j} seconds remaining...", end='', flush=True)
                    time.sleep(1)
                print()
                
                # Take screenshot after certain steps
                if i in [4, 7]:  # After extraction and at end
                    screenshot_path = self.results_dir / f"auto_test_{timestamp}_step{i}.png"
                    print("📸 Taking screenshot...")
                    time.sleep(1)
                    if self._take_screenshot(str(screenshot_path)):
                        print(f"✅ Screenshot saved: {screenshot_path.name}")
                        
        except KeyboardInterrupt:
            print("\n⚠️  Test interrupted")
        finally:
            self._cleanup()
            
        print("\n✅ Test sequence complete!")
        print(f"📁 Results saved in: {self.results_dir}")
        subprocess.run(["open", str(self.results_dir)])

def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    runner = ChonkerTestRunner(pdf_path)
    
    print("🐹 Chonker3 Test Runner")
    print("\nSelect test mode:")
    print("1. Manual test with commands")
    print("2. Semi-automated sequence")
    print("3. Direct extraction only")
    print("4. Exit")
    
    choice = input("\nChoice (1-4): ").strip()
    
    if choice == '1':
        runner.run_manual_test()
    elif choice == '2':
        runner.run_automated_sequence()
    elif choice == '3':
        runner.run_direct_extraction()
    else:
        print("Exiting...")

if __name__ == "__main__":
    main()
