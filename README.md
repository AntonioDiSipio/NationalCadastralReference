# 🏷️ Plugin QGIS: NCR – Estrazione dati catastali

**NCR** è un plugin per QGIS progettato per automatizzare l'estrazione e la trasformazione dei dati catastali basandosi sul campo `NATIONALCADASTRALREFERENCE` di un layer vettoriale[cite: 9].

---

## ⚠️ Modalità di lavoro sui layer

* **Se il layer è WFS o non editabile (WFS3, Memory, OAPIF):**  
  Viene creata automaticamente una copia `-copy` in memoria (con nome dinamico basato sul filtro scelto, es. `Villamagna-foglio 3-copy`), perfettamente editabile e con tutte le geometrie intatte. Il plugin lavora in modo sicuro su questa copia senza alterare la sorgente WFS originale.

* **Se il layer è un layer locale modificabile (Shapefile, GeoPackage, ecc.):**  
  Il plugin opera direttamente sul layer attivo.

---

## 🧩 Funzionalità principali

* **Finestra di dialogo avanzata con filtri in cascata:** Permette di filtrare i dati in modo dinamico e sequenziale (Comune $\rightarrow$ Sezione $\rightarrow$ Foglio $\rightarrow$ Allegato $\rightarrow$ Sviluppo $\rightarrow$ Particella).
* **Decodifica territoriale automatica:** Si collega via web a GitHub per scaricare il file aggiornato dei comuni (`comuni_belfiore.json`), estraendo in automatico:
  * Codice ISTAT
  * Regione
  * Provincia
  * Comune
* **Gestione Cache Offline:** Se la connessione internet non è disponibile, il plugin utilizza automaticamente l'ultima versione memorizzata nella cache locale.
* **Pulizia automatica delle righe spurie:** Scarta ed elimina autonomamente righe tecniche non valide (es. codici fittizi come `A001_000100.ACQUA001`).
* **Rimozione metadati superflui:** Elimina automaticamente i campi non necessari generati in origine dal WFS (`INSPIREID_LOCALID`, `INSPIREID_NAMESPACE`, `LABEL`).
* **Normalizzazione dei dati:** Rimuove gli zeri non significativi dai numeri di foglio e di particella preservando al contempo le codifiche speciali (es. strade e acque).

---

## 🔧 Requisiti

* QGIS 4.0 o versioni compatibili (con supporto a PyQt6 / Python)[cite: 9].
* Un layer attivo dotato del campo `NATIONALCADASTRALREFERENCE`[cite: 9].

---

## 🚀 Installazione

1. Copia l'intera cartella del plugin all'interno della directory dei plugin di QGIS (solitamente in `profiles/default/python/plugins/`).
2. Attiva il plugin dal "Gestore dei plugin" di QGIS.
3. Utilizza l'icona dedicata o il menu contestuale nel menu **NCR** per avviare l'estrazione[cite: 11].

---

## Licenza
Questo progetto è distribuito con licenza **GNU General Public License v3.0 (GPL-3.0-or-later)**. Per maggiori dettagli, consulta il file LICENSE.

## Disclaimer / Esclusione di Responsabilità
- Il software è fornito "così com'è" (*AS IS*), a solo scopo di supporto tecnico, senza alcuna garanzia esplicita o implicita.
- Le elaborazioni cartografiche e catastali prodotte dal plugin non sostituiscono la documentazione ufficiale né i rilievi tecnici di legge.
- L'utente è tenuto a verificare sempre la correttezza dei dati presso gli organi e le banche dati istituzionali competenti (Agenzia delle Entrate ed Enti preposti).
- L'autore declina ogni responsabilità per errori, omissioni, discrepanze geometriche, decisioni tecniche/amministrative o danni diretti/indiretti derivanti dall'uso del software.