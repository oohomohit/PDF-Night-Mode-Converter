import os
import uuid
import tempfile
import sys
import traceback
import logging
import time
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename
from pdf_night_mode import convert_pdf_to_night_mode

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# Configure max content length
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB max upload size
SERVERLESS_MODE = os.environ.get('VERCEL_ENV') is not None  # Detect if running on Vercel

# Set content length based on environment
if SERVERLESS_MODE:
    app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
    app.logger.info(f"Running in serverless mode with {MAX_FILE_SIZE/1024/1024}MB limit")
else:
    app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
    app.logger.info(f"Running in normal mode with {MAX_FILE_SIZE/1024/1024}MB limit")

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
                        
                        # Check file size
                        file_size = os.path.getsize(input_path)
                        app.logger.info(f"File size: {file_size} bytes")
                        
                        if file_size <= MAX_FILE_SIZE:
                            # Process the file
                            app.logger.info("Processing file")
                            output_filename = f"night_mode_{original_filename}"
                            output_path = os.path.join(temp_dir, output_filename)
                            
                            success = convert_pdf_to_night_mode(input_path, output_path)
                            
                            if success:
                                app.logger.info(f"PDF conversion successful: {output_path}")
                                
                                # Check output file size
                                output_size = os.path.getsize(output_path)
                                if output_size > MAX_FILE_SIZE:
                                    return render_template('index.html', 
                                                      error='Converted PDF is too large for download. Please try a smaller document.')
                                
                                # Serve the file
                                return send_file(
                                    output_path,
                                    as_attachment=True,
                                    download_name=output_filename
                                )
                            else:
                                return render_template('index.html', error='Error processing PDF. Conversion failed.')
                        else:
                            # For large files, suggest local processing
                            return render_template('index.html', 
                                     error='This file is too large for online processing. Please download the local converter.',
                                     show_download_local=True)
                    
                    except Exception as e:
                        app.logger.error(f"Processing error: {str(e)}")
                        app.logger.error(traceback.format_exc())
                        return render_template('index.html', error=f'Processing error: {str(e)}')
                
                else:
                    # In normal mode, use regular directories
                    filename = f"{unique_id}_{original_filename}"
                    input_path = os.path.join('uploads', filename)
                    file.save(input_path)
                    
                    # Check file size
                    file_size = os.path.getsize(input_path)
                    if file_size > MAX_FILE_SIZE:
                        return render_template('index.html', 
                                    error='This file is too large for online processing. Please download the local converter.',
                                    show_download_local=True)
                    
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
    return render_template('index.html', serverless_mode=SERVERLESS_MODE, size_limit=MAX_FILE_SIZE)

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
            "max_content_length": app.config['MAX_CONTENT_LENGTH']
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

@app.route('/system-check')
def system_check():
    """Perform system compatibility check and verify required dependencies"""
    try:
        # Check Python version
        python_version = sys.version_info
        python_ok = python_version.major >= 3 and python_version.minor >= 6
        
        # Check PyMuPDF
        fitz_ok = False
        fitz_version = "Not installed"
        try:
            import fitz
            fitz_version = fitz.__version__
            fitz_ok = True
        except ImportError:
            pass
            
        # Check Pillow
        pil_ok = False
        pil_version = "Not installed"
        try:
            from PIL import __version__ as pil_version
            pil_ok = True
        except ImportError:
            try:
                from PIL import Image
                pil_version = "Installed (version unknown)"
                pil_ok = True
            except ImportError:
                pass
                
        # Check for temp directory access
        temp_ok = False
        temp_path = ""
        try:
            temp_dir = tempfile.mkdtemp()
            temp_path = temp_dir
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            os.rmdir(temp_dir)
            temp_ok = True
        except Exception as e:
            app.logger.error(f"Temp directory issue: {str(e)}")
            
        # Check if the system has enough memory (approximate check)
        mem_ok = True
        mem_info = "Unknown"
        try:
            import psutil
            mem = psutil.virtual_memory()
            mem_ok = mem.available > 500 * 1024 * 1024  # 500MB minimum
            mem_info = f"{mem.available / (1024 * 1024):.0f}MB available"
        except ImportError:
            pass
            
        # Determine overall status
        system_ready = python_ok and fitz_ok and pil_ok and temp_ok
        
        # Create result
        result = {
            "system_ready": system_ready,
            "python": {
                "version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
                "ok": python_ok
            },
            "dependencies": {
                "pymupdf": {
                    "version": fitz_version,
                    "ok": fitz_ok
                },
                "pillow": {
                    "version": pil_version,
                    "ok": pil_ok
                }
            },
            "system": {
                "temp_directory": {
                    "path": temp_path,
                    "ok": temp_ok
                },
                "memory": {
                    "info": mem_info,
                    "ok": mem_ok
                }
            }
        }
        
        return render_template('system_check.html', check=result)
    except Exception as e:
        app.logger.error(f"Error in system check: {str(e)}")
        return render_template('system_check.html', error=str(e))

if __name__ == '__main__':
    # Run directly 
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 