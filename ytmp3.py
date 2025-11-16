from flask import Flask, render_template_string, request, jsonify, send_from_directory
import yt_dlp
import threading
import os
import queue
import concurrent.futures
import re
from waitress import serve
import webbrowser
import sys

# --- Configuration ---

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # Not bundled, just running as a .py script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

# This path will now correctly point to ffmpeg.exe even when bundled
FFMPEG_PATH = get_resource_path('ffmpeg.exe')
STATIC_DIR = get_resource_path('static')


# In-memory dictionary to store download status and a lock for thread-safe updates
DOWNLOAD_STATUS = {}
status_lock = threading.Lock()

# Queue for live log output
LOG_QUEUE = queue.Queue()

app = Flask(__name__)

# --- HTML Template with Tailwind CSS and JavaScript ---
HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YT Music Downloader</title>
    <link rel="icon" href="/favicon.ico" type="image/x-icon">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark')
        } else {
            document.documentElement.classList.remove('dark')
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; }
        html { scroll-behavior: smooth; }
        .modal {
            display: none; position: fixed; z-index: 100;
            left: 0; top: 0; width: 100%; height: 100%;
            overflow: auto; background-color: rgba(0,0,0,0.4);
            transition: opacity 0.3s ease;
        }
        .modal-content {
            background-color: #fefefe; margin: 10% auto; padding: 24px;
            border: 1px solid #888; width: 80%; max-width: 600px;
            border-radius: 0.75rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .dark .modal-content {
             background-color: #1f2937; /* gray-800 */
             border-color: #374151; /* gray-700 */
        }
        .close-btn { color: #aaa; float: right; font-size: 28px; font-weight: bold; }
        .close-btn:hover, .close-btn:focus { color: #000; text-decoration: none; cursor: pointer; }
        .dark .close-btn:hover, .dark .close-btn:focus { color: #fff; }
    </style>
</head>
<body class="bg-slate-100 dark:bg-slate-900 text-slate-800 dark:text-slate-200 p-8 flex flex-col items-center min-h-screen transition-colors duration-300">
    <div class="bg-white dark:bg-slate-800 p-8 rounded-xl shadow-lg w-full max-w-2xl transition-all duration-300">
        <h1 class="text-3xl font-bold text-center mb-6 text-indigo-600 dark:text-indigo-400">Download YouTube Music</h1>
        <form id="fetchForm" class="flex flex-col sm:flex-row gap-4 mb-4">
            <input type="text" id="playlistUrl" name="url" placeholder="Enter Playlist or Video URL"
                   class="flex-1 p-3 border-2 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 rounded-lg 
                          focus:outline-none focus:border-indigo-500 dark:focus:border-indigo-400 
                          focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-800
                          transition-all duration-300" required>
            <div class="flex flex-col sm:flex-row gap-4">
                <label class="inline-flex items-center">
                    <input type="radio" name="format" value="mp3" checked class="form-radio text-indigo-600 h-5 w-5 focus:ring-indigo-500">
                    <span class="ml-2 text-slate-700 dark:text-slate-300">MP3</span>
                </label>
                <label class="inline-flex items-center">
                    <input type="radio" name="format" value="mp4" class="form-radio text-indigo-600 h-5 w-5 focus:ring-indigo-500">
                    <span class="ml-2 text-slate-700 dark:text-slate-300">MP4</span>
                </label>
            </div>
            <button type="submit" id="fetchBtn"
                    class="bg-indigo-600 text-white font-semibold py-3 px-6 rounded-lg
                           hover:bg-indigo-700 dark:hover:bg-indigo-500 
                           focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-slate-800
                           transition-all duration-300 shadow-md hover:shadow-lg">
                Fetch
            </button>
        </form>
        
        <div id="errorContainer" class="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-200 px-4 py-3 rounded-lg relative mb-6 hidden" role="alert">
            <strong class="font-bold">Error:</strong>
            <span id="errorText" class="block sm:inline">Something went wrong.</span>
        </div>

        <div id="loading" class="text-center hidden">
             <div class="flex justify-center items-center">
                   <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 dark:border-indigo-400"></div>
             </div>
             <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">Fetching details...</p>
        </div>

        <div id="playlistInfo" class="hidden">
            <div id="playlistTitle" class="text-2xl font-bold mb-4 text-center"></div>
            <div id="selectButtons" class="flex justify-around gap-4 mb-4">
                <button id="selectAllBtn" class="w-full bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 font-semibold py-2 px-4 rounded-lg 
                                               hover:bg-slate-300 dark:hover:bg-slate-600 
                                               focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-400 dark:focus:ring-offset-slate-800
                                               transition-all duration-300">
                    Select All
                </button>
                <button id="downloadSelectedBtn" class="w-full bg-indigo-600 text-white font-semibold py-2 px-4 rounded-lg 
                                                      hover:bg-indigo-700 dark:hover:bg-indigo-500
                                                      focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-slate-800
                                                      transition-all duration-300">
                    Download Selected (<span id="selectedCount">0</span>)
                </button>
            </div>

            <div id="statusContainer" class="p-4 rounded-lg bg-indigo-50 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 mb-6 hidden transition-all duration-300">
                <div id="statusText" class="font-semibold text-center animate-pulse">Starting download...</div>
            </div>

            <div id="downloadStats" class="flex justify-around mb-6 text-sm font-semibold">
                <span class="text-indigo-600 dark:text-indigo-400">Total: <span id="totalItems">0</span></span>
                <span class="text-green-600 dark:text-green-400">Downloaded: <span id="downloadedItems">0</span></span>
                <span class="text-red-600 dark:text-red-400">Failed: <span id="failedItems">0</span></span>
            </div>

            <div id="progressList" class="space-y-4">
                </div>
                
            <div id="resetContainer" class="mt-8 flex justify-center hidden">
                <button id="resetBtn" class="w-full max-w-xs bg-gray-500 dark:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg 
                                           hover:bg-gray-600 dark:hover:bg-gray-500 
                                           focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 dark:focus:ring-offset-slate-800
                                           transition-all duration-300 shadow-md hover:shadow-lg">
                    Download Another
                </button>
            </div>
            
            <div class="mt-6 flex justify-center">
                <button id="logBtn" class="bg-slate-600 dark:bg-slate-700 text-white font-semibold py-2 px-4 rounded-lg hidden 
                                         hover:bg-slate-700 dark:hover:bg-slate-600 
                                         focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500 dark:focus:ring-offset-slate-800
                                         transition-all duration-300">
                    View Logs
                </button>
            </div>
        </div>

    </div>

    <div id="logModal" class="modal">
        <div class="modal-content">
            <span class="close-btn" onclick="document.getElementById('logModal').style.display='none'">&times;</span>
            <h2 class="text-2xl font-bold mb-4 text-slate-800 dark:text-slate-200">Download Logs</h2>
            <pre id="logContent" class="bg-gray-800 dark:bg-gray-900 text-white p-4 rounded-md overflow-y-scroll max-h-80 text-sm"></pre>
        </div>
    </div>

    <script>
        const fetchForm = document.getElementById('fetchForm');
        const playlistUrlInput = document.getElementById('playlistUrl');
        const fetchBtn = document.getElementById('fetchBtn');
        const loading = document.getElementById('loading');
        const playlistInfo = document.getElementById('playlistInfo');
        const playlistTitleEl = document.getElementById('playlistTitle');
        const selectAllBtn = document.getElementById('selectAllBtn');
        const downloadSelectedBtn = document.getElementById('downloadSelectedBtn');
        const selectedCountSpan = document.getElementById('selectedCount');
        const statusContainer = document.getElementById('statusContainer');
        const statusText = document.getElementById('statusText');
        const progressList = document.getElementById('progressList');
        const totalItemsSpan = document.getElementById('totalItems');
        const downloadedItemsSpan = document.getElementById('downloadedItems');
        const failedItemsSpan = document.getElementById('failedItems');
        const logBtn = document.getElementById('logBtn');
        const logModal = document.getElementById('logModal');
        const logContent = document.getElementById('logContent');
        const errorContainer = document.getElementById('errorContainer');
        const errorText = document.getElementById('errorText');
        const resetContainer = document.getElementById('resetContainer');
        const resetBtn = document.getElementById('resetBtn');

        let pollingInterval;
        let logPollingInterval;
        let fetchedSongs = [];
        let playlistTitle = "";
        let selectedFormat = "mp3";

        function setDownloadUIState(downloading) {
            downloadSelectedBtn.disabled = downloading;
            selectAllBtn.disabled = downloading;
            fetchBtn.disabled = downloading;
            playlistUrlInput.disabled = downloading;
            
            statusContainer.className = 'p-4 rounded-lg mb-6 transition-all duration-300'; // Reset
            statusContainer.classList.add('bg-indigo-50', 'dark:bg-indigo-900', 'text-indigo-600', 'dark:text-indigo-300');
            
            if (downloading) {
                logBtn.classList.remove('hidden');
                statusContainer.classList.remove('hidden');
                statusText.classList.add('animate-pulse');
                resetContainer.classList.add('hidden');
            } else {
                statusText.classList.remove('animate-pulse');
            }
        }

        logBtn.onclick = () => logModal.style.display = 'block';
        window.onclick = (event) => {
            if (event.target == logModal) {
                logModal.style.display = 'none';
            }
        };

        async function fetchLogs() {
            try {
                const response = await fetch('/logs');
                const logs = await response.json();
                if (logs.length > 0) {
                    logContent.textContent += logs.join('\\n') + '\\n';
                    logContent.scrollTop = logContent.scrollHeight;
                }
            } catch (error) {
                console.error("Failed to fetch logs:", error);
            }
        }

        fetchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const playlistUrl = playlistUrlInput.value;
            selectedFormat = document.querySelector('input[name="format"]:checked').value;

            loading.classList.remove('hidden');
            playlistInfo.classList.add('hidden');
            progressList.innerHTML = '';
            statusContainer.classList.add('hidden');
            errorContainer.classList.add('hidden');
            resetContainer.classList.add('hidden');
            fetchBtn.disabled = true;

            try {
                const response = await fetch('/fetch_playlist', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: playlistUrl, format: selectedFormat }),
                });
                const data = await response.json();
                if (response.ok) {
                    loading.classList.add('hidden');
                    playlistInfo.classList.remove('hidden');
                    playlistTitle = data.playlist_title;
                    playlistTitleEl.textContent = playlistTitle;
                    fetchedSongs = data.songs;
                    // ### MODIFICATION ###: This line is now fixed
                    totalItemsSpan.textContent = fetchedSongs.length;
                    renderSongList(fetchedSongs);
                    if (fetchedSongs.length === 1) {
                        document.getElementById(`song-${fetchedSongs[0].id}`).checked = true;
                        updateSelectedCount();
                    }
                } else {
                    loading.classList.add('hidden');
                    errorText.textContent = data.message;
                    errorContainer.classList.remove('hidden');
                }
            } catch (error) {
                loading.classList.add('hidden');
                errorText.textContent = `Network error: ${error.message}`;
                errorContainer.classList.remove('hidden');
            } finally {
                fetchBtn.disabled = false;
            }
        });

        selectAllBtn.addEventListener('click', () => {
            const checkboxes = progressList.querySelectorAll('input[type="checkbox"]');
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            checkboxes.forEach(cb => cb.checked = !allChecked);
            updateSelectedCount();
            selectAllBtn.textContent = allChecked ? 'Select All' : 'Deselect All';
        });

        progressList.addEventListener('change', (e) => {
             if (e.target.type === 'checkbox') {
                updateSelectedCount();
             }
        });

        function updateSelectedCount() {
            const checkboxes = progressList.querySelectorAll('input[type="checkbox"]');
            const selectedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
            selectedCountSpan.textContent = selectedCount;
            
            const allChecked = checkboxes.length > 0 && selectedCount === checkboxes.length;
            selectAllBtn.textContent = allChecked ? 'Deselect All' : 'Select All';
        }

        downloadSelectedBtn.addEventListener('click', async () => {
            const selectedSongs = Array.from(progressList.querySelectorAll('input[type="checkbox"]:checked'))
                .map(cb => {
                    const songId = cb.id.replace('song-', '');
                    return fetchedSongs.find(s => s.id === songId);
                });

            if (selectedSongs.length === 0) {
                alert('Please select at least one song to download.');
                return;
            }
            
            logContent.textContent = '';
            
            setDownloadUIState(true);
            statusContainer.classList.remove('hidden');
            statusText.textContent = 'Starting download...';

            if (logPollingInterval) clearInterval(logPollingInterval);
            logPollingInterval = setInterval(fetchLogs, 2000);

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ songs: selectedSongs, playlist_title: playlistTitle, format: selectedFormat }),
                });

                if (response.ok) {
                    statusText.textContent = 'Download started. Fetching status...';
                    if (pollingInterval) clearInterval(pollingInterval);
                    pollingInterval = setInterval(pollStatus, 1500);
                } else {
                    const error = await response.json();
                    statusText.textContent = `Error: ${error.message}`;
                    setDownloadUIState(false);
                    if (logPollingInterval) clearInterval(logPollingInterval);
                }
            } catch (error) {
                statusText.textContent = `Network error: ${error.message}`;
                setDownloadUIState(false);
                if (logPollingInterval) clearInterval(logPollingInterval);
            }
        });

        function renderSongList(songs) {
            progressList.innerHTML = '';
            songs.forEach((item, index) => {
                const songItem = document.createElement('div');
                songItem.className = 'p-3 bg-slate-50 dark:bg-slate-700 rounded-lg flex items-center shadow-sm space-x-4 transition-all duration-300 hover:shadow-md';
                
                const videoId = item.id;
                const thumbnailUrl = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
                const placeholderUrl = 'https://placehold.co/48x48/e2e8f0/64748b?text=YT';
                const thumbnail = `<img src="${thumbnailUrl}" class="w-12 h-12 rounded-lg object-cover" alt="Thumbnail" onerror="this.onerror=null; this.src='${placeholderUrl}';">`;

                const uploader = item.uploader || 'Unknown Channel';
                
                songItem.innerHTML = `
                    <input type="checkbox" id="song-${item.id}" class="h-5 w-5 rounded-md text-indigo-600 focus:ring-indigo-500">
                    <span class="text-sm font-semibold text-slate-400 dark:text-slate-500 w-6 text-right">${index + 1}.</span>
                    ${thumbnail}
                    <div class="flex-1 min-w-0">
                        <div class="font-medium text-slate-700 dark:text-slate-200 truncate">${item.title}</div>
                        <div class="text-sm text-slate-500 dark:text-slate-400 truncate">${uploader}</div>
                    </div>
                `;
                progressList.appendChild(songItem);
            });
            updateSelectedCount();
        }

        async function pollStatus() {
            try {
                const response = await fetch('/status');
                const data = await response.json();

                if (data.status === 'finished' || data.status === 'error') {
                    clearInterval(pollingInterval);
                    clearInterval(logPollingInterval);
                    setDownloadUIState(false);
                    
                    statusContainer.className = 'p-4 rounded-lg mb-6 transition-all duration-300'; // Reset
                    if (data.status === 'finished') {
                        statusContainer.classList.add('bg-green-50', 'dark:bg-green-900', 'text-green-600', 'dark:text-green-300');
                        statusText.textContent = 'Download finished!';
                    } else {
                        statusContainer.classList.add('bg-red-50', 'dark:bg-red-900', 'text-red-600', 'dark:text-red-300');
                        statusText.textContent = `Download failed: ${data.error_message || 'Unknown error'}`;
                    }
                    resetContainer.classList.remove('hidden');
                    fetchLogs();
                } else if (data.status === 'downloading') {
                    statusText.textContent = `Downloading (${data.downloaded_items}/${data.total_items})...`;
                }

                totalItemsSpan.textContent = data.total_items;
                downloadedItemsSpan.textContent = data.downloaded_items;
                failedItemsSpan.textContent = data.failed_items;

                updateProgressList(data.results);
            } catch (error) {
                clearInterval(pollingInterval);
                clearInterval(logPollingInterval);
                setDownloadUIState(false);
                statusText.textContent = 'Error fetching status. Please try again.';
                resetContainer.classList.remove('hidden');
                console.error('Error polling status:', error);
            }
        }
        
        resetBtn.addEventListener('click', () => {
            playlistInfo.classList.add('hidden');
            resetContainer.classList.add('hidden');
            statusContainer.classList.add('hidden');
            logBtn.classList.add('hidden');
            errorContainer.classList.add('hidden');
            
            playlistUrlInput.value = '';
            
            totalItemsSpan.textContent = '0';
            downloadedItemsSpan.textContent = '0';
            failedItemsSpan.textContent = '0';
            
            progressList.innerHTML = '';
            logContent.textContent = '';
            
            fetchedSongs = [];
            playlistTitle = "";
            
            setDownloadUIState(false);
            fetchBtn.disabled = false;
            playlistUrlInput.disabled = false;
        });

        function updateProgressList(results) {
            progressList.innerHTML = '';
            results.forEach(item => {
                const progressItem = document.createElement('div');
                
                const videoId = item.id;
                const thumbnailUrl = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
                const placeholderUrl = 'https://placehold.co/48x48/e2e8f0/64748b?text=YT';
                const thumbnail = `<img src="${thumbnailUrl}" class="w-12 h-12 rounded-lg mr-4 object-cover" alt="Thumbnail" onerror="this.onerror=null; this.src='${placeholderUrl}';">`;
                
                const title = item.title;
                const uploader = item.uploader || 'Unknown Channel';
                const progress = item.progress || 0;
                const status = item.status;
                const order = item.order + 1;
                
                progressItem.className = 'p-4 rounded-lg shadow-sm flex items-center justify-between transition-all duration-300';
                let contentHTML = '';
                let bgColor = 'bg-slate-50 dark:bg-slate-700';
                
                if (status === 'finished') {
                    bgColor = 'bg-green-50 dark:bg-green-900';
                    contentHTML = `<div class="flex items-center min-w-0"><span class="text-sm font-semibold text-slate-400 dark:text-slate-500 mr-2 w-6 text-right">${order}.</span>${thumbnail}<div class="flex-1 ml-4 min-w-0"><div class="text-sm font-medium text-green-700 dark:text-green-300 truncate">${title}</div><div class="text-sm text-green-600 dark:text-green-400 truncate">${uploader}</div></div></div><span class="text-sm font-bold text-green-700 dark:text-green-300 ml-4 flex-shrink-0">Finished</span>`;
                } else if (status === 'error') {
                    bgColor = 'bg-red-50 dark:bg-red-900';
                    contentHTML = `<div class="flex items-center min-w-0"><span class="text-sm font-semibold text-slate-400 dark:text-slate-500 mr-2 w-6 text-right">${order}.</span>${thumbnail}<div class="flex-1 ml-4 min-w-0"><div class="text-sm font-medium text-red-700 dark:text-red-300 truncate">${title}</div><div class="text-sm text-red-600 dark:text-red-400 truncate">${uploader}</div></div></div><span class="text-sm font-bold text-red-700 dark:text-red-300 ml-4 flex-shrink-0">Failed</span>`;
                } else if (status === 'downloading') {
                    bgColor = 'bg-blue-50 dark:bg-blue-900';
                    // ### MODIFICATION ###: This typo is also fixed
                    contentHTML = `<div class="flex items-center w-full"><span class="text-sm font-semibold text-slate-400 dark:text-slate-500 mr-2 w-6 text-right">${order}.</span>${thumbnail}<div class="flex-1 ml-4 min-w-0"><div class="text-sm font-medium text-blue-700 dark:text-blue-300 truncate">${title}</div><div class="text-sm text-blue-600 dark:text-blue-400 truncate">${uploader}</div><div class="w-full h-2 bg-blue-200 dark:bg-blue-700 rounded-full mt-1"><div class="h-2 bg-blue-600 rounded-full transition-all duration-300 ease-out" style="width: ${progress}%"></div></div></div></div>`;
                } else { // pending
                    bgColor = 'bg-slate-50 dark:bg-slate-700';
                    contentHTML = `<div class="flex items-center min-w-0"><span class="text-sm font-semibold text-slate-400 dark:text-slate-500 mr-2 w-6 text-right">${order}.</span>${thumbnail}<div class="flex-1 ml-4 min-w-0"><div class="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">${title}</div><div class="text-sm text-slate-500 dark:text-slate-400 truncate">${uploader}</div></div></div><span class="text-sm font-bold text-slate-700 dark:text-slate-200 ml-4 flex-shrink-0">Pending</span>`;
                }
                
                progressItem.classList.add(...bgColor.split(' '));
                progressItem.innerHTML = contentHTML;
                progressList.appendChild(progressItem);
            });
        }
    </script>
</body>
</html>
"""

# --- Helper functions for download process ---
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def _download_single_song(song, playlist_folder, format_options, log_file_path):
    global DOWNLOAD_STATUS
    video_id = song['id']

    class MyLogger:
        def debug(self, msg):
            if 'Destination' not in msg:
                LOG_QUEUE.put(msg)
        def warning(self, msg): LOG_QUEUE.put(f"[WARNING] {msg}")
        def error(self, msg): LOG_QUEUE.put(f"[ERROR] {msg}")

    def progress_hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            if total_bytes > 0:
                progress = (downloaded_bytes / total_bytes) * 100
                with status_lock:
                    if video_id in DOWNLOAD_STATUS['results']:
                        DOWNLOAD_STATUS['results'][video_id]['progress'] = progress

    def postprocessor_hook(d):
        if d['status'] == 'finished':
            with status_lock:
                if video_id in DOWNLOAD_STATUS['results']:
                    item = DOWNLOAD_STATUS['results'][video_id]
                    if item['status'] != 'finished':
                        item['status'] = 'finished'
                        item['progress'] = 100.0
                        DOWNLOAD_STATUS['downloaded_items'] += 1
                        try:
                            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                                log_file.write(f"{item['title']}\n")
                        except Exception as e:
                            LOG_QUEUE.put(f"[ERROR] Could not write to log file: {e}")

    output_template = os.path.join(
        playlist_folder, 
        f"{song['order'] + 1:02d} - %(artist, 'Unknown Artist')s - %(title)s.%(ext)s"
    )

    ydl_opts = {
        'outtmpl': output_template,
        'writethumbnail': True,
        'ffmpeg_location': FFMPEG_PATH,
        'yesplaylist': False,
        'ignoreerrors': False,
        'progress_hooks': [progress_hook],
        'postprocessor_hooks': [postprocessor_hook],
        'logger': MyLogger(),
        'retries': 5,
        'fragment_retries': 5,
        'quiet': True,
        'extractor_args': {"youtube": {"player_client": ["default"]}},
        **format_options
    }

    try:
        with status_lock:
            if video_id in DOWNLOAD_STATUS['results']:
                DOWNLOAD_STATUS['results'][video_id]['status'] = 'downloading'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    except Exception as e:
        with status_lock:
            if video_id in DOWNLOAD_STATUS['results']:
                item = DOWNLOAD_STATUS['results'][video_id]
                if item['status'] != 'finished':
                    item['status'] = 'error'
                    item['error_message'] = str(e)
                    DOWNLOAD_STATUS['failed_items'] += 1
        LOG_QUEUE.put(f"Failed to download {song['title']}: {e}")

def download_songs_task(songs, playlist_title, format_type):
    global DOWNLOAD_STATUS
    
    try:
        music_dir = os.path.expanduser(r'~\Music')
        base_folder = os.path.join(music_dir, 'YTMusicDownloader')
        playlist_folder = os.path.join(base_folder, sanitize_filename(playlist_title))
        
        if not os.path.exists(playlist_folder):
            os.makedirs(playlist_folder)
    except Exception as e:
        with status_lock:
            DOWNLOAD_STATUS['status'] = 'error'
            DOWNLOAD_STATUS['error_message'] = f"Failed to create playlist folder: {e}"
        return

    log_file_path = os.path.join(playlist_folder, 'downloaded.txt')

    if format_type == 'mp3':
        format_options = {
            'format': 'bestaudio/best',
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'},
                {'key': 'EmbedThumbnail'},
            ]
        }
    else: # mp4
        format_options = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'postprocessors': [
                {'key': 'EmbedThumbnail'},
                {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'},
            ]
        }

    max_workers = 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_download_single_song, song, playlist_folder, format_options, log_file_path) for song in songs]
        concurrent.futures.wait(futures)

    with status_lock:
        DOWNLOAD_STATUS['status'] = 'finished'

# --- Flask Routes ---
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory(STATIC_DIR, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except Exception as e:
        LOG_QUEUE.put(f"[ERROR] Could not serve favicon: {e}")
        return "", 404

@app.route("/fetch_playlist", methods=["POST"])
def fetch_playlist():
    playlist_url = request.json.get("url")
    if not playlist_url:
        return jsonify({"message": "Playlist or Video URL is required."}), 400
    try:
        ydl_info_opts = {
            'quiet': True, 
            'extract_flat': True,
            'noplaylist': False,
            'extractor_args': {"youtube": {"player_client": ["default"]}}
        }
        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            if not info:
                raise Exception("yt-dlp could not extract any info. The URL might be invalid, private, or geo-restricted.")
            songs = []
            if 'entries' in info:
                playlist_title = info.get('title', 'Unknown Playlist')
                for index, entry in enumerate(info['entries']):
                    if entry and 'id' in entry and 'title' in entry:
                        songs.append({
                            'id': entry['id'],
                            'title': entry['title'],
                            'uploader': entry.get('uploader'),
                            'thumbnail': entry.get('thumbnail'),
                            'order': index
                        })
            else:
                playlist_title = info.get('title', 'Unknown Video')
                songs.append({
                    'id': info['id'],
                    'title': info['title'],
                    'uploader': info.get('uploader'),
                    'thumbnail': info.get('thumbnail'),
                    'order': 0
                })
        return jsonify({"playlist_title": playlist_title, "songs": songs}), 200
    except Exception as e:
        LOG_QUEUE.put(f"[ERROR] Failed to fetch info: {str(e)}")
        return jsonify({"message": f"Failed to fetch info. (Details: {str(e)})"}), 500

@app.route("/download", methods=["POST"])
def download_selected_songs():
    global DOWNLOAD_STATUS
    data = request.json
    selected_songs = data.get("songs")
    playlist_title = data.get("playlist_title", "Unknown_Playlist")
    selected_format = data.get("format", "mp3")
    if not selected_songs:
        return jsonify({"message": "No songs were selected for download."}), 400
    with status_lock:
        DOWNLOAD_STATUS = {
            'total_items': len(selected_songs),
            'downloaded_items': 0,
            'failed_items': 0,
            'status': 'downloading',
            'results': {song['id']: {
                'id': song['id'], 
                'title': song['title'],
                'uploader': song.get('uploader'),
                'status': 'pending',
                'progress': 0.0,
                'thumbnail': song.get('thumbnail'), 
                'order': song['order']
            } for song in selected_songs}
        }
    thread = threading.Thread(target=download_songs_task, args=(selected_songs, playlist_title, selected_format))
    thread.start()
    return jsonify({"message": "Download started successfully."}), 202

@app.route("/status")
def get_status():
    with status_lock:
        sorted_results = sorted(DOWNLOAD_STATUS.get('results', {}).values(), key=lambda x: x.get('order', 0))
        response_data = DOWNLOAD_STATUS.copy()
        response_data['results'] = sorted_results
        return jsonify(response_data)

@app.route("/logs")
def get_logs():
    logs = []
    while not LOG_QUEUE.empty():
        logs.append(LOG_QUEUE.get_nowait())
    return jsonify(logs)


if __name__ == "__main__":
    # --- All shortcut code has been removed ---
    
    try:
        music_dir = os.path.expanduser(r'~\Music')
        base_folder = os.path.join(music_dir, 'YTMusicDownloader')
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
    except Exception as e:
        print(f"Could not create download directory: {e}")
        
    if not os.path.exists(STATIC_DIR):
        os.makedirs(STATIC_DIR)
        print(f"Created static directory at {STATIC_DIR}")
        print(f"Please place your 'favicon.ico' file in this directory.")
    
    print("Starting server at http://127.0.0.1:5000")
    
    def open_browser():
        # Only open the browser if running as a bundled .exe
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            threading.Timer(1.0, lambda: webbrowser.open_new_tab('http://127.0.0.1:5000')).start()
        
    open_browser()
    
    serve(app, host='127.0.0.1', port=5000)