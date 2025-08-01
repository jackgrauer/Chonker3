# Chonker3 Automation Tools

This directory contains automation scripts to help with the iterative development of Chonker3.

## Available Scripts

### 1. `simple_test_automation.py`
The simplest automation - builds, runs, loads a PDF, extracts, and takes a screenshot.

```bash
./simple_test_automation.py [optional_pdf_path]
```

Features:
- Automatic build and run
- UI automation with AppleScript
- Screenshot capture
- Opens screenshot for manual review

### 2. `smart_automation.py`
Interactive improvement loop with code modification capabilities.

```bash
./smart_automation.py [optional_pdf_path]
```

Features:
- Iterative testing loop
- Generates analysis prompts
- Can automatically apply code changes
- Supports patterns like:
  - Replace "old code" with "new code"
  - Change variable = old_value to new_value
  - Add "new code" after "existing code"
  - Rename function_name to new_name

Workflow:
1. Runs test and takes screenshot
2. Creates analysis prompt file
3. Wait for you to create a changes file
4. Automatically applies the changes
5. Repeats for next iteration

### 3. `automated_dev_loop.py`
Full automation with Claude AI integration.

```bash
export ANTHROPIC_API_KEY=your-key-here
./automated_dev_loop.py [optional_pdf_path]
```

Features:
- Fully automated iteration loop
- Sends screenshots to Claude for analysis
- Receives improvement suggestions in JSON
- Logs all iterations and scores
- Stops when quality score reaches 9/10

## Setup

1. Make scripts executable:
```bash
chmod +x *.py
# or run: bash make_executable.sh
```

2. For Claude automation, set your API key:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

3. Ensure you have required permissions:
- System Preferences > Security & Privacy > Privacy > Accessibility
- Add Terminal (or your terminal app) to allowed apps

## Default Test PDF

All scripts use this PDF by default:
```
/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf
```

You can specify a different PDF as a command-line argument.

## Output Directories

- `test_screenshots/` - Simple test screenshots
- `smart_automation/` - Interactive loop screenshots and changes
- `automation_screenshots/` - Full automation screenshots
- `code_backups/` - Automatic backups before code modifications

## Example Workflow

### Quick Test
```bash
./simple_test_automation.py
# Screenshot opens automatically for review
```

### Interactive Improvement
```bash
./smart_automation.py

# For each iteration:
# 1. Review the screenshot that opens
# 2. Create changes_iteration_N.txt with specific code changes
# 3. Press Enter to apply changes and continue
```

### Full Automation (with Claude)
```bash
export ANTHROPIC_API_KEY=your-key
./automated_dev_loop.py

# Runs up to 5 iterations automatically
# Stops early if quality score reaches 9/10
# Check automation_summary_*.json for results
```

## Troubleshooting

1. **AppleScript errors**: Make sure Accessibility permissions are granted
2. **Screenshot fails**: The app window must be visible
3. **Build errors**: Check that `cargo` is in PATH
4. **Claude API errors**: Verify your API key is correct

## Code Change Format

For `smart_automation.py`, create changes files like this:

```
For src/main.rs:
1. Replace "zoom_level: 0.86" with "zoom_level: 1.0"
2. Change TEAL = Color32::from_rgb(0x1A, 0xBC, 0x9C) to Color32::from_rgb(0x2E, 0xCC, 0x71)
3. Add "println!('Debug: {}'', self.status_message);" after "self.status_message = message;"

For src/renderer.rs:
1. Rename render_text to render_text_item
2. Change font_size = 12.0 to 14.0
```

The automation will parse and apply these changes automatically.
