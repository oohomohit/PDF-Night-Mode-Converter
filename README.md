# PDF Night Mode Converter

A web application that converts PDF files to night mode (dark background with light text).

## Features

- Upload PDF files through a simple web interface
- Automatic conversion to night mode
- Download or view the converted PDF
- Responsive design that works on desktop and mobile

## Requirements

- Python 3.6+
- Flask
- PyMuPDF (fitz)
- Pillow (PIL)

## Installation

1. Clone this repository or download the files:

```bash
git clone https://github.com/yourusername/pdf-night-mode.git
cd pdf-night-mode
```

2. Install the required dependencies:

```bash
pip install flask pymupdf pillow
```

## Usage

1. Run the Flask application:

```bash
python app.py
```

2. Open your web browser and go to http://127.0.0.1:5000/

3. Upload a PDF file using the web interface

4. Click the "Convert to Night Mode" button

5. Download or view your converted PDF

## How It Works

The application uses PyMuPDF to render PDF pages as images, inverts the colors using PIL (Python Imaging Library), and then creates a new PDF with these inverted images.

## Limitations

- The conversion process can be memory-intensive for large PDFs
- Maximum upload size is limited to 16MB by default
- Text in the resulting PDF is not selectable (it's converted to images)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 