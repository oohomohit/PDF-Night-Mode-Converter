# PDF Night Mode Converter

A tool that converts PDF files to night mode (dark background with light text).

## Features

- Convert PDFs to night mode (inverts colors and adds dark background)
- Web interface for online use with small files (up to 2MB)
- Command-line tool for local processing of files of any size
- Multithreaded support for faster local processing
- High-quality output with customizable settings

## Requirements

- Python 3.6+
- PyMuPDF (fitz)
- Pillow (PIL)
- Flask (for web interface)

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

### Web Application (For Small PDFs)

The web application is best for PDFs up to 2MB:

1. Run the Flask application:

```bash
python app.py
```

2. Open your web browser and go to http://127.0.0.1:5000/

3. Upload a PDF file using the web interface

4. Click the "Convert to Night Mode" button

5. Download your converted PDF

### Command-Line Tool (For Any Size PDFs)

For processing files of any size, use the local command-line tool with multithreading:

```bash
python local_converter.py input.pdf -o output_night_mode.pdf
```

Options:
- `-o, --output`: Specify output filename (default: adds `_night_mode` suffix)
- `-q, --quality`: Image quality (1-100, default: 90)
- `-s, --scale`: Resolution scale factor (default: 2.0)
- `-t, --threads`: Number of processing threads (default: 4)

Example with options:
```bash
python local_converter.py large_textbook.pdf -q 95 -s 2.5 -t 8
```

## How It Works

The application uses PyMuPDF to render PDF pages as images, inverts the colors using PIL (Python Imaging Library), and then creates a new PDF with these inverted images on a black background.

The local command-line version uses multithreading to process pages in parallel, making it much faster for large documents.

## Online Version Limitations

The online version is intended for small files only (up to 2MB) due to:
- Memory constraints in browser environments
- Serverless platform limitations when deployed online
- Processing time considerations

For larger files, please download and use the local command-line version.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 