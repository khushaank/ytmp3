# YT Music Downloader

![Made with Python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)

A simple, self-hosted web application to download YouTube playlists or single videos as high-quality MP3 files, complete with metadata and album art.

***

## Features

* **Download Playlists or Single Videos:** Just paste a URL.
* **High-Quality Audio:** Converts to 320kbps MP3 format (MP4 video also available).
* **Automatic Metadata:** Embeds the correct **Title**, **Artist**, and **Album** tags into the MP3 file.
* **Embeds Thumbnails:** Adds the video thumbnail as the cover/album art.
* **Modern Web UI:** A clean interface that runs locally in your browser.
* **Dark Mode:** Automatically adapts to your system's light or dark theme.
* **Real-time Progress:** See download status, progress bars, and a full log modal.
* **Organized Output:** Saves all files to your user's `Music` folder under `YTMusicDownloader/[Playlist Name]`.

## Installation (for Users)

1.  Go to the [**Releases**](https://github.com/YOUR_USERNAME/YOUR_REPO/releases) page of this repository.
2.  Download **both** files:
    * `YTMusicDownloader_Setup.exe`
    * `ffmpeg.exe`
3.  Place **both files in the same folder** (e.g., your Desktop or Downloads folder).
4.  Run `YTMusicDownloader_Setup.exe`. The installer will automatically find `ffmpeg.exe` and install it for you.
5.  Launch **"YT Music Downloader"** from your Start Menu. It will automatically open the app in your browser at `http://127.0.0.1:5000`.

## Building from Source (for Developers)

If you want to build the application yourself, follow these steps.

### Prerequisites

* [Python 3.10+](https://www.python.org/downloads/)
* [FFmpeg](https://ffmpeg.org/download.html) (Download the "essentials" build and place `ffmpeg.exe` in the root of this project folder, next to `ytmp3.py`).
* [Inno Setup](https://jrsoftware.org/isinfo.php) (To create the final installer).

### 1. Clone the Repository

```bash
git clone [https://github.com/YOUR_USERNAME/YOUR_REPO.git](https://github.com/YOUR_USERNAME/YOUR_REPO.git)
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
