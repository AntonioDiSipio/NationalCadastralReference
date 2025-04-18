from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import Qgis
import os

class NCRPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.action = QAction(QIcon(icon_path), "Estrai dati catastali", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("NCR", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("NCR", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        try:
            from .NCR import main
            main()
        except Exception as e:
            QMessageBox.critical(None, "Errore plugin NCR", str(e))
