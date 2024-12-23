import sys
import asyncio
import aiohttp
import os
from pathlib import Path
import zendriver as zd
from urllib.parse import unquote
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QComboBox, QLineEdit, 
                            QPushButton, QProgressBar, QFileDialog, QCheckBox)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon

class DownloaderWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    url_not_found = pyqtSignal()

    def __init__(self, url, delay, output_dir, headless):
        super().__init__()
        self.url = url
        self.delay = delay
        self.output_dir = output_dir
        self.headless = headless

    def extract_song_title(self, download_url):
        try:
            filename = download_url.split('fname=')[-1]
            if filename.endswith('.m4a'):
                filename = filename[:-4]
            
            decoded_filename = unquote(filename)
            
            if '-' in decoded_filename:
                title, artist = decoded_filename.split('-', 1)
                formatted_title = f"{title.strip()} - {artist.strip()}"
            else:
                formatted_title = decoded_filename.strip()
                
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                formatted_title = formatted_title.replace(char, '_')
                
            return formatted_title or "spotisongdownloader_track"
        except Exception:
            return "spotisongdownloader_track"

    async def download_file(self, download_url, song_title):
        output_path = os.path.join(self.output_dir, f"{song_title}.m4a")
        
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
            max_attempts = 60
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
                song_title = self.extract_song_title(download_url)
                output_path = await self.download_file(download_url, song_title)
                self.finished.emit(f"Download complete: {output_path}")
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
            
        self.setMinimumWidth(500)
        
        self.default_music_dir = str(Path.home() / "Music")
        if not os.path.exists(self.default_music_dir):
            os.makedirs(self.default_music_dir)
        
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        url_layout = QHBoxLayout()
        url_label = QLabel("Track URL:")
        url_label.setFixedWidth(100)
        self.url_input = QLineEdit()
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        dir_layout = QHBoxLayout()
        dir_label = QLabel("Output Directory:")
        dir_label.setFixedWidth(100)
        self.dir_input = QLineEdit(self.default_music_dir)
        self.dir_button = QPushButton("Browse")
        self.dir_button.setFixedWidth(100)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.dir_button)
        self.dir_button.clicked.connect(self.select_directory)
        layout.addLayout(dir_layout)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        bottom_layout = QHBoxLayout()
        
        speed_layout = QHBoxLayout()
        speed_label = QLabel("Speed:")
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Fast", "Normal", "Slow"])
        self.speed_combo.setCurrentText("Fast")
        self.speed_combo.setFixedWidth(100)
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_combo)
        
        self.headless_checkbox = QCheckBox("Headless")
        self.headless_checkbox.setChecked(True)
        speed_layout.addWidget(self.headless_checkbox)
        
        bottom_layout.addLayout(speed_layout)
        bottom_layout.addStretch()
        
        self.download_button = QPushButton("Download")
        self.download_button.setFixedWidth(100)
        self.download_button.clicked.connect(self.button_clicked)
        bottom_layout.addWidget(self.download_button)
        
        layout.addLayout(bottom_layout)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.dir_input.setText(directory)

    def get_delay_seconds(self):
        mode = self.speed_combo.currentText()
        if mode == "Fast":
            return 1.5
        elif mode == "Normal":
            return 3
        else:
            return 6

    def handle_url_not_found(self):
        self.progress_bar.setValue(0)
        self.status_label.setText("URL not found. Please try again.")
        self.download_button.setText("Retry")
        self.download_button.setEnabled(True)

    def clear_form(self):
        self.url_input.clear()
        self.progress_bar.setValue(0)
        self.status_label.clear()
        self.download_button.setText("Download")

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

        if not output_dir:
            output_dir = self.default_music_dir
            self.dir_input.setText(output_dir)

        self.download_button.setEnabled(False)
        self.download_button.setText("Download")
        self.progress_bar.setValue(0)
        self.status_label.setText("Downloading...")

        self.worker = DownloaderWorker(
            url, 
            self.get_delay_seconds(), 
            output_dir,
            self.headless_checkbox.isChecked()
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.download_finished)
        self.worker.error.connect(self.download_error)
        self.worker.url_not_found.connect(self.handle_url_not_found)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def download_finished(self, message):
        self.status_label.setText(message)
        self.download_button.setEnabled(True)
        self.download_button.setText("Clear")

    def download_error(self, error_message):
        self.status_label.setText(error_message)
        self.download_button.setEnabled(True)
        self.download_button.setText("Retry")

def main():
    app = QApplication(sys.argv)
    window = SpotiSongDownloaderGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
