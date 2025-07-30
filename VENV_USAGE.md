# Virtual Environment Usage

## IMPORTANT: Always use the .venv virtual environment!

This project has a virtual environment at `.venv/` that contains all necessary Python dependencies including:
- docling (for PDF extraction)
- pypdfium2 (for PDF rendering)
- pdf2image (for preprocessing)
- And many other dependencies

## How to use:

1. **For Python scripts**: Always use `.venv/bin/python` instead of just `python`
   ```bash
   .venv/bin/python script.py
   ```

2. **For pip**: Always use `.venv/bin/pip` instead of just `pip`
   ```bash
   .venv/bin/pip install package_name
   ```

3. **To activate the environment** (for interactive use):
   ```bash
   source .venv/bin/activate
   ```

## The code automatically uses this venv!

The Rust extractor module (`src/extractor.rs`) is already configured to use `.venv/bin/python` automatically when extracting PDFs.

## DO NOT:
- Create new virtual environments
- Use system Python
- Install packages globally

## To verify you're using the right environment:
```bash
which python  # Should show .venv/bin/python if activated
.venv/bin/python --version  # Should work and show Python version
```