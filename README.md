# 🏷️ Plugin QGIS: NCR – Estrazione dati catastali

**NCR** è un plugin per QGIS che permette di estrarre automaticamente i dati catastali dai riferimenti contenuti nel campo `NATIONALCADASTRALREFERENCE` di un layer vettoriale. I campi risultanti vengono compilati direttamente nel layer attivo oppure in una copia temporanea se necessario.

---

## 🧩 Funzionalità principali

- Analisi del campo `NATIONALCADASTRALREFERENCE`
- Estrazione automatica di:
  - Comune
  - Sezione
  - Foglio
  - Allegato
  - Sviluppo
  - Particella
- Supporto alla mappa dei codici catastali italiani (`codcomITA.py`)
- Salvataggio del log delle operazioni svolte
- **Gestione layer speciali:**
  - Se il layer è un **WFS** o un **layer temporaneo**, viene creata automaticamente una copia `-copy` in memoria, editabile e con le stesse geometrie/attributi.
  - Se il layer è un **layer normale** (es. shapefile, GeoPackage, PostGIS), il plugin lavora direttamente sull’originale.

---

## 🔧 Requisiti

- QGIS 3.28 o versioni successive
- Un layer con un campo chiamato `NATIONALCADASTRALREFERENCE`

---

## 🚀 Installazione

1. Copia la cartella del plugin in:
   ```
   ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/NCR
   ```

2. Verifica che i file siano presenti:
   - `NCR.py` (script principale con logica di estrazione e gestione layer)
   - `ncr_plugin.py` (integrazione con menu QGIS)
   - `codcomITA.py` (mappa codici comuni catastali)
   - `icon.png` (icona plugin)
   - `metadata.txt`
   - `__init__.py`

3. Riavvia QGIS. Il plugin sarà disponibile nel menu **Plugin > NCR > Estrai dati catastali**.

---

## 🖥️ Utilizzo

1. Carica un layer contenente il campo `NATIONALCADASTRALREFERENCE`.
2. Avvia il plugin da:
   - **Plugin > NCR > Estrai dati catastali**, oppure
   - **Toolbar** (icona con il logo dell'Agenzia delle Entrate).
3. Il plugin:
   - Verifica se il layer è editabile:
     - Se **WFS** o **temporaneo**, crea un nuovo layer `nome-layer-copy` in memoria (editabile) con stesse geometrie e attributi.
     - Se **normale**, lavora direttamente sull’originale.
   - Crea i campi di output se non presenti
   - Analizza e compila i valori riga per riga
   - Salva un log (facoltativo) delle operazioni effettuate

---

## 💡 Esempi di input

| Codice input           | Comune riconosciuto       | Foglio | Particella |
|------------------------|---------------------------|--------|------------|
| `C632_1234.567`        | Chieti                    | 1234   | 567        |
| `D763_00210Z.4331`     | Francavilla al Mare       | 0210   | 4331       |
| `A345A010200.2908`     | L'Aquila                  | 0102   | 2908       |

---

## 🗂️ Campi di output generati

| Campo        | Tipo     |
|--------------|----------|
| `comune`     | Testo    |
| `sezione`    | Testo    |
| `foglio`     | Testo    |
| `allegato`   | Testo    |
| `sviluppo`   | Testo    |
| `particella` | Testo    |

---

## 📝 Log

Alla fine dell'elaborazione ti verrà chiesto se vuoi salvare un file `.txt` con il log dettagliato delle operazioni (modifiche, campi invariati, errori di parsing ecc.).
Il log è organizzato per **ID feature** ed è utile per verificare cosa è stato modificato.

---

## 📦 Struttura del plugin

```
NCR/
├── __init__.py
├── NCR.py
├── ncr_plugin.py
├── codcomITA.py
├── icon.png
└── metadata.txt
```

---

## 👤 Autore

Plugin sviluppato da **Antonio Di Sipio**  
📧 Email: `antonio[dot]disipio[at]gmail[dot]com`  
🔗 Licenza: MIT

---

## 📷 Icona

L'icona del plugin è ispirata al logo dell’Agenzia delle Entrate.

---

## 📌 Note importanti

- Il plugin aggiunge automaticamente i campi mancanti.
- Se usato su un layer WFS/temporaneo, viene creata una copia `-copy` **editabile**: lavora sempre su questa, non sull’originale.
- Se usato su un layer shapefile, gpkg o PostGIS, lavora direttamente sul layer originale.
- Il comportamento è stato pensato per evitare errori di scrittura su layer non editabili (tipico dei WFS).
