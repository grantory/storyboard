# 🎬 Project Maestro v2 - AI Storyboard Generator

A powerful desktop application that transforms short videos into professional storyboard shots using AI. Built with CustomTkinter for a modern, accessible interface.

## ✨ Features

- **🎥 Video Analysis**: Upload short videos (≤30s) for AI-powered scene analysis
- **🎨 Style Transfer**: Apply visual styles from reference images to generated shots
- **🎭 Smart Shot Generation**: AI director creates 3-10 storyboard shots based on video content
- **🖼️ High-Quality Images**: Generate storyboard images using advanced AI models
- **⚡ Auto-Upscaling**: Built-in Real-ESRGAN upscaling (2x) for professional quality
- **💾 Auto-Save**: Automatically saves upscaled images to `output/` folder
- **♿ Accessibility**: Light/Dark theme toggle, UI text scaling (75%-175%)
- **⌨️ Keyboard Shortcuts**: Efficient workflow with hotkeys

## 🚀 Quick Start

### Windows (Recommended)
1. Download and extract the project
2. Double-click `launch.bat` - it will:
   - Create a Python virtual environment
   - Install all dependencies
   - Set up configuration files
   - Launch the application
3. Add your OpenRouter API key to `.env` when prompted

### Manual Installation
```bash
# Clone the repository
git clone <repository-url>
cd AIStoryBoard-v3

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m src.gui.main
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
# Required
OPENROUTER_API_KEY=sk-or-your-key-here

# Optional - Model Configuration
V2_OPENROUTER_CONTEXT_MODEL=gpt-4o-mini
V2_OPENROUTER_DIRECTOR_MODEL=gpt-4o
V2_OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image-preview

# Optional - Performance Tuning
V2_MAX_CONCURRENT_REQUESTS=5
V2_REQUEST_TIMEOUT_SEC=60
```

### API Key Setup
1. Get your API key from [OpenRouter](https://openrouter.ai/)
2. Add it to your `.env` file: `OPENROUTER_API_KEY=sk-or-your-key-here`

### Packaged Real-ESRGAN
- This includes `weights/realesr-general-x4v3.pth`. The launcher sets `REAL_ESRGAN_WEIGHTS_DIR` to the local `weights/` folder so no download is required.
- If the weights file is missing, the app will try to download it at runtime. To stay offline, ensure the file exists before launch.

## 🎯 How to Use

1. **📹 Upload Video**: Select a short video file (MP4, ≤30s)
2. **🎨 Upload Style Image**: Choose a reference image for visual style
3. **🔍 Analyze**: Click "Analyze Video" to extract context and generate scene description
4. **✏️ Edit Context**: Review and modify the AI-generated scene description
5. **🎭 Generate Shots**: Click "Generate Shots" to create storyboard descriptions
6. **🖼️ Generate Images**: Create images for individual shots or all at once
7. **💾 Save Results**: Images are automatically upscaled and saved to `output/` folder

## ⌨️ Keyboard Shortcuts

- `Ctrl+O`: Open Video
- `Ctrl+S`: Open Style Image  
- `Ctrl+A`: Analyze Video
- `Ctrl+G`: Generate Shots
- `Ctrl+L`: Clear Logs
- `F1`: Show Help

## 🏗️ Project Structure

```
AIStoryBoard-v3/
├── src/
│   ├── gui/           # CustomTkinter GUI components
│   ├── services/      # Core business logic
│   ├── config.py      # Configuration management
│   └── types.py       # Data models
├── weights/           # Real-ESRGAN model weights
├── output/           # Generated storyboard images
├── requirements.txt  # Python dependencies
└── launch.bat        # Windows launcher script
```

## 🐛 Troubleshooting

### Common Issues

**Real-ESRGAN weights missing**
- The app will attempt to download weights automatically
- For offline use, ensure `weights/realesr-general-x4v3.pth` exists

**API timeouts**
- Increase `V2_REQUEST_TIMEOUT_SEC` in `.env`
- Check your internet connection
- Verify your OpenRouter API key

**Connection issues**
- Verify your `OPENROUTER_API_KEY` is correct
- Check your internet connection
- Try different models if one fails

### Performance Tips

- Use shorter videos (≤30s) for faster processing
- Adjust `V2_MAX_CONCURRENT_REQUESTS` based on your system
- Close other applications to free up GPU memory for upscaling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Commit: `git commit -m "Add feature"`
5. Push: `git push origin feature-name`
6. Submit a Pull Request

## 📄 License

Part of the Lovelife AI ecosystem. See project-level license terms.

## 🙏 Acknowledgments

- **OpenRouter** for AI model access
- **Real-ESRGAN** for image upscaling
- **CustomTkinter** for the modern GUI framework
- **OpenAI** and **Google** for the AI models

---

**Made with ❤️ for content creators and filmmakers**
