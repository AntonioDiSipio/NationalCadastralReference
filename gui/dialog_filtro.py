# NCR/gui/dialog_filtro.py

import os
import io
import zipfile 
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCompleter,
                             QComboBox, QLineEdit, QPushButton, QFormLayout, 
                             QRadioButton, QFileDialog, QGroupBox, QLabel, QMessageBox, QButtonGroup)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsMessageLog, Qgis, QgsApplication, QgsTask
from qgis.utils import iface

from ..core.constants import DATASETS_REGIONI, BASE_URL_AE
from ..core.downloader import DownloadTask

class DialogFiltroCatastoAvanzato(QDialog):
    def __init__(self, record_estratta, layer_destinazione_disponibili, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NCR - Selezione e Filtro Particelle Catastali")
        self.resize(560, 640)
        
        self.records = record_estratta
        self.layer_destinazione_disponibili = layer_destinazione_disponibili
        
        layout = QVBoxLayout()

        # Raggruppa i radio button per renderli mutuamente esclusivi
        self.sorgente_button_group = QButtonGroup(self)
        self.sorgente_button_group.setExclusive(True)
        self.download_task = None


        # =====================================================================
        # === SEZIONE 1: SORGENTE DATI (Modulo A vs Modulo B) ===
        # =====================================================================
        box_sorgente = QGroupBox("Sorgente Dati")
        layout_sorgente = QVBoxLayout()

        self.radio_modulo_a = QRadioButton("Modulo A: Download Bulk da Agenzia delle Entrate (Regione -> Comune)")
        self.radio_modulo_a.setChecked(True)

        form_mod_a = QFormLayout()
        
        # Layout riga Regione + Pulsante Download
        regione_layout = QHBoxLayout()
        self.combo_regione = QComboBox()
        for nome_display, zip_filename in DATASETS_REGIONI.items():
            self.combo_regione.addItem(nome_display, zip_filename)
            
        self.btn_download_regione = QPushButton("⬇️ Scarica Regione")
        self.btn_download_regione.clicked.connect(self.avvia_download_regione)
        regione_layout.addWidget(self.combo_regione)
        regione_layout.addWidget(self.btn_download_regione)

        self.combo_provincia = QComboBox()
        self.combo_comune_bulk = QComboBox()
        # Rende il QComboBox ricercabile
        self.combo_comune_bulk.setEditable(True)
        self.combo_comune_bulk.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.combo_comune_bulk.setCompleter(completer)

        form_mod_a.addRow("1. Seleziona Regione:", regione_layout)
        form_mod_a.addRow("2. Provincia:", self.combo_provincia)
        form_mod_a.addRow("3. Comune da estrarre:", self.combo_comune_bulk)

        layout_sorgente.addWidget(self.radio_modulo_a)
        layout_sorgente.addLayout(form_mod_a)
        self.sorgente_button_group.addButton(self.radio_modulo_a)

        box_sorgente.setLayout(layout_sorgente)
        layout.addWidget(box_sorgente)

        self.radio_modulo_a.toggled.connect(self.gestisci_toggle_sorgente)

        # =====================================================================
        # === SEZIONE 2: FILTRI CATASTALI DI DETTAGLIO ===
        # =====================================================================
        box_filtri = QGroupBox("Filtri di dettaglio (Opzionali)")
        self.radio_modulo_b = QRadioButton("Modulo B: Usa Layer vettoriale attivo in QGIS (WFS/Canvas)")
        form_filtri = QFormLayout()
        
        self.combo_comune = QComboBox()
        self.combo_sezione = QComboBox()
        self.combo_foglio = QComboBox()
        self.combo_allegato = QComboBox()
        self.combo_sviluppo = QComboBox()
        self.input_particella = QLineEdit()
        self.input_particella.setPlaceholderText("Es. 101 (vuoto per tutte)")

        form_filtri.addRow(self.radio_modulo_b)
        self.sorgente_button_group.addButton(self.radio_modulo_b)
        form_filtri.addRow("Comune (Filtro):", self.combo_comune)
        form_filtri.addRow("Sezione:", self.combo_sezione)
        form_filtri.addRow("Foglio:", self.combo_foglio)
        form_filtri.addRow("Allegato:", self.combo_allegato)
        form_filtri.addRow("Sviluppo:", self.combo_sviluppo)
        form_filtri.addRow("Particella:", self.input_particella)

        box_filtri.setLayout(form_filtri)
        layout.addWidget(box_filtri)

        self.radio_modulo_b.toggled.connect(self.gestisci_toggle_sorgente)

        # =====================================================================
        # === SEZIONE 3: DESTINAZIONE OUTPUT ===
        # =====================================================================
        box_output = QGroupBox("Destinazione Output")
        form_out = QFormLayout()

        self.radio_nuovo = QRadioButton("Esporta su GeoPackage (vuoto per layer temporaneo):")
        self.radio_aggiorna = QRadioButton("Aggiorna/Unisci a layer esistente in QGIS:")
        self.radio_nuovo.setChecked(True)

        gpkg_layout = QHBoxLayout()
        self.input_gpkg_path = QLineEdit()
        self.input_gpkg_path.setPlaceholderText("Percorso file GeoPackage...")
        self.btn_browse_gpkg = QPushButton("Sfoglia...")
        self.btn_browse_gpkg.clicked.connect(self.seleziona_file_gpkg)
        gpkg_layout.addWidget(self.input_gpkg_path)
        gpkg_layout.addWidget(self.btn_browse_gpkg)

        self.combo_layer_target = QComboBox()
        self.combo_layer_target.setEnabled(False)

        if self.layer_destinazione_disponibili:
            for lyr in self.layer_destinazione_disponibili:
                self.combo_layer_target.addItem(lyr.name(), lyr)
        else:
            self.radio_aggiorna.setEnabled(False)
            self.combo_layer_target.addItem("Nessun layer idoneo trovato", None)

        self.radio_nuovo.toggled.connect(self.gestisci_toggle_output)

        form_out.addRow(self.radio_nuovo)
        form_out.addRow("File GPKG:", gpkg_layout)
        form_out.addRow(self.radio_aggiorna, self.combo_layer_target)

        box_output.setLayout(form_out)
        layout.addWidget(box_output)

        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Estrai e Salva")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Annulla")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Signals
        self.combo_regione.currentIndexChanged.connect(self.aggiorna_province_bulk)
        self.combo_provincia.currentIndexChanged.connect(self.aggiorna_comuni_bulk)

        self.combo_comune.currentIndexChanged.connect(self.aggiorna_sezioni)
        self.combo_sezione.currentIndexChanged.connect(self.aggiorna_fogli)
        self.combo_foglio.currentIndexChanged.connect(self.aggiorna_allegati)
        self.combo_allegato.currentIndexChanged.connect(self.aggiorna_sviluppi)

        self.popola_comuni()
        self.aggiorna_province_bulk()
        self.combo_comune_bulk.completer().setModel(self.combo_comune_bulk.model())
        self.gestisci_toggle_sorgente()

    def gestisci_toggle_sorgente(self):
        is_a = self.radio_modulo_a.isChecked()

        # Se l'utente sta provando a selezionare il Modulo B, controlla subito il layer attivo
        if not is_a:
            active_layer = iface.activeLayer()
            if not active_layer or active_layer.name() != "CP:CadastralParcel":
                QMessageBox.critical(self, "Errore Modulo B", "Per usare il Modulo B, è necessario selezionare il layer WFS dell'Agenzia delle Entrate (CP:CadastralParcel) prima di aprire questo pannello.")
                self.radio_modulo_a.setChecked(True) # Forza il ritorno al Modulo A
                return

        self.combo_regione.setEnabled(is_a)
        self.btn_download_regione.setEnabled(is_a)
        self.combo_provincia.setEnabled(is_a)
        self.combo_comune_bulk.setEnabled(is_a)

        # Abilita/disabilita i filtri di dettaglio del Modulo B
        self.combo_comune.setEnabled(not is_a)
        self.combo_sezione.setEnabled(not is_a)
        self.combo_foglio.setEnabled(not is_a)
        self.combo_allegato.setEnabled(not is_a)
        self.combo_sviluppo.setEnabled(not is_a)
        self.input_particella.setEnabled(not is_a)

        # Abilita/disabilita la sezione output in base alla selezione
        # La sezione output è sempre attiva, ma i suoi controlli interni
        # vengono gestiti dal loro toggle.
        self.radio_nuovo.setEnabled(True)
        self.radio_aggiorna.setEnabled(bool(self.layer_destinazione_disponibili))

    def gestisci_toggle_output(self, checked):
        self.input_gpkg_path.setEnabled(checked)
        self.btn_browse_gpkg.setEnabled(checked)
        self.combo_layer_target.setEnabled(not checked)

    def _get_cache_dir(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        cache_dir = os.path.join(base_dir, "cache_downloads")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def avvia_download_regione(self):
        zip_filename = self.combo_regione.currentData()
        regione_nome = self.combo_regione.currentText()
        if not zip_filename: return

        cache_dir = self._get_cache_dir()
        self.file_zip_dest = os.path.join(cache_dir, zip_filename)

        base_url = BASE_URL_AE if BASE_URL_AE.endswith("=") else f"{BASE_URL_AE}"
        url = f"{base_url}{zip_filename}"

        self.btn_download_regione.setEnabled(False)
        self.btn_download_regione.setText("Download in corso...")

        # Crea e avvia il task di download in background
        self.download_task = DownloadTask(url, self.file_zip_dest, f"Download di {regione_nome}")
        self.download_task.download_progress.connect(self.aggiorna_progresso_download)
        self.download_task.download_complete.connect(self.fine_download_regione)
        
        QgsApplication.taskManager().addTask(self.download_task)
        iface.messageBar().pushMessage("Download", f"Download di {regione_nome} avviato in background.", level=Qgis.Info, duration=5)

    def aggiorna_progresso_download(self, percent):
        iface.messageBar().pushMessage("Download", f"Scaricamento in corso: {percent}%", level=Qgis.Info, duration=1)

    def fine_download_regione(self, dest_path, success, error_message):
        self.btn_download_regione.setEnabled(True)
        self.btn_download_regione.setText("⬇️ Scarica Regione")

        if success:
            QMessageBox.information(self, "Download Completato", f"Dataset scaricato con successo in:\n{dest_path}")
            self.aggiorna_province_bulk()
        else:
            if "canceled" not in error_message.lower():
                QMessageBox.critical(self, "Errore Download", f"Impossibile scaricare l'archivio.\n\nErrore: {error_message}")
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except OSError:
                    pass
        self.download_task = None

    def aggiorna_province_bulk(self):
        zip_filename = self.combo_regione.currentData()
        zip_path = os.path.join(self._get_cache_dir(), zip_filename) if zip_filename else ""
        
        self.combo_provincia.blockSignals(True)
        self.combo_provincia.clear()

        province_trovate = set()

        if zip_path and os.path.exists(zip_path):
            try:
                with zipfile.ZipFile(zip_path, 'r') as main_zip:
                    for f in main_zip.namelist():
                        nome_base = os.path.basename(f)
                        if nome_base.lower().endswith('.zip'):
                            prov_code = nome_base[:-4].upper()
                            if len(prov_code) == 2 and prov_code.isalpha():
                                province_trovate.add(prov_code)
            except Exception as e:
                QgsMessageLog.logMessage(f"Errore lettura ZIP regionale: {str(e)}", "NCR", Qgis.Warning)

        if province_trovate:
            self.combo_provincia.addItem("--- TUTTE LE PROVINCE ---", "ALL")
            for p in sorted(list(province_trovate)):
                self.combo_provincia.addItem(f"Provincia di {p}", p)
        else:
            self.combo_provincia.addItem("--- Clicca 'Scarica Regione' ---", None)

        self.combo_provincia.blockSignals(False)
        self.aggiorna_comuni_bulk()

    def aggiorna_comuni_bulk(self):
        zip_filename = self.combo_regione.currentData()
        provincia_sel = self.combo_provincia.currentData()
        zip_path = os.path.join(self._get_cache_dir(), zip_filename) if zip_filename else ""

        self.combo_comune_bulk.blockSignals(True)
        self.combo_comune_bulk.clear()

        comuni_trovati = set()

        if zip_path and os.path.exists(zip_path):
            try:
                with zipfile.ZipFile(zip_path, 'r') as main_zip:
                    provincia_zips = [f for f in main_zip.namelist() if f.lower().endswith('.zip')]
                    
                    for prov_file in provincia_zips:
                        prov_code = os.path.basename(prov_file)[:-4].upper()
                        
                        if provincia_sel and provincia_sel not in ["ALL", None] and prov_code != provincia_sel:
                            continue

                        prov_bytes = main_zip.read(prov_file)
                        with zipfile.ZipFile(io.BytesIO(prov_bytes)) as prov_zip:
                            for comune_file in prov_zip.namelist():
                                if comune_file.lower().endswith('.zip'):
                                    nome_clean = os.path.basename(comune_file).replace('.zip', '').replace('.ZIP', '')
                                    parti = nome_clean.split('_')
                                    codice_belfiore = parti[0] if len(parti[0]) == 4 else nome_clean
                                    nome_comune_leggibile = " ".join(parti[1:]) if len(parti) > 1 else nome_clean
                                    label_display = f"{nome_comune_leggibile} ({codice_belfiore})" if len(parti) > 1 else nome_clean
                                    
                                    comuni_trovati.add((label_display, codice_belfiore))

                lista_ordinata = sorted(list(comuni_trovati), key=lambda x: x[0])
                for label, cod in lista_ordinata:
                    self.combo_comune_bulk.addItem(label, cod)

            except Exception as e:
                QgsMessageLog.logMessage(f"Errore scansione ricorsiva comuni: {str(e)}", "NCR", Qgis.Warning)

        if self.combo_comune_bulk.count() == 0:
            if not os.path.exists(zip_path):
                self.combo_comune_bulk.addItem("--- Scarica prima la Regione ---", None)
            else:
                self.combo_comune_bulk.addItem("--- Nessun comune trovato nello ZIP ---", None)

        self.combo_comune_bulk.blockSignals(False)
        # Aggiorna il modello del completer dopo aver popolato la combobox
        if self.combo_comune_bulk.completer():
            self.combo_comune_bulk.completer().setModel(self.combo_comune_bulk.model())

    def seleziona_file_gpkg(self):
        parti_nome = []
        if self.radio_modulo_a.isChecked():
            # Logica per Modulo A
            label_comune = self.combo_comune_bulk.currentText()
            nome_pulito = label_comune.split('(')[0].strip() if '(' in label_comune else label_comune
            if nome_pulito and "---" not in nome_pulito:
                parti_nome.append(nome_pulito.replace(" ", "_"))
        else:
            # Logica per Modulo B (esistente)
            comune = self.combo_comune.currentData()
            if comune: parti_nome.append(str(comune).replace(" ", "_").replace("'", ""))
            foglio = self.combo_foglio.currentData()
            if foglio: parti_nome.append(f"F{foglio}")
            particella = self.input_particella.text().strip()
            if particella: parti_nome.append(f"P{particella}")
            
        nome_suggerito = "_".join(parti_nome) if parti_nome else "Estratto_Catasto"
        nome_suggerito += ".gpkg"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Seleziona percorso GeoPackage", nome_suggerito, "GeoPackage (*.gpkg)"
        )
        if file_path:
            if not file_path.lower().endswith(".gpkg"): file_path += ".gpkg"
            self.input_gpkg_path.setText(file_path)

    def popola_comuni(self):
        self.combo_comune.blockSignals(True)
        self.combo_comune.clear()
        self.combo_comune.addItem("--- TUTTI I COMUNI ---", None)
        for c in sorted(list(set(r["comune"] for r in self.records if r.get("comune")))):
            self.combo_comune.addItem(c, c)
        self.combo_comune.blockSignals(False)
        self.aggiorna_sezioni()

    def aggiorna_sezioni(self):
        c_sel = self.combo_comune.currentData()
        filtrati = [r for r in self.records if not c_sel or r.get("comune") == c_sel]
        self.combo_sezione.blockSignals(True)
        self.combo_sezione.clear()
        self.combo_sezione.addItem("--- TUTTE LE SEZIONI ---", None)
        for s in sorted(list(set(r["sezione"] for r in filtrati if r.get("sezione")))):
            self.combo_sezione.addItem(f"Sezione {s}", s)
        self.combo_sezione.blockSignals(False)
        self.aggiorna_fogli()

    def aggiorna_fogli(self):
        c_sel, s_sel = self.combo_comune.currentData(), self.combo_sezione.currentData()
        filtrati = [r for r in self.records if (not c_sel or r.get("comune") == c_sel) and (not s_sel or r.get("sezione") == s_sel)]
        self.combo_foglio.blockSignals(True)
        self.combo_foglio.clear()
        self.combo_foglio.addItem("--- TUTTI I FOGLI ---", None)
        for f in sorted(list(set(r["foglio"] for r in filtrati if r.get("foglio"))), key=lambda x: int(x) if str(x).isdigit() else 9999):
            self.combo_foglio.addItem(f"Foglio {f}", f)
        self.combo_foglio.blockSignals(False)
        self.aggiorna_allegati()

    def aggiorna_allegati(self):
        c_sel, s_sel, f_sel = self.combo_comune.currentData(), self.combo_sezione.currentData(), self.combo_foglio.currentData()
        filtrati = [r for r in self.records if (not c_sel or r.get("comune") == c_sel) and (not s_sel or r.get("sezione") == s_sel) and (not f_sel or r.get("foglio") == f_sel)]
        self.combo_allegato.blockSignals(True)
        self.combo_allegato.clear()
        self.combo_allegato.addItem("--- TUTTI GLI ALLEGATI ---", None)
        for a in sorted(list(set(r["allegato"] for r in filtrati if r.get("allegato")))):
            self.combo_allegato.addItem(f"Allegato {a}", a)
        self.combo_allegato.blockSignals(False)
        self.aggiorna_sviluppi()

    def aggiorna_sviluppi(self):
        c_sel, s_sel, f_sel, a_sel = self.combo_comune.currentData(), self.combo_sezione.currentData(), self.combo_foglio.currentData(), self.combo_allegato.currentData()
        filtrati = [r for r in self.records if (not c_sel or r.get("comune") == c_sel) and (not s_sel or r.get("sezione") == s_sel) and (not f_sel or r.get("foglio") == f_sel) and (not a_sel or r.get("allegato") == a_sel)]
        self.combo_sviluppo.blockSignals(True)
        self.combo_sviluppo.clear()
        self.combo_sviluppo.addItem("--- TUTTI GLI SVILUPPI ---", None)
        for sv in sorted(list(set(r["sviluppo"] for r in filtrati if r.get("sviluppo")))):
            self.combo_sviluppo.addItem(f"Sviluppo {sv}", sv)
        self.combo_sviluppo.blockSignals(False)

    def get_sorgente_info(self):
        if self.radio_modulo_a.isChecked():
            # Gestisce la selezione da un QComboBox editabile
            testo_selezionato = self.combo_comune_bulk.currentText()
            idx = self.combo_comune_bulk.findText(testo_selezionato, Qt.MatchFlag.MatchFixedString)
            if idx >= 0:
                codice_comune = self.combo_comune_bulk.itemData(idx)
                label_comune = self.combo_comune_bulk.itemText(idx)
            else: # Fallback se l'utente ha scritto qualcosa di non valido
                codice_comune, label_comune = None, ""
            
            nome_pulito = label_comune.split('(')[0].strip() if '(' in label_comune else label_comune
            nome_layer_formatted = f"{codice_comune} - {nome_pulito}" if codice_comune else nome_pulito

            return {
                "tipo": "MODULO_A",
                "zip_filename": self.combo_regione.currentData(),
                "codice_comune": codice_comune,
                "nome_layer": nome_layer_formatted
            }
        else:
            return {"tipo": "MODULO_B"}

    def get_filtri(self):
        return {
            "comune": self.combo_comune.currentData(),
            "sezione": self.combo_sezione.currentData(),
            "foglio": self.combo_foglio.currentData(),
            "allegato": self.combo_allegato.currentData(),
            "sviluppo": self.combo_sviluppo.currentData(),
            "particella": self.input_particella.text().strip() if self.input_particella.text().strip() else None,
            "gpkg_path": self.input_gpkg_path.text().strip() if self.radio_nuovo.isChecked() else None,
            "target_layer": self.combo_layer_target.currentData() if self.radio_aggiorna.isChecked() else None
        }