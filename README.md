# Extractor de texto PDF con PyMuPDF

Herramienta CLI para extraer texto de uno o varios PDFs usando `fitz` / PyMuPDF.
Genera un `.txt` por PDF, un JSON opcional por pagina y un `manifest.json` con
el resumen del procesamiento.

## Interfaz web local

```powershell
powershell -ExecutionPolicy Bypass -File .\run_interface.ps1
```

Abre esta direccion en el navegador:

```text
http://127.0.0.1:8765
```

Desde ahi puedes seleccionar o arrastrar PDFs, ajustar cuanto header o pie de
pagina se omite, extraer el contenido y abrir los archivos `.txt` o `.json`
generados. La interfaz usa siempre el motor de lectura humana para respetar
columnas y letras capitales.

## Instalar dependencia

```powershell
python -m pip install -r requirements.txt
```

En este workspace tambien puedes usar la copia local ya disponible:

```powershell
$env:PYTHONPATH='..\..\.docqa_packages'
```

## Usar con un PDF

```powershell
$env:PYTHONPATH='..\..\.docqa_packages'
python .\extract_pdf_text.py `
  "C:\ruta\al\archivo.pdf" `
  -o .\text
```

## Usar con una carpeta

```powershell
$env:PYTHONPATH='..\..\.docqa_packages'
python .\extract_pdf_text.py "C:\ruta\a\pdfs" `
  -o .\text `
  --recursive
```

## Opciones utiles

- `--mode human`: ordena texto por columnas, quita header/footer y limpia parrafos. Es el default.
- `--header-percent 8`: omite el 8% superior de cada pagina en modo human.
- `--footer-percent 5`: omite el 5% inferior de cada pagina en modo human.
- `--mode text`: extrae el flujo de texto normal.
- `--mode blocks`: separa bloques visuales; suele ayudar con documentos en columnas.
- `--no-pages-json`: solo genera TXT y manifest.
- `--recursive`: busca PDFs en subcarpetas.

Si `needs_ocr` aparece como `true` en el manifest, el PDF probablemente es
escaneado o contiene imagenes sin capa de texto. En ese caso hace falta OCR.

## Evaluar set de entrenamiento

```powershell
python .\evaluate_training_set.py `
  "C:\Users\jumim\OneDrive\Escritorio\Efinfo\Entrenamientos OCR" `
  -o .\evaluation
```

Genera `summary.md`, `summary.csv`, `summary.json` y una carpeta por caso con
el texto actual, el expected copiado y un `diff.txt`.
