# NCR/core/downloader.py

from qgis.core import QgsTask, QgsMessageLog, Qgis
from qgis.PyQt.QtCore import QObject, pyqtSignal
import urllib.request

class DownloadTask(QgsTask):
    """
    Task QGIS per il download di un file in background.
    """
    download_complete = pyqtSignal(str, bool, str)
    download_progress = pyqtSignal(int)

    def __init__(self, url, dest_path, description):
        super().__init__(description, QgsTask.CanCancel)
        self.url = url
        self.dest_path = dest_path
        self.exception = None

    def run(self):
        """Esegue il download."""
        try:
            QgsMessageLog.logMessage(f"Avvio download da: {self.url}", "NCR-Downloader", Qgis.Info)
            req = urllib.request.Request(self.url, headers={'User-Agent': 'QGIS-NCR-Plugin/1.0'})
            with urllib.request.urlopen(req, timeout=600) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                block_size = 8192  # 8KB

                with open(self.dest_path, 'wb') as out_file:
                    while True:
                        if self.isCanceled():
                            return False
                        
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        
                        out_file.write(buffer)
                        downloaded += len(buffer)
                        
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.download_progress.emit(percent)
            return True
        except Exception as e:
            self.exception = e
            return False

    def finished(self, result):
        """Eseguito al termine del task."""
        self.download_complete.emit(self.dest_path, result, str(self.exception) if self.exception else "")