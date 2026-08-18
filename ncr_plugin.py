# NCR/ncr_plugin.py

import os
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtGui import QAction, QIcon # noqa
from qgis.core import Qgis, QgsMessageLog, QgsVectorLayer, NULL
from qgis.utils import iface

from .core.parser import parse_ncr, is_riga_spuria
from .gui.dialog_filtro import DialogFiltroCatastoAvanzato
from .processing.extractor_feature import ottieni_layer_memoria_esistenti, esegui_estrazione
from .processing.extractor_gml import assicura_download_regione, costruisci_layer_da_zip_regionale

class NCRPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.action = QAction(QIcon(icon_path), "Estrai dati catastali NCR", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("NCR", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("NCR", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        try:
            source_layer = None
            record_estratta = []

            active_lyr = self.iface.activeLayer()
            try:
                if active_lyr and isinstance(active_lyr, QgsVectorLayer):
                    source_layer = active_lyr
                    # Cerca il campo di input in modo flessibile (una sola volta)
                    fields = source_layer.fields()
                    idx_inp = -1
                    for fld_name in ["INSPIREID_LOCALID", "inspireid_localid"]:
                        idx_inp = fields.lookupField(fld_name)
                        if idx_inp != -1: break

                    for feat in source_layer.getFeatures():
                        if is_riga_spuria(feat): continue
                        
                        ref = feat[idx_inp] if idx_inp != -1 else None
                        p = parse_ncr(ref)
                        if p and p.get('is_valid'): record_estratta.append(p)
            except Exception as e:
                QgsMessageLog.logMessage(f"Errore durante la pre-scansione del layer: {e}", "NCR", Qgis.Warning)

            layers_target = ottieni_layer_memoria_esistenti(source_layer.id() if source_layer else "")
            dialog = DialogFiltroCatastoAvanzato(record_estratta, layers_target, self.iface.mainWindow())
            
            if dialog.exec() == 1:
                sorgente_info = dialog.get_sorgente_info()
                filtri = dialog.get_filtri()

                if sorgente_info["tipo"] == "MODULO_A":
                    zip_filename = sorgente_info["zip_filename"]
                    codice_comune = sorgente_info["codice_comune"]
                    nome_layer = sorgente_info.get("nome_layer")

                    if not codice_comune or "---" in str(codice_comune):
                        raise Exception("Selezionare un Comune valido per il Modulo A!")

                    gpkg_path = filtri.get("gpkg_path")
                    file_zip_regione = assicura_download_regione(zip_filename)
                    # MODULO A: Crea il layer di base e si ferma.
                    # L'utente potrà poi usare il Modulo B su questo layer.
                    costruisci_layer_da_zip_regionale(file_zip_regione, codice_comune, nome_layer, gpkg_path)
                    QMessageBox.information(self.iface.mainWindow(), "Modulo A Completato", f"Layer '{nome_layer}' creato con successo.\nOra puoi usare il Modulo B su questo layer per estrarre e filtrare le particelle.")

                elif sorgente_info["tipo"] == "MODULO_B":
                    # MODULO B: Lavora sul layer attivo.
                    active_layer = self.iface.activeLayer()
                    if not active_layer or not isinstance(active_layer, QgsVectorLayer):
                        raise Exception("MODULO B: Nessun layer vettoriale/WFS selezionato in QGIS. Selezionare prima il layer attivo a schermo.")
                    esegui_estrazione(active_layer, filtri)

        except Exception as e:
            import traceback
            messaggio_errore = f"Si è verificato un errore: {str(e)}"
            QgsMessageLog.logMessage(f"{messaggio_errore}\n{traceback.format_exc()}", "NCR", Qgis.MessageLevel.Critical)
            QMessageBox.critical(self.iface.mainWindow(), "Errore Plugin NCR", messaggio_errore)