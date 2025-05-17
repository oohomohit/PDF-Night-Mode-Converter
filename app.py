import os
import uuid
import tempfile
import sys
import traceback
import logging
import time
import json
from flask import Flask, request, render_template, send_file, redirect, url_for, jsonify, session
from werkzeug.utils import secure_filename
from pdf_night_mode import convert_pdf_to_night_mode, process_pdf_in_chunks

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Configure max content length for serverless mode
MAX_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB chunks
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload size in normal mode
SERVERLESS_MODE = os.environ.get('VERCEL_ENV') is not None  # Detect if running on Vercel

# Set content length based on environment
if SERVERLESS_MODE:
    app.config['MAX_CONTENT_LENGTH'] = MAX_CHUNK_SIZE  # Smaller limit for serverless
    app.logger.info(f"Running in serverless mode with {MAX_CHUNK_SIZE/1024/1024}MB limit")
else:
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH  # Larger limit for regular hosting
    app.logger.info(f"Running in normal mode with {MAX_CONTENT_LENGTH/1024/1024}MB limit")

# Create upload and result directories if not in serverless mode
if not SERVERLESS_MODE:
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('results', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        try:
            app.logger.info("POST request received to /")
            
            # Check if the post request has the file part
            if 'file' not in request.files:
                app.logger.warning("No file part in request")
                return render_template('index.html', error='No file part')
            
            file = request.files['file']
            
            # If user does not select file, browser submits an empty file
            if file.filename == '':
                app.logger.warning("No file selected")
                return render_template('index.html', error='No file selected')
            
            app.logger.info(f"File received: {file.filename}")
            
            if file and allowed_file(file.filename):
                # Generate unique filename to avoid collisions
                original_filename = secure_filename(file.filename)
                unique_id = str(uuid.uuid4())
                
                if SERVERLESS_MODE:
                    # In serverless mode, use tempfile for processing
                    try:
                        # Create temporary directory
                        temp_dir = tempfile.mkdtemp(prefix="pdf_night_")
                        app.logger.info(f"Created temp directory: {temp_dir}")
                        
                        # Save uploaded file
                        input_path = os.path.join(temp_dir, original_filename)
                        file.save(input_path)
                        app.logger.info(f"Saved input file to {input_path}")
                        
                        # Check file size to determine processing method
                        file_size = os.path.getsize(input_path)
                        app.logger.info(f"File size: {file_size} bytes")
                        
                        if file_size <= MAX_CHUNK_SIZE:
                            # For small files, process directly
                            app.logger.info("Processing small file directly")
                            output_filename = f"night_mode_{original_filename}"
                            output_path = os.path.join(temp_dir, output_filename)
                            
                            success = convert_pdf_to_night_mode(input_path, output_path)
                            
                            if success:
                                app.logger.info(f"PDF conversion successful: {output_path}")
                                
                                # Check output file size
                                output_size = os.path.getsize(output_path)
                                if output_size > MAX_CHUNK_SIZE:
                                    return render_template('index.html', 
                                                      error='Converted PDF is too large for serverless response. Please try a smaller document.')
                                
                                # Serve the file
                                return send_file(
                                    output_path,
                                    as_attachment=True,
                                    download_name=output_filename
                                )
                            else:
                                return render_template('index.html', error='Error processing PDF. Conversion failed.')
                        else:
                            # For large files, process in chunks
                            app.logger.info("File too large for direct processing, redirecting to chunked processing")
                            # Store the file path in the session
                            session['pdf_path'] = input_path
                            session['temp_dir'] = temp_dir
                            session['original_filename'] = original_filename
                            
                            # Redirect to chunked processing route
                            return redirect(url_for('process_chunks'))
                    
                    except Exception as e:
                        app.logger.error(f"Processing error: {str(e)}")
                        app.logger.error(traceback.format_exc())
                        return render_template('index.html', error=f'Processing error: {str(e)}')
                
                else:
                    # In normal mode, use regular directories
                    filename = f"{unique_id}_{original_filename}"
                    input_path = os.path.join('uploads', filename)
                    file.save(input_path)
                    
                    # Generate output filename
                    output_filename = f"night_mode_{original_filename}"
                    output_path = os.path.join('results', output_filename)
                    
                    # Process the file
                    success = convert_pdf_to_night_mode(input_path, output_path)
                    
                    if success:
                        # Serve the file
                        return send_file(
                            output_path,
                            as_attachment=True,
                            download_name=output_filename
                        )
                    else:
                        return render_template('index.html', error='Error processing PDF')
            else:
                app.logger.warning(f"Invalid file type: {file.filename}")
                return render_template('index.html', error='Invalid file type. Only PDF files are allowed.')
        
        except Exception as e:
            app.logger.error(f"Unhandled exception: {str(e)}")
            app.logger.error(traceback.format_exc())
            return render_template('index.html', error=f'Server error: {str(e)}')
    
    # If GET request or any other case
    chunk_limit = MAX_CHUNK_SIZE if SERVERLESS_MODE else MAX_CONTENT_LENGTH
    return render_template('index.html', serverless_mode=SERVERLESS_MODE, size_limit=chunk_limit)

@app.route('/process-chunks', methods=['GET'])
def process_chunks():
    try:
        # Get stored file path from session
        input_path = session.get('pdf_path')
        temp_dir = session.get('temp_dir')
        original_filename = session.get('original_filename')
        
        if not input_path or not os.path.exists(input_path):
            app.logger.error("No valid PDF path in session")
            return render_template('index.html', error='Session expired or invalid. Please upload again.')
        
        # Calculate total pages and chunks
        import fitz
        doc = fitz.open(input_path)
        total_pages = len(doc)
        doc.close()
        
        # Create a processing ID
        process_id = str(uuid.uuid4())
        
        # Store process info in session
        session['process_id'] = process_id
        session['total_pages'] = total_pages
        
        return render_template('chunks.html', 
                               total_pages=total_pages, 
                               process_id=process_id,
                               filename=original_filename)
        
    except Exception as e:
        app.logger.error(f"Error in process_chunks: {str(e)}")
        app.logger.error(traceback.format_exc())
        return render_template('index.html', error=f'Error preparing chunks: {str(e)}')

@app.route('/api/process-chunk', methods=['POST'])
def api_process_chunk():
    try:
        # Get chunk information from request
        data = request.json
        start_page = int(data.get('start_page', 0))
        end_page = int(data.get('end_page', 0))
        
        # Validate chunk range
        if start_page < 0 or end_page <= start_page:
            return jsonify({'success': False, 'error': 'Invalid page range'})
        
        # Get file path from session
        input_path = session.get('pdf_path')
        temp_dir = session.get('temp_dir')
        
        if not input_path or not os.path.exists(input_path):
            return jsonify({'success': False, 'error': 'Session expired or invalid'})
        
        # Generate chunk output path
        chunk_name = f"chunk_{start_page}_{end_page}.pdf"
        chunk_path = os.path.join(temp_dir, chunk_name)
        
        # Process the chunk
        success = process_pdf_in_chunks(input_path, chunk_path, start_page, end_page)
        
        if success:
            return jsonify({
                'success': True, 
                'chunk_id': f"{start_page}_{end_page}",
                'message': f"Pages {start_page+1}-{end_page} processed successfully"
            })
        else:
            return jsonify({'success': False, 'error': 'Processing failed'})
            
    except Exception as e:
        app.logger.error(f"Error processing chunk: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/combine-chunks', methods=['POST'])
def api_combine_chunks():
    try:
        # Get information from session
        temp_dir = session.get('temp_dir')
        original_filename = session.get('original_filename')
        
        if not temp_dir or not os.path.exists(temp_dir):
            return jsonify({'success': False, 'error': 'Session expired or invalid'})
        
        # Get chunk info from request
        data = request.json
        chunks = data.get('chunks', [])
        
        if not chunks:
            return jsonify({'success': False, 'error': 'No chunks to combine'})
        
        # Sort chunks by start page
        chunks.sort(key=lambda x: int(x.split('_')[0]))
        
        # Combine chunks
        import fitz
        result_doc = fitz.open()
        
        for chunk_id in chunks:
            start_page, end_page = map(int, chunk_id.split('_'))
            chunk_path = os.path.join(temp_dir, f"chunk_{start_page}_{end_page}.pdf")
            
            if os.path.exists(chunk_path):
                chunk_doc = fitz.open(chunk_path)
                result_doc.insert_pdf(chunk_doc)
                chunk_doc.close()
        
        # Save combined result
        result_filename = f"night_mode_{original_filename}"
        result_path = os.path.join(temp_dir, result_filename)
        result_doc.save(result_path, garbage=4, deflate=True, clean=True)
        result_doc.close()
        
        # Store result path in session
        session['result_path'] = result_path
        session['result_filename'] = result_filename
        
        return jsonify({'success': True, 'redirect': url_for('download_result')})
        
    except Exception as e:
        app.logger.error(f"Error combining chunks: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download-result')
def download_result():
    try:
        # Get result info from session
        result_path = session.get('result_path')
        result_filename = session.get('result_filename')
        
        if not result_path or not os.path.exists(result_path):
            return render_template('index.html', error='Result not found or session expired')
        
        # Serve the file
        return send_file(
            result_path,
            as_attachment=True,
            download_name=result_filename
        )
        
    except Exception as e:
        app.logger.error(f"Error in download_result: {str(e)}")
        app.logger.error(traceback.format_exc())
        return render_template('index.html', error=f'Error downloading result: {str(e)}')

# Health check endpoint with system info
@app.route('/health')
def health_check():
    try:
        system_info = {
            "status": "ok",
            "python_version": sys.version,
            "platform": sys.platform,
            "temp_dir": tempfile.gettempdir(),
            "serverless_mode": SERVERLESS_MODE,
            "max_content_length": app.config['MAX_CONTENT_LENGTH'],
            "env": {k: v for k, v in os.environ.items() if k.startswith(('PYTHON', 'FLASK', 'VERCEL'))}
        }
        return jsonify(system_info)
    except Exception as e:
        app.logger.error(f"Health check error: {str(e)}")
        return {"status": "error", "message": str(e)}, 500

# Cleanup temporary files when the app is shutting down
@app.teardown_appcontext
def cleanup_temp_files(exception):
    if SERVERLESS_MODE:
        # In serverless mode, no need for manual cleanup
        pass
    else:
        # In normal mode, periodically clean up old files
        try:
            # Clean files older than 1 hour
            current_time = time.time()
            for folder in ['uploads', 'results']:
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    # If file is older than 1 hour, delete it
                    if os.path.isfile(filepath) and os.path.getmtime(filepath) < current_time - 3600:
                        os.remove(filepath)
        except Exception as e:
            app.logger.warning(f"Error during cleanup: {str(e)}")

if __name__ == '__main__':
    # Run directly 
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 