use std::process::Command;
use std::path::Path;
use anyhow::Result;

pub struct ExtractionResult {
    pub success: bool,
    pub json_path: String,
    pub items: usize,
    pub message: String,
}

pub fn extract_pdf(pdf_path: &Path) -> Result<ExtractionResult> {
    // Ensure we have absolute path
    let pdf_path = pdf_path.canonicalize().unwrap_or_else(|_| pdf_path.to_path_buf());
    // Python code that extracts PDF with image preprocessing
    let python_code = r#"
import sys
import json
import tempfile
import os

try:
    # Add current directory to path to use local scripts
    sys.path.insert(0, os.getcwd())
    
    # Get PDF path from command line
    pdf_path = sys.argv[1]
    
    # Try to use enhanced chonker2 with preprocessing first
    try:
        from enhanced_chonker2 import EnhancedChonker2
        use_enhanced = True
        print(f"DEBUG: Using Enhanced Docling extractor with preprocessing", file=sys.stderr)
    except ImportError as e1:
        # Try regular chonker2
        try:
            from chonker2 import Chonker2
            use_enhanced = False
            use_docling = True
            print(f"DEBUG: Using regular Docling extractor", file=sys.stderr)
        except ImportError as e2:
            # Fall back to simple extractor
            print(f"DEBUG: Docling import failed: {e2}", file=sys.stderr)
            from simple_extractor import extract_pdf_with_fonts
            use_enhanced = False
            use_docling = False
            print(f"DEBUG: Using simple extractor", file=sys.stderr)
    
    # TEMPORARY: Force simple extractor for testing
    if '--force-simple' in str(pdf_path):
        from simple_extractor import extract_pdf_with_fonts
        use_enhanced = False
        use_docling = False
        print(f"DEBUG: FORCED simple extractor", file=sys.stderr)
    
    # No preprocessing - use original PDF directly
    pdf_to_extract = pdf_path
    
    # Extract from PDF
    temp_json = tempfile.mktemp(suffix='_chonker3.json')
    
    if use_enhanced:
        # Use Enhanced Docling extractor with preprocessing
        extractor = EnhancedChonker2(verbose=False, preprocess=True)
        data = extractor.extract_to_json(pdf_to_extract, temp_json)
    elif use_docling:
        # Use regular Docling extractor
        extractor = Chonker2(verbose=False)
        data = extractor.extract_to_json(pdf_to_extract, temp_json)
    else:
        # Use simple pypdfium2 extractor
        data = extract_pdf_with_fonts(pdf_to_extract)
        with open(temp_json, 'w') as f:
            json.dump(data, f, indent=2)
    
    
    # Output results as JSON for Rust to parse
    result = {
        'success': True,
        'json_path': temp_json,
        'items': len(data.get('items', [])),
        'pages': len(data.get('pages', [])),
        'tables': len(data.get('tables', [])),
        'extractor_used': 'enhanced' if use_enhanced else ('docling' if use_docling else 'simple')
    }
    
    print(json.dumps(result))
except ImportError as e:
    if 'docling' in str(e).lower():
        print(json.dumps({
            'success': False,
            'error': 'Docling not installed. Please run: pip install docling'
        }))
    else:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))
except Exception as e:
    print(json.dumps({
        'success': False,
        'error': str(e)
    }))
"#;

    // IMPORTANT: Always use the chonker3 virtual environment's Python!
    // This venv has all required dependencies (docling, pypdfium2, etc.)
    // DO NOT use system python or create new venvs
    let venv_python = std::env::current_dir()
        .unwrap()
        .join(".venv")
        .join("bin")
        .join("python");
    
    // Run Python with our embedded code
    let output = Command::new(venv_python)
        .arg("-c")
        .arg(python_code)
        .arg(&pdf_path)
        .output()?;

    if output.status.success() {
        // Parse the JSON output from Python
        let stdout = String::from_utf8_lossy(&output.stdout);
        println!("Python output: {}", stdout); // Debug print
        
        let result: serde_json::Value = serde_json::from_str(&stdout)?;
        
        // Check if it's an error response
        if let Some(false) = result["success"].as_bool() {
            return Ok(ExtractionResult {
                success: false,
                json_path: String::new(),
                items: 0,
                message: result["error"].as_str().unwrap_or("Unknown error").to_string(),
            });
        }
        
        Ok(ExtractionResult {
            success: true,
            json_path: result["json_path"].as_str().unwrap_or("").to_string(),
            items: result["items"].as_u64().unwrap_or(0) as usize,
            message: format!("Extracted {} items from {} pages", 
                result["items"].as_u64().unwrap_or(0),
                result["pages"].as_u64().unwrap_or(0)),
        })
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        
        // Check if error was returned as JSON
        if let Ok(error_result) = serde_json::from_str::<serde_json::Value>(&stdout) {
            if let Some(error) = error_result.get("error").and_then(|v| v.as_str()) {
                return Ok(ExtractionResult {
                    success: false,
                    json_path: String::new(),
                    items: 0,
                    message: format!("Extraction failed: {}", error),
                });
            }
        }
        
        Ok(ExtractionResult {
            success: false,
            json_path: String::new(),
            items: 0,
            message: format!("Extraction failed: {} | {}", stderr, stdout),
        })
    }
}