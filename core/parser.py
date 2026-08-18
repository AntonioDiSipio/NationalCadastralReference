import re
from typing import Dict, Any
from qgis.core import NULL, QgsMessageLog, Qgis
from .belfiore import MAPPA_COMUNI, MAPPA_ISTAT, MAPPA_PROVINCIA, MAPPA_REGIONE

# Regex per la validazione e il parsing della stringa catastale.
# Supporta sia il formato INSPIRE (con prefisso e underscore) sia quello classico.
MAIN_PATTERN = re.compile(
    r"^(?:IT\.AGE\.PLA\.)?([A-Z0-9]{4})[_]?([A-Z_])?([0-9]{4,6})([A-Z0-9]{2})?\.(.+)$"
)

# Regex per i vari tipi di particella
PARTICELLA_ORDINARIA = re.compile(r"^[0-9]{1,5}$") # Particelle numeriche
PARTICELLA_SPECIALE = re.compile(r"^[A-Z0-9]+$") # Particelle alfanumeriche (es. X1, ACQUA001)
PARTICELLA_TAVOLARE_FRAZIONATA = re.compile(r"^([0-9]{1,4})/([0-9]{1,4})$")
PARTICELLA_TAVOLARE_EDIFICIALE_FRAZIONATA = re.compile(r"^\.([0-9]{1,4})/([0-9]{1,4})$")
PARTICELLA_TAVOLARE_EDIFICIALE = re.compile(r"^\.([0-9]{1,4})$")

RIGA_SPURIA_ESATTA = "A001_000100.ACQUA001"

def is_riga_spuria(feat):
    """Verifica se la feature contiene la combinazione spuria A001_000100.ACQUA001."""
    for val in feat.attributes():
        if val and val != NULL:
            val_str = str(val).upper().strip()
            if RIGA_SPURIA_ESATTA in val_str or val_str == RIGA_SPURIA_ESATTA:
                return True
    return False

def parse_ncr(code: str) -> Dict[str, Any]:
    """
    Esegue il parsing e la validazione di una stringa "National Cadastral Reference"
    secondo lo standard INSPIRE italiano.

    Args:
        code: La stringa del riferimento catastale da analizzare.

    Returns:
        Un dizionario contenente i campi parsati se la stringa è valida,
        altrimenti un dizionario con un messaggio di errore.
    """
    if not isinstance(code, str) or code is NULL:
        return {"is_valid": False, "error_message": "L'input non è una stringa valida."}

    # 1. Pulisce la stringa e la converte in maiuscolo
    clean_code = code.strip().upper().replace("CADASTRALPARCEL.", "").replace("IT.AGE.PLA.", "")
    if RIGA_SPURIA_ESATTA in clean_code:
        return {"is_valid": False, "error_message": "Trovata riga spuria."}

    # 2. Validazione della struttura principale con Regex
    main_match = MAIN_PATTERN.match(clean_code)
    if not main_match:
        QgsMessageLog.logMessage(f"Formato generale non valido per '{clean_code}'.", "NCR Parser", Qgis.Warning)
        return {
            "is_valid": False,
            "error_message": f"Formato generale non valido per '{clean_code}'."
        }

    belfiore, sezione_raw, foglio_block, allegato_sviluppo, particella_valore = main_match.groups()

    # --- Parsing della prima parte (Zoning Reference) ---
    sezione = None if not sezione_raw or sezione_raw == "_" else sezione_raw
    
    # Gestisce sia il formato a 4 cifre che quello a 6
    if len(foglio_block) >= 4:
        foglio_raw = foglio_block[:4]
        # La logica per allegato e sviluppo è gestita dopo, qui ci assicuriamo solo del foglio

    if belfiore == "A001":
        return {"is_valid": False, "error_message": "Trovata riga spuria (A001)."}
    
    try:
        foglio = int(foglio_raw)
    except ValueError:
         return {
            "is_valid": False,
            "error_message": f"Il numero di foglio '{foglio_raw}' non è un intero valido."
        }

    # Gestione flessibile di allegato e sviluppo
    if len(foglio_block) == 6:
        allegato = foglio_block[4] if foglio_block[4] != '0' else None
        sviluppo = foglio_block[5] if foglio_block[5] != '0' else None
    else: # len == 4
        allegato = allegato_sviluppo[0] if allegato_sviluppo and allegato_sviluppo[0] != '0' else None
        sviluppo = allegato_sviluppo[1] if allegato_sviluppo and len(allegato_sviluppo) > 1 and allegato_sviluppo[1] != '0' else None

    # --- Parsing della seconda parte (Nome Particella) ---
    result = {
        "is_valid": True,
        "codice_istat": MAPPA_ISTAT.get(belfiore, NULL),
        "regione": MAPPA_REGIONE.get(belfiore, NULL),
        "provincia": MAPPA_PROVINCIA.get(belfiore, NULL),
        "comune": MAPPA_COMUNI.get(belfiore, belfiore),
        "sezione": sezione,
        "foglio": foglio,
        "allegato": allegato,
        "sviluppo": sviluppo,
        "particella_valore": particella_valore,
        "numeratore": None,
        "denominatore": None
    }

    # Catena di controlli per determinare il tipo di particella
    match_tav_edif_fraz = PARTICELLA_TAVOLARE_EDIFICIALE_FRAZIONATA.match(particella_valore)
    if match_tav_edif_fraz:
        result["tipo_particella"] = "tavolare_edificiale_frazionata"
        result["numeratore"] = int(match_tav_edif_fraz.group(1))
        result["denominatore"] = int(match_tav_edif_fraz.group(2))
        result["particella"] = particella_valore
        return result

    match_tav_edif = PARTICELLA_TAVOLARE_EDIFICIALE.match(particella_valore)
    if match_tav_edif:
        result["tipo_particella"] = "tavolare_edificiale"
        result["numeratore"] = int(match_tav_edif.group(1))
        result["particella"] = particella_valore
        return result

    match_tav_fraz = PARTICELLA_TAVOLARE_FRAZIONATA.match(particella_valore)
    if match_tav_fraz:
        result["tipo_particella"] = "tavolare_frazionata"
        result["numeratore"] = int(match_tav_fraz.group(1))
        result["denominatore"] = int(match_tav_fraz.group(2))
        result["particella"] = particella_valore
        return result

    if PARTICELLA_ORDINARIA.match(particella_valore):
        result["tipo_particella"] = "ordinaria"
        result["numeratore"] = int(particella_valore)
        result["particella"] = str(int(particella_valore)) # Rimuove zeri iniziali
        return result
        
    if PARTICELLA_SPECIALE.match(particella_valore):
        result["tipo_particella"] = "speciale"
        result["particella"] = particella_valore
        return result

    # Se nessun pattern corrisponde, la particella non è valida
    QgsMessageLog.logMessage(f"Formato del nome particella '{particella_valore}' non riconosciuto.", "NCR Parser", Qgis.Warning)
    return {
        "is_valid": False,
        "error_message": f"Formato del nome particella '{particella_valore}' non riconosciuto."
    }