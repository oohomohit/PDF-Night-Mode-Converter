import fitz  # PyMuPDF
import os
import sys
import argparse
from PIL import Image, ImageOps
import io

def convert_pdf_to_night_mode(input_path, output_path):
    try:
        # Check if input file exists
        if not os.path.exists(input_path):
            print(f"Error: Input file '{input_path}' not found.")
            return False
            
        # Open input document
        doc_in = fitz.open(input_path)
        # Create output document
        doc_out = fitz.open()
        
        # Process each page with reduced memory usage
        for page_no in range(len(doc_in)):
            # Get the page
            page = doc_in[page_no]
            
            # Render at slightly lower resolution to save memory
            matrix = fitz.Matrix(1.5, 1.5)  # Reduced from 2.0 to save memory
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Free up memory
            pix = None
            
            # Invert the image
            img_inverted = ImageOps.invert(img.convert("RGB"))
            
            # Free up memory
            img = None
            
            # Convert back to bytes
            img_bytes = io.BytesIO()
            img_inverted.save(img_bytes, format="PNG", optimize=True, quality=85)
            img_bytes.seek(0)
            
            # Create a new page with black background
            new_page = doc_out.new_page(width=page.rect.width, height=page.rect.height)
            shape = new_page.new_shape()
            shape.draw_rect(new_page.rect)
            shape.finish(fill=(0, 0, 0))
            shape.commit()
            
            # Add inverted image to page
            new_page.insert_image(new_page.rect, stream=img_bytes)
            
            # Free up memory
            img_inverted = None
            img_bytes = None
        
        # Save and close
        doc_out.save(output_path, garbage=4, deflate=True, clean=True)
        doc_out.close()
        doc_in.close()
        
        print(f"Night mode PDF saved as: {output_path}")
        return True
    except Exception as e:
        print(f"Error converting PDF: {e}")
        return False

def main():
    # Create command line argument parser
    parser = argparse.ArgumentParser(description='Convert a PDF to night mode (inverted colors).')
    parser.add_argument('input_pdf', help='Path to the input PDF file')
    parser.add_argument('-o', '--output', help='Path to save the night mode PDF (default: adds _night_mode suffix)')
    
    args = parser.parse_args()
    
    # If output path not specified, create one based on input filename
    if not args.output:
        input_base = os.path.splitext(args.input_pdf)[0]
        args.output = f"{input_base}_night_mode.pdf"
    
    print(f"Converting {args.input_pdf} to night mode...")
    convert_pdf_to_night_mode(args.input_pdf, args.output)

if __name__ == "__main__":
    main()
