# YouLoad

A fast, simple desktop video downloader built with Python, PySide6, and yt-dlp.

YouLoad is designed around a clean, minimal interface while still giving you control over video and audio quality, download locations, queues, and download history.

## Features

* YouTube video downloading
* Separate video and audio quality selection
* Audio-only downloads
* Original audio selection when multiple audio tracks are available
* Download progress, speed, and ETA
* Download cancellation
* Download queue
* Persistent download history
* Persistent user data
* Open the original video from Recent Activity
* Choose a custom download folder
* Built-in FFmpeg support
* Built-in yt-dlp support
* Dependency and application update checking
* Automatic FFmpeg updates
* Dark, minimal desktop UI
* Windows application icon and branding
* Random startup tips and facts

## Tech Stack

* **Python**
* **PySide6**
* **Qt WebEngine**
* **JavaScript / HTML / CSS**
* **yt-dlp**
* **FFmpeg**

## Project Structure

```text
YouLoad/
├── core/
│   ├── downloader.py
│   ├── user_data.py
│   └── ...
├── ui/
│   ├── assets/
│   ├── css/
│   ├── js/
│   ├── pages/
│   └── index.html
├── updater/
│   ├── components.json
│   ├── dependency_checker.py
│   ├── component_updater.py
│   └── app_updater.py
├── runtime/
├── main.py
├── requirements.txt
├── LICENSE
└── README.md
```

## Requirements

* Windows
* Python 3.12 or newer recommended
* Internet connection for video extraction and updates

## Installation

Clone the repository:

```bash
git clone https://github.com/Nispax-Official/YouLoad.git
cd YouLoad
```

Create a virtual environment:

```bash
py -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run YouLoad:

```bash
py main.py
```

## Configuration

Application settings and version information are kept in the project's configuration files.

The application version is also used by the built-in updater when checking GitHub releases.

Use standard version formats such as:

```text
0.1.0
1.0.0b1
1.0.0rc1
1.0.0
```

## Updates

YouLoad includes an updater that checks the configured release sources for newer versions of:

* YouLoad
* yt-dlp
* FFmpeg
* Bundled PySide6 components

PySide6 runtime components that are bundled into the application are updated through a new YouLoad release rather than being replaced while the application is running.

## User Data

YouLoad stores application user data separately from the browser cache.

Persistent data includes things such as:

```text
history
queue
```

The application also uses a persistent Qt WebEngine profile for browser storage and cache data.

## FFmpeg

FFmpeg is used for media processing tasks such as combining separate video and audio streams.

YouLoad can use the bundled FFmpeg runtime so users do not need to install FFmpeg separately.

## Legal

YouLoad is a downloader application. Users are responsible for making sure their use of YouLoad complies with the applicable laws, website terms, and copyright permissions in their jurisdiction.

Only download content that you are legally permitted to download.

## License

YouLoad is released under the **MIT License**.

See [`LICENSE`](LICENSE) for the complete license text.

## Credits

YouLoad uses:

* [yt-dlp](https://github.com/yt-dlp/yt-dlp)
* [FFmpeg](https://ffmpeg.org/)
* [PySide6](https://doc.qt.io/qtforpython/)

## Developed By

**NISPAX InfoTech**

YouLoad is proudly developed by NISPAX InfoTech.

---

> YouLoad is an independent project and is not affiliated with YouTube.
