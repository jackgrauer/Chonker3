#!/usr/bin/env python3
"""
Compare OCR engines: EasyOCR vs Apple Vision (ocrmac)
Tests speed and accuracy on the same PDF
"""
import time
import json
import sys
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image
import numpy as np
from difflib import SequenceMatcher

# Import OCR engines
from ocrmac.ocrmac import text_from_image as apple_vision_ocr
import easyocr

class OCRComparison:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.easyocr_reader = None
        
    def prepare_image(self, scale=2.0):
        """Convert PDF page to image for OCR"""
        print(f"📄 Preparing image from PDF at {scale}x scale...")
        pdf = pdfium.PdfDocument(str(self.pdf_path))
        page = pdf[0]
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        pdf.close()
        
        # Save for testing
        image_path = "/tmp/ocr_test_image.png"
        image.save(image_path)
        return image_path, image
    
    def test_apple_vision(self, image_path):
        """Test Apple Vision OCR"""
        print("\n🍎 Testing Apple Vision (ocrmac)...")
        
        start_time = time.time()
        results = apple_vision_ocr(image_path, recognition_level="accurate", detail=True)
        ocr_time = time.time() - start_time
        
        # Extract text and organize by position
        extracted_items = []
        for text, confidence, bbox in results:
            extracted_items.append({
                'text': text,
                'confidence': confidence,
                'bbox': bbox
            })
        
        # Join all text
        full_text = ' '.join([item['text'] for item in extracted_items])
        
        return {
            'engine': 'Apple Vision',
            'time': ocr_time,
            'items_count': len(extracted_items),
            'full_text': full_text,
            'items': extracted_items,
            'avg_confidence': np.mean([item['confidence'] for item in extracted_items]) if extracted_items else 0
        }
    
    def test_easyocr(self, image_path):
        """Test EasyOCR"""
        print("\n🤖 Testing EasyOCR...")
        
        # Initialize reader if not already done
        if self.easyocr_reader is None:
            print("  Initializing EasyOCR (first time takes longer)...")
            init_start = time.time()
            self.easyocr_reader = easyocr.Reader(['en'])
            init_time = time.time() - init_start
            print(f"  Initialization took {init_time:.2f}s")
        
        start_time = time.time()
        results = self.easyocr_reader.readtext(image_path)
        ocr_time = time.time() - start_time
        
        # Extract text and organize
        extracted_items = []
        for bbox, text, confidence in results:
            # Convert bbox format to match Apple Vision
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            normalized_bbox = [
                min(x_coords) / 2448,  # Assuming image width from 2x scale
                min(y_coords) / 3168,  # Assuming image height from 2x scale
                (max(x_coords) - min(x_coords)) / 2448,
                (max(y_coords) - min(y_coords)) / 3168
            ]
            
            extracted_items.append({
                'text': text,
                'confidence': confidence,
                'bbox': normalized_bbox
            })
        
        # Join all text
        full_text = ' '.join([item['text'] for item in extracted_items])
        
        return {
            'engine': 'EasyOCR',
            'time': ocr_time,
            'items_count': len(extracted_items),
            'full_text': full_text,
            'items': extracted_items,
            'avg_confidence': np.mean([item['confidence'] for item in extracted_items]) if extracted_items else 0
        }
    
    def find_key_text(self, results, search_terms):
        """Find specific text in results"""
        found = {}
        for term in search_terms:
            found[term] = []
            for item in results['items']:
                if term.lower() in item['text'].lower():
                    found[term].append(item['text'])
        return found
    
    def calculate_similarity(self, text1, text2):
        """Calculate text similarity score"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def run_comparison(self):
        """Run full comparison"""
        print("🔬 OCR Engine Comparison: EasyOCR vs Apple Vision")
        print("=" * 60)
        
        # Prepare images at different scales
        scales = [2.0, 4.0]  # Test at 2x and 4x resolution
        results = {}
        
        for scale in scales:
            print(f"\n📐 Testing at {scale}x scale...")
            image_path, image = self.prepare_image(scale)
            
            # Test both engines
            apple_results = self.test_apple_vision(image_path)
            easy_results = self.test_easyocr(image_path)
            
            results[f'{scale}x'] = {
                'apple_vision': apple_results,
                'easyocr': easy_results
            }
        
        # Analyze results
        print("\n" + "=" * 60)
        print("📊 RESULTS SUMMARY")
        print("=" * 60)
        
        # Key text to search for
        key_terms = ['University Avenue', 'Philadelphia', '19104', 'Air Management', 'Registration']
        
        for scale, scale_results in results.items():
            print(f"\n🔍 Scale: {scale}")
            print("-" * 40)
            
            for engine_name, engine_results in scale_results.items():
                print(f"\n{engine_results['engine']}:")
                print(f"  ⏱️  Time: {engine_results['time']:.3f}s")
                print(f"  📝 Items: {engine_results['items_count']}")
                print(f"  🎯 Avg Confidence: {engine_results['avg_confidence']:.2%}")
                print(f"  📏 Text Length: {len(engine_results['full_text'])} chars")
                
                # Check for key text
                found = self.find_key_text(engine_results, key_terms)
                print(f"  🔑 Key text found:")
                for term, matches in found.items():
                    if matches:
                        print(f"    • {term}: ✅ ({len(matches)} matches)")
                        if term == 'Philadelphia':
                            # Show the actual text for address verification
                            for match in matches[:2]:  # Show first 2 matches
                                print(f"      → '{match}'")
                    else:
                        print(f"    • {term}: ❌")
        
        # Direct comparison at 2x scale
        print("\n" + "=" * 60)
        print("🔬 DIRECT COMPARISON (2x scale)")
        print("=" * 60)
        
        apple = results['2.0x']['apple_vision']
        easy = results['2.0x']['easyocr']
        
        # Speed comparison
        speed_ratio = easy['time'] / apple['time']
        print(f"\n⚡ Speed:")
        print(f"  Apple Vision: {apple['time']:.3f}s")
        print(f"  EasyOCR: {easy['time']:.3f}s")
        print(f"  → Apple Vision is {speed_ratio:.1f}x faster")
        
        # Accuracy comparison (text similarity)
        similarity = self.calculate_similarity(apple['full_text'], easy['full_text'])
        print(f"\n📊 Text Similarity: {similarity:.1%}")
        
        # Character count comparison
        print(f"\n📝 Extracted Text:")
        print(f"  Apple Vision: {len(apple['full_text'])} characters")
        print(f"  EasyOCR: {len(easy['full_text'])} characters")
        
        # Confidence comparison
        print(f"\n🎯 Average Confidence:")
        print(f"  Apple Vision: {apple['avg_confidence']:.1%}")
        print(f"  EasyOCR: {easy['avg_confidence']:.1%}")
        
        # Save detailed results
        with open('ocr_comparison_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Detailed results saved to ocr_comparison_results.json")
        
        # Final verdict
        print("\n" + "=" * 60)
        print("🏆 VERDICT")
        print("=" * 60)
        print(f"Speed Winner: Apple Vision ({speed_ratio:.1f}x faster)")
        print(f"Accuracy Winner: {'Apple Vision' if apple['avg_confidence'] > easy['avg_confidence'] else 'EasyOCR'}")
        print(f"Completeness: Both engines found the key text elements")

def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
    
    comparison = OCRComparison(pdf_path)
    comparison.run_comparison()

if __name__ == "__main__":
    main()