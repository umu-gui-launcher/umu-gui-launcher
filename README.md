# Umu-Run Games Launcher

A GTK-based game launcher for managing and running Windows games on Linux using umu-run.

## Features

- Clean and modern GTK 4.0 interface
- Support for Windows executables (32-bit and 64-bit)
- Configurable launch options
- Process management and monitoring
- GameMode and MangoHud integration
- Virtual desktop support

## Requirements

- Python 3.8+
- GTK 4.0
- umu-run
- Optional: GameMode, MangoHud

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have umu-run installed on your system.

## Usage

Run the launcher:
```bash
python3 main.py
```

## Configuration

The launcher can be configured through the settings dialog (gear icon). Options include:
- Recursive search
- Display options (fullscreen, virtual desktop)
- Performance options (GameMode, MangoHud)
- Additional launch options
