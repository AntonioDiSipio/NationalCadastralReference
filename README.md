# Estrazione dati catastali da NATIONALCADASTRALREFERENCE

Questo repository contiene uno script Python per QGIS che estrae automaticamente i dati catastali (comune, sezione, foglio, allegato, sviluppo, particella) da un campo `NATIONALCADASTRALREFERENCE`, compilando i relativi campi attributo in un layer vettoriale.

## 📦 Contenuto

- `ncr.py`: script principale, già pronto all'uso in QGIS
- `codcomITA.py`: mappa completa dei codici catastali => nomi comuni italiani

## 🧩 Requisiti

- QGIS (testato con QGIS 3.28 o superiore)
- Il layer deve contenere un campo `NATIONALCADASTRALREFERENCE`

## ⚙️ Come si usa

### Fase 1: Preparazione dei dati catastali da WFS ufficiale

1. Apri QGIS
2. Aggiungi un layer di base (es. OpenStreetMap)
3. Aggiungi il layer WFS dell'Agenzia delle Entrate:
   - **URL**: `https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php?VERSION=2.0.0`
   - Vai su **Layer > Aggiungi Layer > Aggiungi layer WFS / OGC API - Features**
   - Crea una nuova connessione con l'URL sopra
   - Clicca su **Connetti**, seleziona il layer `CP:CadastralParcel`
   - Spunta **"Solo le geometrie sovrapposte all'estensione della vista"**, quindi clicca su **Aggiungi**
4. Verrà aggiunto il layer "CP:CadastralParcel"
5. (Opzionale ma consigliato) Rimuovi i duplicati:
   - Vai su **Processing > Toolbox**
   - Cerca "Elimina vettori duplicati" e applicalo sul layer WFS per ottenere un layer temporaneo pulito

### Fase 2: Esecuzione dello script

1. Scarica `ncr.py` e `codcomITA.py` e mettili nella stessa cartella
2. Vai su **Plugin > Console Python > Mostra editor**
3. Apri `ncr.py` dallo script editor
4. Clicca su **Esegui Script**
5. Verrà richiesto dove salvare un file `.txt` contenente il log delle operazioni
6. Il layer verrà aggiornato con i seguenti campi (creati automaticamente se mancanti):
   - `comune`
   - `sezione`
   - `foglio`
   - `allegato`
   - `sviluppo`
   - `particella`

## 🗂 Esempio input

| NATIONALCADASTRALREFERENCE       |
|----------------------------------|
| C632_1234.567                   |

## 📤 Output generato

| comune               | sezione   | foglio | allegato | sviluppo | particella |
|----------------------|-----------|--------|----------|----------|------------|
| Chieti               | *(vuoto)* | 1234   | *(vuoto)*| *(vuoto)*| 567        |
| San Giovanni Teatino| *(vuoto)* | 0009   | *(vuoto)*| *(vuoto)*| 4096       |
| Francavilla al Mare | *(vuoto)* | 0015   | A        | Z        | 4159       |

## 📌 Esempi aggiuntivi

### Esempio 1
**Input:**
```
D690_000900.4096
```
**Output:**
| comune               | sezione   | foglio | allegato | sviluppo | particella |
|----------------------|-----------|--------|----------|----------|------------|
| San Giovanni Teatino | *(vuoto)* | 0009   | *(vuoto)*| *(vuoto)*| 4096       |

### Esempio 2
**Input:**
```
D763_0015AZ.4159
```
**Output:**
| comune               | sezione   | foglio | allegato | sviluppo | particella |
|----------------------|-----------|--------|----------|----------|------------|
| Francavilla al Mare  | *(vuoto)* | 0015   | A        | Z        | 4159       |

## 📝 Log

Lo script chiede se vuoi salvare un log con tutte le operazioni svolte (opzionale).

## 📄 Licenza

MIT License
