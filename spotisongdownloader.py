import sys
import asyncio
import aiohttp
import os
from pathlib import Path
import zendriver as zd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QComboBox, QLineEdit, 
                            QPushButton, QProgressBar, QFileDialog, QCheckBox,
                            QRadioButton, QGroupBox)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QCursor

class ImageDownloader(QThread):
    finished = pyqtSignal(bytes)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    async def download_image(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                if response.status == 200:
                    return await response.read()
        return None
        
    def run(self):
        image_data = asyncio.run(self.download_image())
        if image_data:
            self.finished.emit(image_data)

class TrackInfoFetcher(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    async def fetch_info(self):
        api_url = f"https://api.fabdl.com/spotify/get?url={self.url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception("Failed to fetch track information")
                    
    def run(self):
        try:
            result = asyncio.run(self.fetch_info())
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class DownloaderWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    url_not_found = pyqtSignal()

    def __init__(self, url, delay, output_dir, headless, track_info, filename_format):
        super().__init__()
        self.url = url
        self.delay = delay
        self.output_dir = output_dir
        self.headless = headless
        self.track_info = track_info
        self.filename_format = filename_format

    def format_filename(self):
        title = self.track_info['result']['name']
        artists = self.track_info['result']['artists']
        
        if self.filename_format == "title_artist":
            formatted = f"{title} - {artists}"
        else:
            formatted = f"{artists} - {title}"
            
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            formatted = formatted.replace(char, '_')
            
        return formatted

    async def download_file(self, download_url):
        filename = self.format_filename()
        output_path = os.path.join(self.output_dir, f"{filename}.m4a")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status != 200:
                    raise Exception("Failed to download file")
                
                file_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(output_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = 50 + int((downloaded / file_size) * 50)
                        self.progress.emit(progress)
        
        return output_path

    async def download_track(self):
        try:
            browser = await zd.start(headless=self.headless) 
            page = await browser.get("https://spotisongdownloader.to")
            
            await asyncio.sleep(self.delay)
            self.progress.emit(10)

            await page.evaluate(f"""
                document.querySelector("#id_url").value = "{self.url}";
                document.querySelector("#id_url").dispatchEvent(new Event('input', {{ bubbles: true }}));
            """)
            
            self.progress.emit(20)

            generate_link_button = await page.wait_for("a#download_btn")
            if generate_link_button:
                await generate_link_button.click()

            self.progress.emit(30)

            await page.wait_for("#qquality")
            await page.evaluate("""
                var select = document.getElementById('qquality');
                select.value = 'm4a';
                select.dispatchEvent(new Event('change', { bubbles: true }));
            """)

            self.progress.emit(40)

            download_url = None
            max_attempts = 30
            attempt = 0
            
            while attempt < max_attempts and not download_url:
                links = await page.evaluate("""
                    Array.from(document.getElementsByTagName('a')).map(a => a.href)
                """)
                
                for link in links:
                    if isinstance(link, str) and link.endswith('.m4a'):
                        download_url = link
                        break
                
                if not download_url:
                    await asyncio.sleep(0.5)
                    attempt += 1
                    progress = 40 + int((attempt / max_attempts) * 10)
                    self.progress.emit(progress)

            await browser.stop()

            if download_url:
                output_path = await self.download_file(download_url)
                self.finished.emit("Download complete!")
            else:
                self.url_not_found.emit()

        except Exception as e:
            self.error.emit(f"Error: {str(e)}")

    def run(self):
        asyncio.run(self.download_track())

class SpotiSongDownloaderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SpotiSongDownloader")
        
        icon_path = os.path.join(os.path.dirname(__file__), "icon.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.setFixedWidth(600)
        self.setFixedHeight(180)
        
        self.default_music_dir = str(Path.home() / "Music")
        if not os.path.exists(self.default_music_dir):
            os.makedirs(self.default_music_dir)
        
        self.track_info = None
        self.init_ui()

    def format_duration(self, duration_ms):
        total_seconds = int(duration_ms / 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.input_widget = QWidget()
        input_layout = QVBoxLayout(self.input_widget)
        input_layout.setSpacing(10)

        url_layout = QHBoxLayout()
        url_label = QLabel("Track URL:")
        url_label.setFixedWidth(100)
        self.url_input = QLineEdit()
        self.fetch_button = QPushButton("Fetch")
        self.fetch_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.fetch_button.setFixedWidth(100)
        self.fetch_button.clicked.connect(self.fetch_track_info)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.fetch_button)
        input_layout.addLayout(url_layout)

        dir_layout = QHBoxLayout()
        dir_label = QLabel("Output Directory:")
        dir_label.setFixedWidth(100)
        self.dir_input = QLineEdit(self.default_music_dir)
        self.dir_button = QPushButton("Browse")
        self.dir_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dir_button.setFixedWidth(100)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.dir_button)
        self.dir_button.clicked.connect(self.select_directory)
        input_layout.addLayout(dir_layout)

        settings_group = QGroupBox("Settings")
        settings_layout = QHBoxLayout(settings_group)
        settings_layout.setContentsMargins(10, 5, 10, 5)
        settings_layout.setSpacing(10)
        
        speed_widget = QWidget()
        speed_widget.setFixedWidth(130)
        speed_layout = QHBoxLayout(speed_widget)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(5)
        
        speed_label = QLabel("Speed:")
        speed_label.setFixedWidth(45)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Fast", "Normal", "Slow"])
        self.speed_combo.setCurrentText("Fast")
        self.speed_combo.setFixedHeight(20)
        
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_combo)
        settings_layout.addWidget(speed_widget)
        
        self.headless_checkbox = QCheckBox("Headless")
        self.headless_checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.headless_checkbox.setChecked(True)
        settings_layout.addWidget(self.headless_checkbox)
        
        format_widget = QWidget()
        format_layout = QHBoxLayout(format_widget)
        format_layout.setContentsMargins(0, 0, 0, 0)
        format_layout.setSpacing(8)
        
        format_label = QLabel("Filename Format:")
        self.format_title_artist = QRadioButton("Title - Artist")
        self.format_artist_title = QRadioButton("Artist - Title")
        self.format_title_artist.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.format_artist_title.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.format_title_artist.setChecked(True)
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_title_artist)
        format_layout.addWidget(self.format_artist_title)
        
        settings_layout.addWidget(format_widget)
        settings_layout.addStretch()
        
        input_layout.addWidget(settings_group)
        self.main_layout.addWidget(self.input_widget)

        self.track_widget = QWidget()
        self.track_widget.hide()
        track_layout = QHBoxLayout(self.track_widget)
        track_layout.setContentsMargins(0, 0, 0, 0)
        track_layout.setSpacing(10)

        cover_container = QWidget()
        cover_layout = QVBoxLayout(cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(100, 100)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_layout.addWidget(self.cover_label)
        track_layout.addWidget(cover_container)

        track_details_container = QWidget()
        track_details_layout = QVBoxLayout(track_details_container)
        track_details_layout.setContentsMargins(0, 0, 0, 0)
        track_details_layout.setSpacing(2)
        track_details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumWidth(400)
        
        self.artist_label = QLabel()
        self.artist_label.setStyleSheet("font-size: 12px;")
        self.artist_label.setWordWrap(True)
        self.artist_label.setMinimumWidth(400)

        self.duration_label = QLabel()
        self.duration_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.duration_label.setWordWrap(True)
        self.duration_label.setMinimumWidth(400)

        track_details_layout.addWidget(self.title_label)
        track_details_layout.addWidget(self.artist_label)
        track_details_layout.addWidget(self.duration_label)
        track_layout.addWidget(track_details_container, stretch=1)
        track_layout.addStretch()

        self.main_layout.addWidget(self.track_widget)

        self.download_button = QPushButton("Download")
        self.download_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.download_button.setFixedWidth(100)
        self.download_button.clicked.connect(self.button_clicked)
        self.download_button.hide()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_button.setFixedWidth(100)
        self.cancel_button.clicked.connect(self.cancel_clicked)
        self.cancel_button.hide()

        self.open_button = QPushButton("Open")
        self.open_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_button.setFixedWidth(100)
        self.open_button.clicked.connect(self.open_output_directory)
        self.open_button.hide()

        download_layout = QHBoxLayout()
        download_layout.addStretch()
        download_layout.addWidget(self.download_button)
        download_layout.addWidget(self.open_button)
        download_layout.addWidget(self.cancel_button)
        download_layout.addStretch()
        self.main_layout.addLayout(download_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.main_layout.addWidget(self.status_label)

    def fetch_track_info(self):
        url = self.url_input.text().strip()
        if not url:
            self.status_label.setText("Please enter a Track URL")
            return

        self.fetch_button.setEnabled(False)
        self.status_label.setText("Fetching track information...")
        
        self.fetcher = TrackInfoFetcher(url)
        self.fetcher.finished.connect(self.handle_track_info)
        self.fetcher.error.connect(self.handle_fetch_error)
        self.fetcher.start()

    def handle_track_info(self, info):
        self.track_info = info
        self.fetch_button.setEnabled(True)
        
        title = info['result']['name']
        artist = info['result']['artists']
        duration = self.format_duration(info['result']['duration_ms'])
        
        self.title_label.setText(title)
        self.artist_label.setText(artist)
        self.duration_label.setText(duration)
        
        image_url = info['result']['image']
        if '/ab67616d0000b273' in image_url:
            image_url = image_url
        else:
            base_url = image_url.split('/ab67616d')[0]
            image_url = f"{base_url}/ab67616d0000b273{image_url.split('/')[-1]}"
            
        self.image_downloader = ImageDownloader(image_url)
        self.image_downloader.finished.connect(self.update_cover_art)
        self.image_downloader.start()
        
        self.input_widget.hide()
        self.track_widget.show()
        self.download_button.show()
        self.cancel_button.show()
        self.status_label.clear()
        
        self.adjustWindowHeight()

    def adjustWindowHeight(self):
        title_height = self.title_label.sizeHint().height()
        artist_height = self.artist_label.sizeHint().height()
        
        base_height = 180
        additional_height = max(0, (title_height + artist_height) - 40)
        
        new_height = min(300, base_height + additional_height)
        self.setFixedHeight(int(new_height))

    def update_cover_art(self, image_data):
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        scaled_pixmap = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.cover_label.setPixmap(scaled_pixmap)

    def handle_fetch_error(self, error):
        self.fetch_button.setEnabled(True)
        self.status_label.setText(f"Error fetching track info: {error}")

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.dir_input.setText(directory)

    def open_output_directory(self):
        output_dir = self.dir_input.text().strip() or self.default_music_dir
        os.startfile(output_dir)
                
    def get_delay_seconds(self):
        mode = self.speed_combo.currentText()
        if mode == "Fast":
            return 1.5
        elif mode == "Normal":
            return 3
        else:
            return 6

    def cancel_clicked(self):
        self.track_widget.hide()
        self.input_widget.show()
        self.download_button.hide()
        self.cancel_button.hide()
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        self.status_label.clear()
        self.track_info = None
        self.fetch_button.setEnabled(True)
        self.setFixedHeight(180)

    def handle_url_not_found(self):
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText("URL not found. Please try again.")
        self.download_button.setText("Retry")
        self.download_button.show()
        self.cancel_button.show()
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def clear_form(self):
        self.url_input.clear()
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        self.status_label.clear()
        self.download_button.setText("Download")
        self.download_button.hide()
        self.cancel_button.hide()
        self.open_button.hide()
        self.track_widget.hide()
        self.input_widget.show()
        self.track_info = None

    def button_clicked(self):
        if self.download_button.text() == "Clear":
            self.clear_form()
        else:
            self.start_download()

    def start_download(self):
        url = self.url_input.text().strip()
        output_dir = self.dir_input.text().strip()

        if not url:
            self.status_label.setText("Please enter a Track URL")
            return

        if not self.track_info:
            self.status_label.setText("Please fetch track information first")
            return

        if not output_dir:
            output_dir = self.default_music_dir
            self.dir_input.setText(output_dir)

        self.download_button.hide()
        self.cancel_button.hide()
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.status_label.setText("Downloading...")

        filename_format = "title_artist" if self.format_title_artist.isChecked() else "artist_title"

        self.worker = DownloaderWorker(
            url, 
            self.get_delay_seconds(), 
            output_dir,
            self.headless_checkbox.isChecked(),
            self.track_info,
            filename_format
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.download_finished)
        self.worker.error.connect(self.download_error)
        self.worker.url_not_found.connect(self.handle_url_not_found)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def download_finished(self, message):
        self.progress_bar.hide()
        self.status_label.setText(message)
        self.download_button.setText("Clear")
        self.download_button.show()
        self.open_button.show()
        self.cancel_button.hide()
        self.download_button.setEnabled(True)

    def download_error(self, error_message):
        self.progress_bar.hide()
        self.status_label.setText(error_message)
        self.download_button.setText("Retry")
        self.download_button.show()
        self.cancel_button.show()
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    window = SpotiSongDownloaderGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
