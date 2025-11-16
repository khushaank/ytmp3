# YT Music Downloader

![Made with Python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)

A simple, self-hosted web application to download YouTube playlists or single videos as high-quality MP3 files, complete with metadata and album art.

---

## Screenshot

(Add a screenshot of your app here — drag and drop an image into this README on GitHub)

![YT Music Downloader Screenshot](https://i.imgur.com/your-screenshot-url.png)

---

## Features

- **Download Playlists or Single Videos:** Paste any YouTube URL.
- **High-Quality Audio:** Converts to 320kbps MP3 (MP4 video option also available).
- **Automatic Metadata:** MP3 files include Title, Artist, and Album tags.
- **Embedded Thumbnail Art:** The YouTube thumbnail becomes the cover image.
- **Modern Web UI:** Clean, responsive interface that runs locally in your browser.
- **Dark Mode:** Automatically adapts to your system theme.
- **Real-time Progress:** Progress bars, live logs, and status updates.
- **Organized Output:** Files saved under your user's `Music/YTMusicDownloader/[Playlist Name]`.

---

## Installation (For Users)

1. Visit the **[Releases](https://github.com/YOUR_USERNAME/YOUR_REPO/releases)** page.
2. Download the latest `YTMusicDownloader_Setup.exe`.
3. Run the installer (includes all dependencies — even `ffmpeg`).
4. Launch **YT Music Downloader** from the Start Menu.  
   The app will open automatically at `http://127.0.0.1:5000`.

---

## Building From Source (For Developers)

### Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [FFmpeg](https://ffmpeg.org/download.html)  
  Download the *essentials* build and place `ffmpeg.exe` in the project root (next to `ytmp3.py`).
- [Inno Setup](https://jrsoftware.org/isinfo.php) — required for building the final installer.

---

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

---

## 2. Create a Virtual Environment

```bash
# Windows
python -m venv .venv
.\.venv\Scriptsctivate
```

---

## 3. Install Python Dependencies

All dependencies are listed in `requirements.txt`.

```bash
pip install -r requirements.txt
```

---

## 4. Run Locally (Development)

Starts the server in debug mode.

```bash
python ytmp3.py
```

---

## 5. Build the Standalone .exe

Uses **PyInstaller** to bundle Python, your script, static files, and `ffmpeg.exe`.

```bash
pyinstaller --onefile --windowed --name ytmp3 ^
  --icon="static\favicon.ico" ^
  --add-binary "ffmpeg.exe;." ^
  --add-data "static;static" ^
  ytmp3.py
```

The executable will appear in the `dist/` folder.

---

## 6. Build the Final Installer

Uses **Inno Setup** to generate `YTMusicDownloader_Setup.exe`.

1. Open **Inno Setup**.
2. File → Open → select `setup.iss` from this repository.
3. Build → Compile.
4. The final installer will appear in an `Output/` folder.

---

## Acknowledgements

This project is built on the excellent work of:

- **yt-dlp**
- **FFmpeg**
- **Flask**
- **Waitress**
- **PyInstaller**
- **Inno Setup**
