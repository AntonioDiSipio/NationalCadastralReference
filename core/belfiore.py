# NCR/core/belfiore.py

import os
import json
import urllib.request
from qgis.core import QgsMessageLog, Qgis

GITHUB_RAW_URL = "https://raw.githubusercontent.com/AntonioDiSipio/codici_comuni/refs/heads/main/comuni_belfiore.json"

def carica_dati_comuni_remote():
    """Scarica il file comuni_belfiore.json da GitHub e restituisce le mappe territoriali."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    cache_dir = os.path.join(base_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "comuni_belfiore_cache.json")

    data = []

    try:
        QgsMessageLog.logMessage("Download comuni_belfiore.json da GitHub in corso...", "NCR", Qgis.Info)
        req = urllib.request.Request(GITHUB_RAW_URL, headers={'User-Agent': 'QGIS-Plugin-NCR'})
        with urllib.request.urlopen(req, timeout=5) as response:
            raw_data = response.read().decode('utf-8')
            data = json.loads(raw_data)

        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(raw_data)

    except Exception as e:
        QgsMessageLog.logMessage(f"Impossibile scaricare da GitHub ({str(e)}). Uso cache...", "NCR", Qgis.Warning)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

    mappa_comuni, mappa_istat, mappa_provincia, mappa_regione, nome_to_belfiore = {}, {}, {}, {}, {}

    for item in data:
        codice = item.get("codice_belfiore")
        nome = item.get("nome")
        istat = item.get("codice_istat")
        prov = item.get("provincia")
        reg = item.get("regione")
        
        if codice:
            key = str(codice).strip().upper()
            if nome: mappa_comuni[key] = str(nome).strip()
            if nome: nome_to_belfiore[str(nome).strip().upper()] = key
            if istat is not None: mappa_istat[key] = str(istat).strip()
            if prov is not None and str(prov).lower() != "null": mappa_provincia[key] = str(prov).strip().upper()
            if reg: mappa_regione[key] = str(reg).strip()

    return mappa_comuni, mappa_istat, mappa_provincia, mappa_regione, nome_to_belfiore

# Inizializzazione globale all'import
MAPPA_COMUNI, MAPPA_ISTAT, MAPPA_PROVINCIA, MAPPA_REGIONE, NOME_TO_BELFIORE = carica_dati_comuni_remote()