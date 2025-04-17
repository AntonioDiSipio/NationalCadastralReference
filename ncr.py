from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QProgressDialog, QFileDialog
from qgis.utils import iface
from qgis.core import QgsProject, QgsField, Qgis, QgsMessageLog
import os
import re
from datetime import datetime
from codcomITA import mappa_codici_comuni

# === CONFIGURAZIONE ===
CAMPO_INPUT = "NATIONALCADASTRALREFERENCE"
CAMPI_OUTPUT = ["comune", "sezione", "foglio", "allegato", "sviluppo", "particella"]
PATTERN_NCR = r"^([A-Z0-9]{4})([_A-Z])([0-9]{4})([A-Z0-9]?)([A-Z0-9]?)\.(.+)$"

# === FUNZIONI UTILI ===
def verifica_layer_attivo():
    """Verifica che il layer attivo sia presente e valido."""
    layer = iface.activeLayer()
    if not layer:
        raise Exception("Nessun layer attivo trovato!")
    return layer

def parse_ncr(ref):
    """Parsa il riferimento catastale e restituisce un dizionario."""
    match = re.match(PATTERN_NCR, ref)
    if not match:
        return None
    codice = match.group(1)
    sezione = None if match.group(2) == "_" else match.group(2)
    foglio = match.group(3)
    allegato = match.group(4) if match.group(4) not in ["", "0"] else None
    sviluppo = match.group(5) if match.group(5) not in ["", "0"] else None
    particella = match.group(6)
    nome_comune = mappa_codici_comuni.get(codice, codice)
    return {
        "comune": nome_comune,
        "sezione": sezione,
        "foglio": foglio,
        "allegato": allegato,
        "sviluppo": sviluppo,
        "particella": particella
    }

# === INIZIALIZZAZIONE ===
layer = verifica_layer_attivo()
prov = layer.dataProvider()
campi_esistenti = [f.name().lower() for f in layer.fields()]
mappa_indici = {}

# === CREA CAMPI MANCANTI ===
nuovi = [QgsField(nome, QVariant.String) for nome in CAMPI_OUTPUT if nome.lower() not in campi_esistenti]
if nuovi:
    prov.addAttributes(nuovi)
    layer.updateFields()

# === INDICI CAMPI ===
for nome in CAMPI_OUTPUT:
    mappa_indici[nome] = layer.fields().lookupField(nome)

# === FEATURES ===
features = list(layer.getFeatures())
total = len(features)

progress = QProgressDialog("Estrazione in corso...", "Annulla", 0, total)
progress.setWindowTitle("Estrai dati catastali")
progress.setMinimumDuration(0)

valori_da_aggiornare = {}
righe_log = []

try:
    for i, feat in enumerate(features):
        if progress.wasCanceled():
            print("⚠️ Operazione annullata.")
            break

        ref = feat[CAMPO_INPUT]
        if not ref:
            continue

        parsed = parse_ncr(ref)
        if not parsed:
            righe_log.append(f"⚠️ Parsing fallito per ID {feat.id()}: {ref}")
            continue

        fid = feat.id()
        update = {}
        for campo, valore in parsed.items():
            idx = mappa_indici[campo]
            update[idx] = valore
        valori_da_aggiornare[fid] = update

        if salva_log:
            righe_log.append(f"ID {fid}: {ref} → {parsed}")

        if i % 10 == 0 or i == total - 1:  # Aggiorna la barra di progresso ogni 10 iterazioni
            progress.setValue(i + 1)

    progress.close()

    # === AGGIORNA IL LAYER IN MODO SICURO ===
    if not layer.isEditable() and not layer.startEditing():
        raise Exception("⚠️ Non riesco ad aprire il layer in modalità di editing.")

    prov.changeAttributeValues(valori_da_aggiornare)

    if not layer.commitChanges():
        raise Exception("⚠️ Errore nel salvataggio delle modifiche.")

    # === LOG ===
    if salva_log:
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(righe_log))
        QgsMessageLog.logMessage(f"Dati catastali aggiornati.\nLog: {log_filename}", "Script Catasto", Qgis.Info)
        print(f"✅ Completato! Log: {log_filename}")
    else:
        print("✅ Completato! Nessun log salvato.")

except Exception as e:
    print(f"Errore: {e}")
    progress.close()
