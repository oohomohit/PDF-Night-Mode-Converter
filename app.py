import os
import uuid
from flask import Flask, request, render_template, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from pdf_night_mode import convert_pdf_to_night_mode

app = Flask(__name__)

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Create upload and result directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            # Generate unique filename to avoid collisions
            original_filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())
            filename = f"{unique_id}_{original_filename}"
            
            # Save uploaded file
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_path)
            
            # Generate output filename and convert to night mode
            output_filename = f"night_mode_{original_filename}"
            output_path = os.path.join(app.config['RESULT_FOLDER'], output_filename)
            
            # Convert the PDF
            success = convert_pdf_to_night_mode(input_path, output_path)
            
            if success:
                # Redirect to download page
                return redirect(url_for('download_file', filename=output_filename))
            else:
                return render_template('index.html', error='Error processing PDF')
        
        return render_template('index.html', error='Invalid file type. Only PDF files are allowed.')
    
    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    return render_template('download.html', filename=filename)

@app.route('/get-file/<filename>')
def get_file(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename, as_attachment=True)

@app.route('/results/<filename>')
def view_file(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

# For Vercel serverless deployment
@app.route('/_vercel/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Health check endpoint
@app.route('/health')
def health_check():
    return {"status": "ok"}, 200

if __name__ == '__main__':
    # Run directly 
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 