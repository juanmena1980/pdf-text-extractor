# Extractor de texto PDF con PyMuPDF

Herramienta independiente para extraer texto de uno o varios PDFs usando
`fitz` / PyMuPDF. Incluye interfaz web local y modo CLI.

Genera un `.txt` por PDF, un JSON opcional por pagina y un `manifest.json`.
La correccion de texto esta separada por **genero editorial**: cada genero
tiene su propio motor en `engines/`.

## Géneros / motores de correccion

| ID | Descripcion |
| --- | --- |
| `nota_informativa` | Notas cortas de prensa (default) |
| `periodismo` | Diccionario de artefactos tipicos de columnas |
| `generico` | Solo limpieza base (parrafos, guiones, drop caps) |

Para agregar un genero nuevo: crea `engines/mi_genero.py`, registra el motor
y agrega el import en `engines/__init__.py`.

## Usar desde una USB (recomendado)

### Opcion A — Ejecutable unico (mejor entre PCs distintas)

En una PC con Python, genera el `.exe` una vez:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_portable.ps1
```

Copia a la USB la carpeta `dist\usb` (o al menos `PDFTextExtractor.exe` + `Iniciar.bat`).

En cualquier Windows, abre `Iniciar.bat` o haz doble clic en `PDFTextExtractor.exe`.
Se abre el navegador en `http://127.0.0.1:8765`. Los `.txt` quedan en la carpeta `text` al lado del ejecutable.

### Opcion B — Runtime portable (sin .exe)

En una PC con Python, prepara el runtime una vez:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_usb.ps1
```

Copia **toda** la carpeta del proyecto a la USB y abre `Iniciar.bat`.

## Interfaz web en desarrollo

```powershell
powershell -ExecutionPolicy Bypass -File .\run_interface.ps1
```

O simplemente:

```powershell
.\Iniciar.bat
```

Abre esta direccion en el navegador:

```text
http://127.0.0.1:8765
```

Desde ahi puedes seleccionar o arrastrar PDFs, elegir el genero de correccion,
ajustar cuanto header o pie de pagina se omite, extraer el contenido y abrir
los archivos `.txt` o `.json` generados.

## Instalar dependencia (modo desarrollo)

```powershell
python -m pip install -r requirements.txt
```

## Usar con un PDF (CLI)

```powershell
python .\extract_pdf_text.py "C:\ruta\al\archivo.pdf" -o .\text --genre nota_informativa
```

## Usar con una carpeta (CLI)

```powershell
python .\extract_pdf_text.py "C:\ruta\a\pdfs" -o .\text --recursive --genre generico
```

## Opciones utiles

- `--genre nota_informativa|periodismo|generico`: elige el motor de correccion.
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
  -o .\evaluation `
  --genre nota_informativa
```

Genera `summary.md`, `summary.csv`, `summary.json` y una carpeta por caso con
el texto actual, el expected copiado y un `diff.txt`.
