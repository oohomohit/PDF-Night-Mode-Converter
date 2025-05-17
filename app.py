import os
import uuid
import tempfile
from flask import Flask, request, render_template, send_file, redirect, url_for
from werkzeug.utils import secure_filename
from pdf_night_mode import convert_pdf_to_night_mode

app = Flask(__name__)

# Configure max content length
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return render_template('index.html', error='No file part')
        
        file = request.files['file']
        
        # If user does not select file, browser submits an empty file
        if file.filename == '':
            return render_template('index.html', error='No file selected')
        
        if file and allowed_file(file.filename):
            try:
                # Create temporary directory for this request
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Generate unique filename to avoid collisions
                    original_filename = secure_filename(file.filename)
                    
                    # Save uploaded file
                    input_path = os.path.join(temp_dir, original_filename)
                    file.save(input_path)
                    
                    # Generate output filename and path
                    output_filename = f"night_mode_{original_filename}"
                    output_path = os.path.join(temp_dir, output_filename)
                    
                    # Convert the PDF
                    success = convert_pdf_to_night_mode(input_path, output_path)
                    
                    if success:
                        # Store the path in session
                        return send_file(
                            output_path,
                            as_attachment=True,
                            download_name=output_filename
                        )
                    else:
                        return render_template('index.html', error='Error processing PDF')
            except Exception as e:
                app.logger.error(f"Error processing PDF: {str(e)}")
                return render_template('index.html', error=f'Processing error: {str(e)}')
        
        return render_template('index.html', error='Invalid file type. Only PDF files are allowed.')
    
    return render_template('index.html')

# Health check endpoint
@app.route('/health')
def health_check():
    return {"status": "ok"}, 200

if __name__ == '__main__':
    # Run directly 
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 