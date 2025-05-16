# fastraw

![License](https://img.shields.io/github/license/marcelytumy/fastraw)
![Language](https://img.shields.io/badge/language-Python-blue)

A lightweight, fast RAW image viewer built with Python that prioritizes quick loading and smooth transitions between preview and full-quality images.

## Features

- **Instant Loading**: Uses embedded previews to display images immediately
- **Smooth Transitions**: Elegant fade between preview and full-quality images
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Minimalist UI**: Dark theme, clean interface
- **Support for Multiple RAW Formats**: Compatible with most camera RAW formats including:
  - ARW (Sony)
  - CR2/CR3 (Canon)
  - NEF (Nikon)
  - RAF (Fujifilm)
  - DNG (Adobe/Generic)
  - ORF (Olympus)
  - PEF (Pentax)
  - RW2 (Panasonic)
  - X3F (Sigma)

## Installation

### Option 1: Download Pre-built Binary

Download the latest release for your operating system from the [Releases page](https://github.com/marcelytumy/fastraw/releases).

### Option 2: Run from Source

1. Clone the repository:
```bash
git clone https://github.com/marcelytumy/fastraw.git
cd fastraw
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

### Option 3: Build Your Own Binary

1. Clone the repository and install requirements:
```bash
git clone https://github.com/marcelytumy/fastraw.git
cd fastraw
pip install -r requirements.txt
```

2. Use PyInstaller to build the executable:
```bash
pyinstaller fastraw.spec
```

3. The executable will be created in the `dist` folder.

## Usage

### Basic Usage

1. Launch fastraw
2. Click the "Open Image" button or press the `O` key to open a file dialog
3. Select a RAW image file to view

### Command-Line Usage

You can also open images directly from the command line:

```bash
fastraw /path/to/image.raw
```

### Controls

- **O**: Open file dialog
- **ESC**: Exit the application
- **Right-click**: Show context menu

## How It Works

fastraw uses a two-stage loading process for optimal user experience:

1. **Stage 1 - Preview**: Extracts the embedded JPEG preview from the RAW file or generates a quick low-resolution preview for immediate display
2. **Stage 2 - Full Image**: Processes the complete RAW file with high-quality settings using rawpy's advanced demosaicing algorithms
3. **Transition**: Smoothly fades from preview to full-quality image once processing is complete

## Feature Roadmap
- [ ] Zoom and pan functionality
- [ ] Metadata display (EXIF information)
- [ ] Customizable keyboard shortcuts
- [ ] Export options (JPEG, PNG, TIFF)
- [ ] Histogram display
- [ ] Improved Windows and macOS integration
- [ ] Support for video files
- [ ] Folder navigation
- [ ] Plugin system for extensibility
- [ ] GPU acceleration for faster processing

## Requirements

- Python 3.7+
- Tkinter (included with most Python installations)
- Pillow (PIL Fork) for image processing
- rawpy for RAW file handling
- numpy for image data manipulation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [rawpy](https://github.com/letmaik/rawpy) for RAW file processing
- [Pillow](https://python-pillow.org/) for image handling
- [LibRaw](https://www.libraw.org/) which powers the rawpy library
