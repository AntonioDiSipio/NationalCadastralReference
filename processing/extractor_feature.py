# NCR/processing/extractor_feature.py

import os
from datetime import datetime
from qgis.core import (QgsProject, QgsVectorLayer, QgsFeature, QgsFields, 
                     QgsField, QgsMessageLog, Qgis, NULL, QgsVectorFileWriter,
                     QgsCoordinateTransformContext, QgsMapLayer)
from qgis.PyQt.QtWidgets import QMessageBox, QProgressDialog
from qgis.PyQt.QtCore import Qt

try:
    from qgis.PyQt.QtCore import QVariant
    FIELD_TYPE_STRING = QVariant.String
except ImportError:
    from qgis.PyQt.QtCore import QMetaType
    FIELD_TYPE_STRING = QMetaType.Type.QString

from ..core.parser import parse_ncr, is_riga_spuria

CAMPO_INPUT = "INSPIREID_LOCALID"
CAMPI_OUTPUT = ["codice_istat", "regione", "provincia", "comune", "sezione", "foglio", "allegato", "sviluppo", "particella"]
CAMPI_DA_ELIMINARE = ["INSPIREID_NAMESPACE", "LABEL", "ADMINISTRATIVEUNIT", "nationalcadastralreference", "NATIONALCADASTRALREFERENCE", "INSPIREID_LOCALID"]

def applica_stile_qml(layer):
    """Applica il file di stile QML forzando Simbologia ed Etichettatura dopo l'aggiunta a QGIS."""
    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        # Cerca il file di stile con priorità
        possible_names = ["stile_particelle.qml", "particelle_style.qml"]
        qml_path = None
        for name in possible_names:
            path = os.path.join(base_dir, "styles", name)
            if os.path.exists(path):
                qml_path = path
                break

        if os.path.exists(qml_path):
            categories = QgsMapLayer.Symbology | QgsMapLayer.Labeling
            # Applica lo stile. Ignoriamo il valore di ritorno 'res' perché può essere
            # inaffidabile, riportando 'False' anche quando lo stile viene applicato.
            layer.loadNamedStyle(qml_path, categories)
            QgsMessageLog.logMessage(f"Tentativo di applicare lo stile QML da: {qml_path}", "NCR", Qgis.Info)
            
            layer.setLabelsEnabled(True)
            layer.triggerRepaint()
        else:
            QgsMessageLog.logMessage(f"Nessun file di stile QML trovato nella cartella 'styles'. Stile ignorato.", "NCR", Qgis.Warning)
    except Exception as e:
        QgsMessageLog.logMessage(f"Errore durante l'applicazione dello stile QML: {str(e)}", "NCR", Qgis.Warning)

def ottieni_layer_memoria_esistenti(layer_corrente_id):
    return [lyr for l_id, lyr in QgsProject.instance().mapLayers().items() 
            if l_id != layer_corrente_id and isinstance(lyr, QgsVectorLayer)]

def assicura_campi_output(target_layer):
    prov = target_layer.dataProvider()
    campi_esistenti = [f.name().lower() for f in target_layer.fields()]
    campi_da_aggiungere = CAMPI_OUTPUT.copy()
    if "timestamp" not in campi_esistenti:
        campi_da_aggiungere.insert(0, "timestamp") # Aggiungiamo il timestamp se manca
    nuovi = [QgsField(nome, FIELD_TYPE_STRING) for nome in campi_da_aggiungere if nome.lower() not in campi_esistenti]
    if nuovi:
        prov.addAttributes(nuovi)
        target_layer.updateFields()

def esegui_estrazione(source_layer, filtri):
    from qgis.utils import iface
    
    if not source_layer or not source_layer.isValid():
        raise Exception("Layer sorgente non valido o non specificato.")

    # Controllo bloccante: il Modulo B deve operare solo sul layer WFS dell'AdE
    if source_layer.name() != "CP:CadastralParcel":
        raise Exception("MODULO B: Selezionare il layer WFS dell'Agenzia delle Entrate (CP:CadastralParcel) prima di avviare l'estrazione.")

    comune_f = filtri.get("comune")
    sezione_f = filtri.get("sezione")
    foglio_f = str(filtri.get("foglio")) if filtri.get("foglio") is not None else None
    allegato_f = filtri.get("allegato")
    sviluppo_f = filtri.get("sviluppo")
    particella_f = filtri.get("particella")
    gpkg_path = filtri.get("gpkg_path")
    target_layer_selezionato = filtri.get("target_layer")

    # --- Inizio Logica Modulo B ---

    # 1. Preparazione del layer temporaneo di staging
    geom_type = source_layer.geometryType()
    geom_str = "Polygon"
    if geom_type == Qgis.GeometryType.Point: geom_str = "Point"
    elif geom_type == Qgis.GeometryType.Line: geom_str = "LineString"
    
    uri = f"{geom_str}?crs={source_layer.crs().authid()}"
    temp_mem_layer = QgsVectorLayer(uri, "temp_extract", "memory")
    
    campi_sorgente_filtrati = [f for f in source_layer.fields() if f.name() not in CAMPI_DA_ELIMINARE]
    temp_mem_layer.dataProvider().addAttributes(campi_sorgente_filtrati)
    temp_mem_layer.updateFields()

    # Aggiunge il campo inspireid_localid in minuscolo
    temp_mem_layer.dataProvider().addAttributes([QgsField("inspireid_localid", FIELD_TYPE_STRING)])
    # Aggiunge il campo per il timestamp
    temp_mem_layer.dataProvider().addAttributes([QgsField("timestamp", FIELD_TYPE_STRING)])
    temp_mem_layer.updateFields()
    assicura_campi_output(temp_mem_layer)
    mappa_indici_output = {nome: temp_mem_layer.fields().lookupField(nome) for nome in CAMPI_OUTPUT}

    # 2. Controllo duplicati: crea un set di chiavi e geometrie già presenti
    riferimenti_gia_nel_target, geometrie_gia_nel_target = set(), set()
    if target_layer_selezionato:
        idx_input_dest = target_layer_selezionato.fields().lookupField(CAMPO_INPUT)
        for f in target_layer_selezionato.getFeatures():
            if idx_input_dest != -1 and f[idx_input_dest] and f[idx_input_dest] != NULL:
                riferimenti_gia_nel_target.add(str(f[idx_input_dest]).strip().upper())
            if f.hasGeometry():
                geometrie_gia_nel_target.add(f.geometry().asWkt())

    # 3. Ciclo di estrazione e filtraggio
    total = source_layer.featureCount() if source_layer.featureCount() > 0 else 100
    progress = QProgressDialog("Modulo B: Elaborazione ed estrazione particelle...", "Annulla", 0, total, iface.mainWindow())
    try:
        progress.setWindowModality(Qt.WindowModality.WindowModal)
    except AttributeError:
        progress.setWindowModality(Qt.WindowModal)
    progress.setWindowTitle("NCR - Estrazione Catastale")
    progress.show()

    nuove_features = []
    timestamp_elaborazione = datetime.now().isoformat(sep=' ', timespec='seconds')
    totale_scartati = 0
    idx_input_src = source_layer.fields().lookupField(CAMPO_INPUT)

    for i, feat in enumerate(source_layer.getFeatures()):
        if progress.wasCanceled(): break
        progress.setValue(i)

        if is_riga_spuria(feat):
            totale_scartati += 1
            continue

        ref = feat[idx_input_src] if idx_input_src != -1 else None
        ref_clean = str(ref).strip().upper() if ref and ref != NULL else ""
        geom_wkt = feat.geometry().asWkt() if feat.hasGeometry() else ""

        is_speciale = any(k in ref_clean for k in ["STRADA", "ACQUA", "AREA", "FABBR"])
        if is_speciale:
            if geom_wkt and geom_wkt in geometrie_gia_nel_target:
                totale_scartati += 1; continue
        else:
            if ref_clean in riferimenti_gia_nel_target or (geom_wkt and geom_wkt in geometrie_gia_nel_target):
                totale_scartati += 1; continue

        parsed = parse_ncr(ref)
        if not parsed or not parsed.get('is_valid'):
            totale_scartati += 1
            continue

        if comune_f and parsed.get("comune") != comune_f: totale_scartati += 1; continue
        if sezione_f and parsed.get("sezione") != sezione_f: totale_scartati += 1; continue
        if foglio_f and str(parsed.get("foglio")) != foglio_f: totale_scartati += 1; continue
        if allegato_f and parsed.get("allegato") != allegato_f: totale_scartati += 1; continue
        if sviluppo_f and parsed.get("sviluppo") != sviluppo_f: totale_scartati += 1; continue

        if particella_f:
            p_dig = str(particella_f).lstrip('0').upper()
            p_eff = str(parsed.get("particella", "")).upper()
            if p_eff != p_dig: totale_scartati += 1; continue

        nuova_feat = QgsFeature()
        nuova_feat.setFields(temp_mem_layer.fields())
        if feat.hasGeometry(): nuova_feat.setGeometry(feat.geometry())

        for s_field in campi_sorgente_filtrati:
            d_idx = temp_mem_layer.fields().lookupField(s_field.name())
            if d_idx != -1: nuova_feat.setAttribute(d_idx, feat.attribute(s_field.name()))
        
        nuova_feat.setAttribute("inspireid_localid", ref)
        nuova_feat.setAttribute("timestamp", timestamp_elaborazione)

        for campo_nome, valore in parsed.items():
            if campo_nome in CAMPI_OUTPUT:
                d_idx = mappa_indici_output.get(campo_nome, -1)
                if d_idx != -1: nuova_feat.setAttribute(d_idx, str(valore) if valore is not None else NULL)

        nuove_features.append(nuova_feat)
        if ref_clean: riferimenti_gia_nel_target.add(ref_clean)
        if geom_wkt: geometrie_gia_nel_target.add(geom_wkt)

    progress.close()

    if not nuove_features:
        QMessageBox.information(iface.mainWindow(), "Risultato", f"Nessuna nuova particella trovata con i filtri impostati.\nScartati/Duplicati: {totale_scartati}")
        return

    temp_mem_layer.dataProvider().addFeatures(nuove_features)
    temp_mem_layer.updateExtents()

    # 4. Gestione dell'output finale
    parti_nome = []
    if comune_f: parti_nome.append(str(comune_f))
    if foglio_f: parti_nome.append(f"foglio {foglio_f}")
    if particella_f: parti_nome.append(f"particella {particella_f}")
    nome_layer_dinamico = "-".join(parti_nome) if parti_nome else "Estratto Catastale"

    # CASO 1: AGGIORNAMENTO LAYER ESISTENTE IN QGIS
    if target_layer_selezionato:
        assicura_campi_output(target_layer_selezionato)
        
        features_allineate = []
        for nf in nuove_features:
            feat_dest = QgsFeature(target_layer_selezionato.fields())
            if nf.hasGeometry(): feat_dest.setGeometry(nf.geometry())
            for f_col in temp_mem_layer.fields():
                idx_d = target_layer_selezionato.fields().lookupField(f_col.name())
                if idx_d != -1: feat_dest.setAttribute(idx_d, nf.attribute(f_col.name()))
            features_allineate.append(feat_dest)

        target_layer_selezionato.dataProvider().addFeatures(features_allineate)
        target_layer_selezionato.updateExtents()
        applica_stile_qml(target_layer_selezionato)
        dest_layer = target_layer_selezionato

    # CASO 2: SALVATAGGIO SU FILE GEOPACKAGE
    elif gpkg_path:
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = nome_layer_dinamico
        # Se il file non esiste, lo creiamo. Se esiste, sovrascriviamo il layer al suo interno.
        if not os.path.exists(gpkg_path):
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        else:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

        # La funzione restituisce una tupla, il codice di errore è il primo elemento.
        result_tuple = QgsVectorFileWriter.writeAsVectorFormatV3(temp_mem_layer, gpkg_path, QgsCoordinateTransformContext(), options)
        error_code = result_tuple[0]
        if error_code != QgsVectorFileWriter.WriterError.NoError:
            raise Exception(f"Errore nella scrittura del file GeoPackage (codice: {error_code}). Dettagli: {result_tuple[1]}")

        dest_layer = QgsVectorLayer(f"{gpkg_path}|layername={nome_layer_dinamico}", nome_layer_dinamico, "ogr")
        applica_stile_qml(dest_layer)
        QgsProject.instance().addMapLayer(dest_layer)

    # CASO 3: LAYER IN MEMORIA TEMPORANEO
    else:
        temp_mem_layer.setName(nome_layer_dinamico)
        applica_stile_qml(temp_mem_layer)
        QgsProject.instance().addMapLayer(temp_mem_layer)
        dest_layer = temp_mem_layer

    QMessageBox.information(
        iface.mainWindow(), "Completato", 
        f"Elaborazione Modulo B completata con successo!\n"
        f"Layer: '{dest_layer.name()}'\n"
        f"Particelle aggiunte: {len(nuove_features)}\n"
        f"Scartati/Duplicati: {totale_scartati}"
    )