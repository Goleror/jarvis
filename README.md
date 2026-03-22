# Jarvis 2026

A voice-controlled AI assistant project combining web interface, Python backend, and IoT integration.

## Project Structure

```
Jarvis2026/
├── jarvis.py              # Main Python backend
├── index.html             # Web interface
├── style.css              # Frontend styling
├── script.js              # Frontend JavaScript
├── inventory.json         # Configuration/data file
├── ESP2026/               # Arduino/ESP8266 firmware
│   └── ESP2026.ino       # Microcontroller code
├── model/                 # Speech recognition model
│   ├── am/               # Acoustic model
│   ├── conf/             # Configuration files
│   ├── graph/            # FST graphs
│   └── ivector/          # iVector model files
└── sounds/               # Audio files
    ├── error/            # Error sound files
    ├── jarvis_voice/     # Jarvis voice samples
    ├── yessir/           # Acknowledgment sounds
    └── привет/           # Russian greeting sounds
```

## Features

- **Web Interface**: HTML/CSS/JavaScript frontend for control and interaction
- **Python Backend**: Core processing and logic (jarvis.py)
- **Speech Recognition**: Kaldi-based speech recognition model
- **IoT Integration**: ESP8266/ESP32 microcontroller support
- **Multilingual**: Support for multiple languages (English, Russian)
- **Audio Processing**: Sound recognition and voice feedback

## Requirements

- Python 3.x
- Node.js (for frontend dependencies)
- Arduino IDE (for ESP2026 firmware)
- Kaldi speech recognition framework

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Goleror/jarvis.git
   cd Jarvis2026
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies** (if needed)
   ```bash
   npm install
   ```

4. **Configure Arduino firmware** 
   - Open `ESP2026/ESP2026.ino` in Arduino IDE
   - Select appropriate board (ESP8266/ESP32)
   - Upload to your microcontroller

## Usage

### Starting the Python Backend

```bash
python jarvis.py
```

### Accessing the Web Interface

Open `index.html` in a web browser to access the control interface.

## Configuration

Edit `inventory.json` to configure:
- Device settings
- API endpoints
- Voice parameters
- Sound preferences

## Voice Commands

The system supports voice commands in multiple languages:
- English commands
- Russian commands (Russian audio files included)

## Audio Files

- **error/**: Error notification sounds
- **jarvis_voice/**: Jarvis response voice samples
- **yessir/**: Acknowledgment sounds
- **привет/**: Russian greeting sounds

## Hardware

### ESP2026 Microcontroller
- Supports WiFi connectivity
- GPIO pin control
- Sensor integration
- Real-time communication with main backend

## Speech Recognition

Uses Kaldi framework for offline speech recognition:
- Acoustic model (am/final.mdl)
- Language model (Gr.fst)
- iVector features for speaker adaptation
- MFCC feature extraction

## Development

### Backend Development
Edit `jarvis.py` for core functionality changes.

### Frontend Development
Modify `index.html`, `style.css`, and `script.js` for interface updates.

### Model Updates
Replace files in the `model/` directory for improved speech recognition.

## Troubleshooting

If you encounter issues:

1. **Python errors**: Ensure all dependencies are installed
2. **ESP2026 connection**: Check USB driver and board selection
3. **Speech recognition**: Verify model files are present in the model/ directory
4. **Audio issues**: Check sounds/ directory has required audio files

## License

Please refer to the project license for usage terms.

## Author

Goleror

## Support

For issues and feature requests, please create an issue on GitHub.

---

**Last Updated**: March 22, 2026
