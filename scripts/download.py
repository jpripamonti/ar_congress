import os
import requests
import json
from datetime import datetime
import re
import time
import pandas as pd


# Configuración para la pausa
DOWNLOAD_DELAY = 5  # Pausa en segundos entre descargas


# URLs base para el Senado
SENADO_URL = "https://www.senado.gob.ar/micrositios/DatosAbiertos/ExportarListadoVersionesTac/json"
OUTPUT_FOLDER_SENADO = "./data/raw/senado/taquigraficas/"  # Carpeta para Senado

# Filtros configurables
FILTER_YEARS = [2024, 2023, 2022, 2021, 2020]  # Lista de años que queremos descargar
FILTER_SESSION_TYPES = None #["ORDINARIA"]  # Lista de tipos de sesión (o None para todos)

# Configuración de reintentos
MAX_RETRIES = 3

def fetch_taquigraficas_json(url):
    """
    Descarga el JSON desde la URL y valida su estructura.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()

        # Eliminar posibles comas finales en el JSON
        cleaned_text = re.sub(r",\s*([\}\]])", r"\1", response.text)

        # Cargar el JSON
        json_data = json.loads(cleaned_text)

        # Validar la estructura esperada
        if not isinstance(json_data, dict) or "table" not in json_data:
            print("Estructura inesperada en el JSON descargado. Falta 'table'.")
            return None
        if "rows" not in json_data["table"] or not isinstance(json_data["table"]["rows"], list):
            print("Estructura inesperada en el JSON descargado. Falta 'rows'.")
            return None

        return json_data

    except requests.exceptions.RequestException as e:
        print(f"Error al descargar el JSON desde {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error al procesar el JSON descargado: {e}")
        return None

def parse_taquigraficas(json_data):
    """
    Procesa el JSON y extrae las URLs de las versiones taquigráficas junto con los metadatos.
    """
    rows = json_data.get("table", {}).get("rows", [])
    if not isinstance(rows, list):
        print("El JSON no contiene una lista válida en 'table->rows'.")
        return []

    taquigraficas = []
    for row in rows:
        try:
            taquigraficas.append({
                "fecha": row.get("FECHA DE SESION"),
                "tipo": row.get("TIPO DE SESION"),
                "sesion": row.get("NRO DE SESION"),
                "reunion": row.get("NRO DE REUNION"),
                "url": row.get("URL VESION TAQUIGRAFICA"),  # Asegúrate de corregir la clave si es necesario
            })
        except KeyError as e:
            print(f"Falta una clave en el JSON: {e}")
    return taquigraficas

def filter_taquigraficas(taquigraficas, years=None, session_types=None):
    """
    Filtra las versiones taquigráficas por año y tipo de sesión.
    """
    filtered = []
    for item in taquigraficas:
        try:
            # Extraer el año de la fecha
            year = datetime.strptime(item["fecha"], "%d-%m-%Y").year
        except (ValueError, KeyError) as e:
            print(f"Error al procesar la fecha '{item.get('fecha')}': {e}")
            continue
        
        # Filtrar por años
        if years and year not in years:
            continue
        
        # Filtrar por tipos de sesión (normalizar a mayúsculas)
        if session_types and item.get("tipo", "").strip().upper() not in [stype.upper() for stype in session_types]:
            continue
        
        filtered.append(item)
    return filtered

def download_pdf_and_metadata(url, metadata, output_folder, retries=MAX_RETRIES):
    """
    Descarga un archivo PDF desde la URL proporcionada y guarda su metadata en un archivo JSON.
    """
    os.makedirs(output_folder, exist_ok=True)  # Asegura que la carpeta exista

    # Verificar campos críticos
    fecha = metadata.get("fecha")
    tipo = metadata.get("tipo")
    if not fecha or not tipo:
        print(f"Metadata incompleta para la sesión: {metadata}")
        return

    # Formatear el nombre del archivo
    filename_base = f"{fecha}_{tipo.replace(' ', '_')}"
    pdf_path = os.path.join(output_folder, f"{filename_base}.pdf")
    metadata_path = os.path.join(output_folder, f"{filename_base}.json")
    
    # Verificar si el archivo ya existe
    if os.path.exists(pdf_path):
        print(f"Archivo ya descargado: {pdf_path}. Saltando descarga.")
        return  # Salir si ya existe

    # Intentar la descarga con reintentos
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            with open(pdf_path, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=8192):
                    pdf_file.write(chunk)
            print(f"Descargado: {pdf_path}")
            
            # Guardar metadata
            with open(metadata_path, "w") as metadata_file:
                json.dump(metadata, metadata_file, indent=4)
            print(f"Metadata guardada en {metadata_path}")
            return  # Salir después de una descarga exitosa
        except requests.exceptions.RequestException as e:
            print(f"Error al descargar el PDF (Intento {attempt}/{retries}) para la sesión del {fecha} desde {url}: {e}")
            if attempt == retries:
                print(f"Descarga fallida tras {retries} intentos.")
                
def process_senado():
    """
    Procesa las versiones taquigráficas del Senado.
    """
    print("Procesando datos del Senado...")
    json_data = fetch_taquigraficas_json(SENADO_URL)
    if not json_data:
        return

    # Extraer y filtrar datos
    taquigraficas = parse_taquigraficas(json_data)
    filtered_taquigraficas = filter_taquigraficas(taquigraficas, FILTER_YEARS, FILTER_SESSION_TYPES)

    for taquigrafica in filtered_taquigraficas:
        url = taquigrafica.get("url")
        if not url:
            print(f"URL faltante para la sesión del {taquigrafica.get('fecha')}")
            continue

        # Verificar si el archivo ya existe antes de la descarga
        fecha = taquigrafica.get("fecha")
        tipo = taquigrafica.get("tipo")
        filename_base = f"{fecha}_{tipo.replace(' ', '_')}"
        pdf_path = os.path.join(OUTPUT_FOLDER_SENADO, f"{filename_base}.pdf")

        if os.path.exists(pdf_path):
            print(f"Archivo ya descargado: {pdf_path}. Saltando descarga.")
            continue

        # Descargar PDF y guardar metadata
        download_pdf_and_metadata(url, taquigrafica, OUTPUT_FOLDER_SENADO)

        # Pausar después de cada descarga efectiva
        print(f"Pausa de {DOWNLOAD_DELAY} segundos antes de la próxima descarga...")
        time.sleep(DOWNLOAD_DELAY)
    

def main():
    process_senado()

if __name__ == "__main__":
    main()