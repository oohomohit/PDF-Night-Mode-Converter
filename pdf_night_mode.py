import fitz  # PyMuPDF
import os
import sys
import argparse
import traceback
import logging
from PIL import Image, ImageOps
import io

# Configure logging
logger = logging.getLogger(__name__)

def convert_pdf_to_night_mode(input_path, output_path):
    try:
        # Check if input file exists
        if not os.path.exists(input_path):
            logger.error(f"Error: Input file '{input_path}' not found.")
            return False
        
        logger.info(f"Opening input PDF: {input_path}")
        # Get PDF info
        file_size = os.path.getsize(input_path)
        logger.info(f"Input PDF size: {file_size} bytes")
            
        # Open input document
        doc_in = fitz.open(input_path)
        logger.info(f"PDF opened. Pages: {len(doc_in)}")
        
        # Create output document
        doc_out = fitz.open()
        
        # Process each page with reduced memory usage and optimized for smaller file size
        for page_no in range(len(doc_in)):
            logger.info(f"Processing page {page_no+1}/{len(doc_in)}")
            
            try:
                # Get the page
                page = doc_in[page_no]
                
                # Adjust scale based on file size and page count to keep output small
                if len(doc_in) > 5:
                    scale = 0.8  # Very low resolution for multi-page docs
                elif file_size > 1 * 1024 * 1024:  # 1MB
                    scale = 1.0  # Low resolution for large files
                else:
                    scale = 1.2  # Medium resolution for small files
                    
                logger.info(f"Using scale factor: {scale}")
                
                # Render at a lower resolution to save memory and reduce output size
                matrix = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                
                # Convert to PIL Image - use a direct path to avoid memory issues
                img_path = f"{output_path}_temp_page_{page_no}.png"
                pix.save(img_path)
                logger.info(f"Saved temporary image: {img_path}")
                
                # Free up memory
                pix = None
                
                # Open saved image
                img = Image.open(img_path)
                
                # Invert the image
                img_inverted = ImageOps.invert(img.convert("RGB"))
                
                # Free up memory
                img.close()
                img = None
                
                # Save inverted image with high compression for serverless environment
                inverted_path = f"{output_path}_inverted_page_{page_no}.jpg"  # Use JPG for better compression
                img_inverted.save(inverted_path, format="JPEG", optimize=True, quality=70)  # Lower quality for smaller size
                
                # Free up memory
                img_inverted.close()
                img_inverted = None
                
                # Create a new page with black background
                new_page = doc_out.new_page(width=page.rect.width, height=page.rect.height)
                shape = new_page.new_shape()
                shape.draw_rect(new_page.rect)
                shape.finish(fill=(0, 0, 0))
                shape.commit()
                
                # Add inverted image to page
                new_page.insert_image(new_page.rect, filename=inverted_path)
                
                # Clean up temporary files
                try:
                    os.remove(img_path)
                    os.remove(inverted_path)
                except Exception as e:
                    logger.warning(f"Error removing temporary files: {e}")
                
            except Exception as page_error:
                logger.error(f"Error processing page {page_no+1}: {str(page_error)}")
                logger.error(traceback.format_exc())
                # Continue with next page
                continue
        
        # Check if we have any pages
        if doc_out.page_count == 0:
            logger.error("No pages were successfully processed")
            return False
        
        # Save with maximum compression options for serverless environment
        logger.info(f"Saving output PDF: {output_path}")
        doc_out.save(output_path, 
                     garbage=4,          # Maximum garbage collection
                     deflate=True,       # Use deflate compression
                     clean=True,         # Clean unused objects
                     linear=True,        # Optimize for web
                     pretty=False,       # No pretty printing
                     encryption=None)    # No encryption
        doc_out.close()
        doc_in.close()
        
        # Verify the output exists and has size
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            output_size = os.path.getsize(output_path)
            logger.info(f"PDF conversion complete. Output size: {output_size} bytes")
            return True
        else:
            logger.error(f"Output file does not exist or is empty: {output_path}")
            return False
            
    except Exception as e:
        logger.error(f"Error converting PDF: {e}")
        logger.error(traceback.format_exc())
        return False

def process_pdf_in_chunks(input_path, output_path, start_page, end_page):
    """
    Process a specific page range from a PDF and convert to night mode
    
    Args:
        input_path: Path to the input PDF file
        output_path: Path to save the output PDF file
        start_page: Starting page index (0-based)
        end_page: Ending page index (exclusive)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Processing chunk from page {start_page+1} to {end_page} of {input_path}")
        
        # Check if input file exists
        if not os.path.exists(input_path):
            logger.error(f"Error: Input file '{input_path}' not found.")
            return False
            
        # Open input document
        doc_in = fitz.open(input_path)
        total_pages = len(doc_in)
        
        # Validate page range
        if start_page < 0 or end_page > total_pages or start_page >= end_page:
            logger.error(f"Invalid page range: {start_page}-{end_page}, document has {total_pages} pages")
            return False
        
        # Create output document
        doc_out = fitz.open()
        
        # Process specified pages
        for page_idx in range(start_page, end_page):
            logger.info(f"Processing page {page_idx+1}")
            
            try:
                # Get the page
                page = doc_in[page_idx]
                
                # Use lower resolution for chunks to save memory
                scale = 0.8  # Lower resolution for chunked processing
                
                # Render page to image
                matrix = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                
                # Save to temporary file to avoid memory issues
                temp_img_path = f"{output_path}_temp_{page_idx}.jpg"
                pix.save(temp_img_path, "jpeg", quality=70)
                
                # Free memory
                pix = None
                
                # Open with PIL
                img = Image.open(temp_img_path)
                
                # Invert colors
                img_inverted = ImageOps.invert(img.convert("RGB"))
                
                # Free memory
                img.close()
                img = None
                
                # Save inverted image
                inverted_path = f"{output_path}_inverted_{page_idx}.jpg"
                img_inverted.save(inverted_path, format="JPEG", optimize=True, quality=70)
                
                # Free memory
                img_inverted.close()
                img_inverted = None
                
                # Create a new page with black background
                new_page = doc_out.new_page(width=page.rect.width, height=page.rect.height)
                shape = new_page.new_shape()
                shape.draw_rect(new_page.rect)
                shape.finish(fill=(0, 0, 0))
                shape.commit()
                
                # Add inverted image to page
                new_page.insert_image(new_page.rect, filename=inverted_path)
                
                # Clean up temporary files
                try:
                    os.remove(temp_img_path)
                    os.remove(inverted_path)
                except Exception as e:
                    logger.warning(f"Error removing temporary files: {e}")
                
            except Exception as page_error:
                logger.error(f"Error processing page {page_idx+1}: {str(page_error)}")
                logger.error(traceback.format_exc())
                # Continue with next page
                continue
        
        # Check if we have any pages
        if doc_out.page_count == 0:
            logger.error("No pages were successfully processed")
            return False
        
        # Save the chunk
        logger.info(f"Saving chunk to {output_path}")
        doc_out.save(output_path, 
                     garbage=4,
                     deflate=True,
                     clean=True,
                     linear=True)
        doc_out.close()
        doc_in.close()
        
        # Verify the output
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Chunk saved successfully: {output_path}, size: {os.path.getsize(output_path)} bytes")
            return True
        else:
            logger.error(f"Chunk output file does not exist or is empty")
            return False
        
    except Exception as e:
        logger.error(f"Error processing chunk: {e}")
        logger.error(traceback.format_exc())
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
