# SACMES Web

Multi-user web platform for electrochemical data analysis with real-time file monitoring.

## Project Structure

```
SACMES_Web-Multiuser/
├── app.py                          # Main Flask server
├── wsgi.py                         # WSGI entry point for production
├── agent.py                        # Desktop agent for file monitoring
├── requirements.txt                # Server dependencies
├── requirements_agent_minimal.txt  # Minimal agent dependencies
│
├── data_processing/                # Data analysis modules
│   ├── data_reader.py
│   ├── swv_analyzer.py
│   └── cv_analyzer.py
│
├── static/                         # Frontend assets
│   ├── js/                         # JavaScript modules
│   │   ├── swv_module.js
│   │   ├── cv_module.js
│   │   └── plot_utils.js
│   └── css/
│
├── templates/
│   └── index.html                  # Main web interface
│
├── temp_uploads/                   # Temporary file storage
│
├── agent_minimal.spec              # PyInstaller config for agent
├── build_agent_minimal.bat         # Agent build script (recommended)
├── build_agent_exe.bat             # Agent build script (alternative)
├── test_dependencies.bat           # Test agent dependencies
├── cleanup_build.bat               # Clean build artifacts
│
├── Netzlab.ico                     # Application icon
├── BUILD_AGENT_README.md           # Agent build guide
├── VERSION_FIX_SUMMARY.md          # Version compatibility notes
└── SACMES_SWV_FrequencyMap.py      # Desktop version (reference)
```

## Quick Start

### Server Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py

# Run production server
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 wsgi:app
```

### Agent Setup

```bash
# Build agent EXE
build_agent_minimal.bat

# The EXE will be in: dist/SACMES_Agent_Minimal.exe
```

## Features

- SWV (Square Wave Voltammetry) Analysis
  - Peak Height Extraction
  - Area Under Curve (AUC)
  - Frequency Map Analysis
  - Multi-electrode support

- CV (Cyclic Voltammetry) Analysis
  - Real-time plotting
  - Multi-file processing

- Real-time Agent Monitoring
  - File system monitoring
  - Automatic data upload
  - Socket.IO communication

## Requirements

- Python 3.8+
- Flask 2.0+
- numpy, scipy (for data processing)
- Socket.IO (for real-time communication)

## Deployment

### Local Development
```bash
python app.py
```

### Production (Linux/Cloud)
```bash
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 wsgi:app
```

### Docker (Optional)
See deployment documentation for containerization.

## License

Research use only.
