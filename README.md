# Estrazione dati catastali da NATIONALCADASTRALREFERENCE

Questo repository contiene uno script Python per QGIS che estrae automaticamente i dati catastali (comune, sezione, foglio, allegato, sviluppo, particella) dal campo `NATIONALCADASTRALREFERENCE`, compilando i relativi campi attributo in un layer vettoriale.

## 📦 Contenuto

- `ncr_commented.py`: script principale, già pronto all'uso in QGIS
- `codcomITA.py`: mappa completa dei codici catastali => nomi comuni italiani

## 🧩 Requisiti

- QGIS (testato con QGIS 3.28 o superiore)
- Il layer deve contenere un campo `NATIONALCADASTRALREFERENCE`

## ⚙️ Come si usa

1. Carica un layer contenente un campo `NATIONALCADASTRALREFERENCE`
2. Apri la console Python di QGIS
3. Esegui lo script `ncr_commented.py`
4. Alla fine, verranno aggiunti i campi catastali e compilati automaticamente

> ✏️ Se non esistono, i campi `comune`, `sezione`, `foglio`, `allegato`, `sviluppo`, `particella` verranno creati automaticamente.

## 🗂 Esempio input

| NATIONALCADASTRALREFERENCE       |
|----------------------------------|
| C632A_1234.567                  |

## 📤 Output generato

| comune | sezione | foglio | allegato | sviluppo | particella |
|--------|---------|--------|----------|----------|------------|
| Chieti |*(Vuoto) | 1234   |*(vuoto)* |*(vuoto)* | 567        |

## 📝 Log

Lo script chiede se vuoi salvare un log con tutte le operazioni svolte (opzionale).

## 📄 Licenza

MIT License
