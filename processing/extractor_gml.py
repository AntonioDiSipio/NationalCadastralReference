# NCR/processing/extractor_gml.py

import os
import io
import tempfile
import zipfile
import urllib.request 
from qgis.core import QgsVectorFileWriter, QgsCoordinateTransformContext
from datetime import datetime
from qgis.PyQt.QtCore import QVariant
from qgis.core import (Qgis, QgsMessageLog, QgsVectorLayer, QgsFeature, 
                     QgsField, QgsFields, QgsProject, NULL)

from .extractor_feature import applica_stile_qml
from ..core.parser import parse_ncr
from ..core.constants import BASE_URL_AE

def get_cache_dir():
    """Restituisce il percorso della directory di cache, creandola se non esiste."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    cache_dir = os.path.join(base_dir, "cache_downloads")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def assicura_download_regione(zip_filename):
    """
    Verifica se il file ZIP della regione è in cache. Se non lo è, lo scarica.
    Restituisce il percorso completo del file in cache.
    """
    cache_dir = get_cache_dir()
    file_zip = os.path.join(cache_dir, zip_filename)

    if not os.path.exists(file_zip):
        url = f"{BASE_URL_AE}{zip_filename}"
        QgsMessageLog.logMessage(f"Download dataset regionale da: {url}", "NCR", Qgis.Info)
        req = urllib.request.Request(url, headers={'User-Agent': 'QGIS-NCR-Plugin'})
        with urllib.request.urlopen(req, timeout=300) as resp, open(file_zip, 'wb') as f_out:
            f_out.write(resp.read())
        QgsMessageLog.logMessage(f"Dataset {zip_filename} salvato in cache!", "NCR", Qgis.Info)

    return file_zip

def costruisci_layer_da_zip_regionale(zip_regionale_path, codice_belfiore_input, nome_layer_custom=None, gpkg_path=None):
    """
    Funzione principale del Modulo A. Scansiona gli ZIP, estrae i GML del comune richiesto
    e costruisce un QgsVectorLayer completo di attributi parsati.
    """
    features_gml = []
    timestamp_elaborazione = datetime.now().isoformat(sep=' ', timespec='seconds')
    crs_sorgente = None

    cod_target = str(codice_belfiore_input).strip().upper()
    if '(' in cod_target and ')' in cod_target:
        cod_target = cod_target.split('(')[-1].split(')')[0].strip()

    if not cod_target or len(cod_target) != 4:
        raise Exception(f"Codice Belfiore non valido: '{cod_target}'. Impossibile individuare il Comune.")
        
    # Definisce i campi di destinazione una sola volta, all'inizio.
    campi_destinazione = QgsFields()
    campi_destinazione.append(QgsField("inspireid_localid", QVariant.String))
    campi_destinazione.append(QgsField("timestamp", QVariant.String))
    campi_ncr = ["codice_istat", "regione", "provincia", "comune", "sezione", "foglio", "allegato", "sviluppo", "particella"]
    for nome_campo in campi_ncr:
        campi_destinazione.append(QgsField(nome_campo, QVariant.String))

    QgsMessageLog.logMessage(f"Ricerca esatta per Codice Belfiore: '{cod_target}'", "NCR", Qgis.Info)

    def elabora_file_gml(zip_obj, nome_gml):
        nonlocal crs_sorgente, features_gml
        # Usa un file temporaneo gestito in modo sicuro
        with tempfile.NamedTemporaryFile(suffix=".gml", delete=False) as temp_gml_file:
            temp_gml_file.write(zip_obj.read(nome_gml))
            layer_gml = QgsVectorLayer(temp_gml_file.name, "temp_gml", "ogr")
        if layer_gml.isValid():
            if not crs_sorgente:
                crs_sorgente = layer_gml.crs()
            
            idx_ref_gml = layer_gml.fields().lookupField("INSPIREID_LOCALID")
            if idx_ref_gml == -1:
                return

            for feat in layer_gml.getFeatures():
                ref_val = feat.attribute(idx_ref_gml)
                if not ref_val:
                    continue

                dati_ncr = parse_ncr(ref_val)
                if dati_ncr and dati_ncr.get('is_valid'):
                    # Crea una feature già con lo schema di campi corretto
                    new_feat = QgsFeature(campi_destinazione)
                    new_feat.setGeometry(feat.geometry())
                    
                    new_feat.setAttributes([
                        ref_val,
                        timestamp_elaborazione,
                        dati_ncr.get("codice_istat"),
                        dati_ncr.get("regione"),
                        dati_ncr.get("provincia"),
                        dati_ncr.get("comune"),
                        dati_ncr.get("sezione"),
                        str(dati_ncr.get("foglio")) if dati_ncr.get("foglio") is not None else NULL,
                        dati_ncr.get("allegato"),
                        dati_ncr.get("sviluppo"),
                        str(dati_ncr.get("particella")) if dati_ncr.get("particella") is not None else NULL,
                    ])
                    features_gml.append(new_feat)

        # Rilascia esplicitamente il layer e le sue risorse prima di tentare la rimozione del file
        layer_gml = None

        if os.path.exists(temp_gml_file.name):
            try:
                os.remove(temp_gml_file.name)
            except OSError as e:
                QgsMessageLog.logMessage(f"Impossibile rimuovere il file temporaneo {temp_gml_file.name}: {e}", "NCR", Qgis.Warning)

    trovato_comune = False
    with zipfile.ZipFile(zip_regionale_path, 'r') as main_zip:
        for nome_prov_zip in (f for f in main_zip.namelist() if f.lower().endswith('.zip')):
            with zipfile.ZipFile(io.BytesIO(main_zip.read(nome_prov_zip))) as prov_zip:
                for nome_comune_zip in (f for f in prov_zip.namelist() if f.lower().endswith('.zip')):
                    if cod_target.upper() not in nome_comune_zip.upper():
                        continue

                    trovato_comune = True
                    with zipfile.ZipFile(io.BytesIO(prov_zip.read(nome_comune_zip))) as zip_comune:
                        for nome_foglio_zip in (f for f in zip_comune.namelist() if f.lower().endswith('.zip')):
                            with zipfile.ZipFile(io.BytesIO(zip_comune.read(nome_foglio_zip))) as zip_foglio:
                                for gml_name in (f for f in zip_foglio.namelist() if f.lower().endswith('.gml') and not f.lower().endswith('_pt.gml')):
                                    elabora_file_gml(zip_foglio, gml_name)
                        for gml_name in (f for f in zip_comune.namelist() if f.lower().endswith('.gml') and not f.lower().endswith('_pt.gml')):
                            elabora_file_gml(zip_comune, gml_name)
                    break
            if trovato_comune:
                break

    if not trovato_comune:
        raise Exception(f"MODULO A: Il Codice Belfiore '{cod_target}' non è stato trovato nello ZIP della Regione selezionata.")

    if not features_gml:
        raise Exception(f"MODULO A: Nessuna particella vettoriale trovata per il Comune '{cod_target}'.")

    titolo_layer = nome_layer_custom if nome_layer_custom else f"Catasto_{cod_target}"
    uri = f"Polygon?crs={crs_sorgente.authid() if crs_sorgente else 'EPSG:6706'}"
    mem_layer = QgsVectorLayer(uri, titolo_layer, "memory")
    
    dp = mem_layer.dataProvider()    
    dp.addAttributes(campi_destinazione)
    mem_layer.updateFields()

    dp.addFeatures(features_gml)
    mem_layer.updateExtents()

    # Gestione dell'output: GeoPackage o Layer in memoria
    if gpkg_path:
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = titolo_layer
        if not os.path.exists(gpkg_path):
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        else:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

        result_tuple = QgsVectorFileWriter.writeAsVectorFormatV3(mem_layer, gpkg_path, QgsCoordinateTransformContext(), options)
        error_code = result_tuple[0]
        if error_code != QgsVectorFileWriter.WriterError.NoError:
            raise Exception(f"Errore nella scrittura del file GeoPackage (codice: {error_code}). Dettagli: {result_tuple[1]}")

        dest_layer = QgsVectorLayer(f"{gpkg_path}|layername={titolo_layer}", titolo_layer, "ogr")
        applica_stile_qml(dest_layer)
        QgsProject.instance().addMapLayer(dest_layer)
        return dest_layer
    else:
        # Comportamento predefinito: layer in memoria
        QgsProject.instance().addMapLayer(mem_layer)
        applica_stile_qml(mem_layer)
        return mem_layer