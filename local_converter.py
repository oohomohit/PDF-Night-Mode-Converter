import os
import sys
import fitz  # PyMuPDF
from PIL import Image, ImageOps
import argparse
import io
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def process_page(page, output_prefix, page_no, quality=80, scale=1.5):
    """Process a single page to night mode"""
    print(f"Processing page {page_no+1}...")
    
    # Render at specified resolution
    matrix = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    
    # Convert to PIL Image 
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    # Free pixmap resources
    pix = None
    
    # Invert the image
    img_inverted = ImageOps.invert(img.convert("RGB"))
    
    # Close original image
    img.close()
    
    # Return the inverted image and page dimensions
    return img_inverted, page.rect.width, page.rect.height

def convert_to_night_mode(input_path, output_path, quality=90, scale=2.0, max_workers=4):
    """Convert a PDF to night mode using multithreading for speed"""
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found")
        return False
        
    # Get base filename for temp files
    temp_prefix = f"temp_{int(time.time())}"
    
    try:
        print(f"Opening PDF: {input_path}")
        print(f"This may take a while depending on the PDF size...")
        
        # Open the input document
        doc_in = fitz.open(input_path)
        total_pages = len(doc_in)
        print(f"PDF has {total_pages} pages")
        
        # Create output document
        doc_out = fitz.open()
        
        # Process pages in parallel
        completed = 0
        print("Starting parallel processing of pages with high quality settings...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_page, doc_in[page_no], temp_prefix, page_no, quality, scale): 
                page_no for page_no in range(total_pages)
            }
            
            # As each page completes, add it to the output PDF
            for i, future in enumerate(futures):
                # Get page info and inverted image
                try:
                    inverted_img, width, height = future.result()
                    page_no = futures[future]
                    
                    # Create a new page with black background
                    new_page = doc_out.new_page(width=width, height=height)
                    shape = new_page.new_shape()
                    shape.draw_rect(new_page.rect)
                    shape.finish(fill=(0, 0, 0))
                    shape.commit()
                    
                    # Save inverted image to temp file
                    temp_img_path = f"{temp_prefix}_{page_no}.jpg"
                    inverted_img.save(temp_img_path, format="JPEG", quality=quality)
                    
                    # Add inverted image to page
                    new_page.insert_image(new_page.rect, filename=temp_img_path)
                    
                    # Clean up
                    try:
                        os.remove(temp_img_path)
                    except Exception as e:
                        print(f"Warning: Could not remove temp file {temp_img_path}: {e}")
                    
                    # Free memory
                    inverted_img.close()
                    
                    # Progress indication
                    completed += 1
                    print(f"Completed: {completed}/{total_pages} pages ({(completed/total_pages*100):.1f}%)")
                    
                except Exception as e:
                    print(f"Error processing page {futures[future]+1}: {str(e)}")
        
        # Check if we have any pages
        if doc_out.page_count == 0:
            print("Error: No pages were successfully processed")
            return False
            
        # Save the output file
        print(f"Saving to {output_path}...")
        doc_out.save(output_path, garbage=4, deflate=True, clean=True)
        doc_out.close()
        doc_in.close()
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"Success! Night mode PDF saved to: {output_path}")
            return True
        else:
            print("Error: Output file was not created or is empty")
            return False
    
    except Exception as e:
        print(f"Error converting PDF: {e}")
        return False
    
    finally:
        # Clean up any remaining temp files
        for tmp_file in Path('.').glob(f"{temp_prefix}_*.jpg"):
            try:
                os.remove(tmp_file)
            except:
                pass

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert PDF to night mode (dark background with light text)')
    parser.add_argument('input_pdf', help='Path to the input PDF file')
    parser.add_argument('-o', '--output', help='Path to save the night mode PDF (default: adds _night_mode suffix)')
    parser.add_argument('-q', '--quality', type=int, default=90, help='Image quality (1-100, default: 90)')
    parser.add_argument('-s', '--scale', type=float, default=2.0, help='Resolution scale factor (default: 2.0)')
    parser.add_argument('-t', '--threads', type=int, default=4, help='Number of processing threads (default: 4)')
    
    args = parser.parse_args()
    
    # If output path not specified, create one based on input filename
    if not args.output:
        input_base = os.path.splitext(args.input_pdf)[0]
        args.output = f"{input_base}_night_mode.pdf"
    
    # Validate quality
    if args.quality < 1 or args.quality > 100:
        print("Quality must be between 1 and 100")
        return
    
    # Validate scale
    if args.scale <= 0:
        print("Scale must be greater than 0")
        return
        
    # Validate threads
    if args.threads < 1:
        print("Threads must be at least 1")
        return
    
    print("Converting with high quality settings: scale=%.1f, quality=%d, threads=%d" % 
          (args.scale, args.quality, args.threads))
        
    # Convert the PDF
    convert_to_night_mode(
        args.input_pdf, 
        args.output, 
        quality=args.quality, 
        scale=args.scale,
        max_workers=args.threads
    )

if __name__ == "__main__":
    main() 