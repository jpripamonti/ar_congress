import os
import pdfplumber
import re
import pandas as pd

def extract_all_characters(pdf_path, max_pages=None, verbose=False):
    """
    Extrae todos los caracteres de un PDF, incluyendo texto, tipo de letra y
    tamaño, de todas las páginas especificadas.

    Args:
        pdf_path (str): Ruta al archivo PDF.
        max_pages (int or None): Número máximo de páginas a procesar. 
        Si es None, se procesan todas.

    Returns:
        list: Lista de diccionarios con información de cada carácter extraído.
    """
    extracted_characters = []

    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages) if max_pages is None else min(max_pages, len(pdf.pages))
        print(f"Procesando un total de {num_pages} páginas del PDF...") if verbose else None

        for i, page in enumerate(pdf.pages[:num_pages]):
            page_characters = 0  # Contador para esta página
            for char in page.chars:
                extracted_characters.append({
                    "text": char["text"],
                    "font": char["fontname"],
                    "size": round(char["size"], 1),
                    "page": i + 1  # Agregar número de página para referencia
                })
                page_characters += 1

    print(f"Extracción completa. Se extrajeron {len(extracted_characters)} caracteres en total.")
    return extracted_characters


def classify_font_styles(extracted_characters):
    """
    Clasifica el tipo de letra de los caracteres extraídos en 'normal', 'bold' o 'italic'.

    Args:
        extracted_characters (list): Lista de caracteres extraídos, donde cada carácter
                                     es un diccionario con el atributo 'font'.

    Returns:
        list: Lista de caracteres con un atributo adicional 'font_style'.
    """
    for char in extracted_characters:
        font_name = char["font"].lower()  # Convertir a minúsculas para comparación
        if "bold" in font_name:
            char["font_style"] = "bold"
        elif "italic" in font_name or "oblique" in font_name:  # Corregido
            char["font_style"] = "italic"
        else:
            char["font_style"] = "normal"
    
    return extracted_characters

def group_characters_into_text_blocks(extracted_characters, verbose=False):
    """
    Agrupa caracteres en bloques de texto basados en tipo de letra, tamaño y fuente,
    rastreando todas las páginas que abarcan los caracteres.

    Args:
        extracted_characters (list): Lista de caracteres extraídos, con sus atributos.

    Returns:
        list: Lista de bloques de texto, donde cada bloque es un diccionario con los atributos:
              - "text": Texto concatenado.
              - "font": Fuente original del bloque.
              - "font_style": Tipo de letra del bloque.
              - "size": Tamaño de letra del bloque.
              - "pages": Lista de páginas únicas donde aparece el bloque.
    """
    text_blocks = []
    current_block = {"text": "", "font": None, "font_style": None, "size": None, "pages": []}

    if verbose: print("Iniciando el agrupamiento de caracteres en bloques de texto...")

    for char in extracted_characters:
        font = char["font"]
        font_style = char["font_style"]
        size = char["size"]
        page = char["page"]
        text = char["text"]

        if not current_block["text"]:  # Inicializamos el bloque actual
            current_block.update({"text": text, "font": font, "font_style": font_style, "size": size, "pages": [page]})
            continue

        # Si el tipo o tamaño de letra cambia, almacenamos el bloque actual
        if current_block["font_style"] != font_style or current_block["size"] != size:
            text_blocks.append(current_block)
            current_block = {"text": text, "font": font, "font_style": font_style, "size": size, "pages": [page]}
        else:
            current_block["text"] += text
            if page not in current_block["pages"]:  # Aseguramos rastrear todas las páginas
                current_block["pages"].append(page)

    # Aseguramos guardar el último bloque
    if current_block["text"]:
        text_blocks.append(current_block)

    if verbose:
        print(f"Agrupamiento completo. Se generaron {len(text_blocks)} bloques de texto.")

    # Reasignación de guiones
    text_blocks = reassign_hyphens_to_italic_blocks(text_blocks, verbose=verbose)

    return text_blocks


def reassign_hyphens_to_italic_blocks(text_blocks, verbose=False):
    """
    Mueve los guiones finales al inicio del siguiente bloque cursivo, si corresponde.

    Args:
        text_blocks (list): Lista de bloques de texto agrupados.
        verbose (bool): Imprime información adicional si es True.

    Returns:
        list: Lista de bloques con los guiones reasignados.
    """
    for i in range(len(text_blocks) - 1):
        current_block = text_blocks[i]
        next_block = text_blocks[i + 1]

        # Verificar si el bloque actual termina con un guión
        if current_block["text"].strip().endswith("-"):
            # Verificar si el siguiente bloque es cursivo
            if next_block["font_style"] == "italic":
                # Mover el guión al siguiente bloque
                if verbose:
                    print(f"Reasignando guión de '{current_block['text']}' al inicio de '{next_block['text']}'")
                current_block["text"] = current_block["text"].rstrip("-").strip()  # Quitar el guión del bloque actual
                next_block["text"] = "-" + next_block["text"].strip()  # Añadir el guión al siguiente bloque

    return text_blocks


def filter_blocks_by_marker(text_blocks, marker_text="1.", 
                            marker_font="bold", 
                            marker_size=12.0,
                            verbose=False):
    """
    Filtra bloques de texto comenzando desde un marcador específico.

    Args:
        text_blocks (list): Lista de bloques de texto generados por group_characters_into_text_blocks.
        marker_text (str): Texto del marcador que indica el inicio del análisis.
        marker_font (str): Tipo de letra del marcador.
        marker_size (float): Tamaño de letra del marcador.

    Returns:
        list: Lista de bloques de texto a partir del marcador, incluyendo el marcador.
    """
    marker_found = False
    blocks_from_marker = []

    if verbose: print(f"Buscando el marcador '{marker_text}' con fuente '{marker_font}' y tamaño {marker_size}...")

    for block in text_blocks:
        # Verificar si el bloque es el marcador
        if not marker_found:
            if (
                block["text"].strip().startswith(marker_text) and
                marker_font in block["font_style"] and
                block["size"] == marker_size
            ):
                marker_found = True
                blocks_from_marker.append(block)  # Incluir el bloque del marcador
                print(f"Marcador encontrado en el bloque: {block}")
            continue

        # Una vez encontrado el marcador, añadir los bloques restantes
        blocks_from_marker.append(block)

    if not marker_found:
        print("=== Advertencia: No se encontró el marcador ===")

    print(f"Filtrado completo. Se seleccionaron {len(blocks_from_marker)} bloques a partir del marcador.")
    return blocks_from_marker


def remove_headers(blocks, verbose=False):
    """
    Filtra los bloques y elimina encabezados específicos, incluyendo:
    - "Dirección General de Taquígrafos".
    - Bloques que comienzan y terminan con “ y ”.
    - Fechas con número de página (e.g., "13 de abril de 2023 Pág. X").

    Args:
        blocks (list): Lista de bloques de texto.

    Returns:
        list: Lista de bloques sin los encabezados.
    """
    blocks_without_headers = []
    removed_headers_count = 0

    for block in blocks:
        text = block["text"].strip()
        font_style = block["font_style"]
        size = block["size"]

        # Eliminar encabezados específicos
        if (
            text in ["Dirección General de Taquígrafos", "Dirección General de Taquígrafos "] and
            font_style == "italic" and
            size == 12.0
        ):
            if verbose: print(f"Encabezado eliminado: {block}")
            removed_headers_count += 1
            continue

        # Eliminar encabezados entre comillas especiales
        if (
            text.startswith("“") and
            text.endswith("”") and
            font_style == "normal" and
            size == 10.0
        ):
            if verbose: print(f"Encabezado eliminado: {block}")
            removed_headers_count += 1
            continue

        # Eliminar fechas con número de página
        if (
            font_style == "normal" and
            9.9 <= size <= 10.1  and
            re.match(r"^\d{1,2} .* Pág\. \d+ ?$", text)
        ):
            if verbose: print(f"Encabezado eliminado: {block}")
            removed_headers_count += 1
            continue

        # Mantener bloques no encabezados
        blocks_without_headers.append(block)

    print(f"Eliminación de encabezados completa. Se eliminaron {removed_headers_count} encabezados.")
    print(f"Cantidad de bloques restantes: {len(blocks_without_headers)}.")
    return blocks_without_headers


def remove_empty_blocks(blocks):
    """
    Elimina los bloques de texto vacíos o que contienen solo espacios en blanco.

    Args:
        blocks (list): Lista de bloques de texto.

    Returns:
        list: Lista de bloques no vacíos.
    """
    initial_count = len(blocks)
    non_empty_blocks = [block for block in blocks if block["text"].strip()]
    removed_count = initial_count - len(non_empty_blocks)

    print(f"Se eliminaron {removed_count} bloques vacíos. Quedan {len(non_empty_blocks)} bloques no vacíos.")
    return non_empty_blocks

def remove_tachygrapher_blocks(blocks, verbose=False):
    """
    Elimina bloques de texto correspondientes a taquígrafos.

    Args:
        blocks (list): Lista de bloques de texto.

    Returns:
        list: Lista de bloques sin los textos de taquígrafos.
    """
    filtered_blocks = []
    tachygrapher_count = 0

    for block in blocks:
        text = block["text"].strip()
        font_style = block["font_style"]
        size = block["size"]

        # Identificar bloques de taquígrafos (guion inicial o entre paréntesis)
        if font_style == "italic" and size == 12.0:
            if verbose: print(f"Bloque de taquígrafo eliminado: {block}")
            tachygrapher_count += 1
            continue  # Saltar bloques de taquígrafos

        filtered_blocks.append(block)

    print(f"Eliminación completa. Se eliminaron {tachygrapher_count} bloques de taquígrafos.")
    print(f"Cantidad de bloques restantes: {len(filtered_blocks)}.")
    return filtered_blocks


def assign_chapter_to_blocks(blocks, verbose=False):
    """
    Identifica y divide bloques de capítulos, luego asigna un número de capítulo
    a cada bloque y guarda los títulos de los capítulos en una estructura separada.

    Args:
        blocks (list): Lista de bloques de texto.

    Returns:
        tuple: (lista de bloques actualizada, diccionario de capítulos)
               - blocks_with_chapters: Bloques con el capítulo asignado.
               - chapters: Diccionario con números de capítulo como claves y títulos como valores.
    """
    chapters = {}  # Diccionario para almacenar los títulos de capítulos
    current_chapter = None
    blocks_with_chapters = []
    chapter_count = 0

    for block in blocks:
        text = block["text"].strip()
        font_style = block["font_style"]
        size = block["size"]
        
        # Detectar si el bloque es un título de capítulo
        if re.match(r"^\d+\.\s", text) and font_style == "bold":
            if verbose: print(f"Título de capítulo detectado (antes de dividir): {block}")

            # Dividir el bloque por espacios dobles si es necesario
            if "  " in text:
                if verbose: print("Bloque de capítulo contiene espacios dobles. Dividiendo...")
                parts = text.split("  ")
                for i, part in enumerate(parts):
                    if part.strip():
                        new_block = {
                            "text": part.strip(),
                            "font_style": font_style,
                            "size": size,
                            "pages": block["pages"]
                        }
                        if verbose: print(f"Nuevo bloque creado: {new_block}")

                        # Procesar la primera parte como título del capítulo
                        if i == 0:
                            chapter_number = part.split('.')[0]  # Extraer el número del capítulo
                            chapters[chapter_number] = part.strip()
                            current_chapter = chapter_number
                            chapter_count += 1
                            if verbose: print(f"Capítulo asignado: {chapter_number} -> {part.strip()}")
                        else:
                            # Procesar las partes restantes como bloques normales
                            new_block["capítulo"] = current_chapter
                            blocks_with_chapters.append(new_block)
            else:
                # Bloque sin espacios dobles, procesar como título de capítulo directamente
                chapter_number = text.split('.')[0]  # Extraer el número del capítulo
                chapters[chapter_number] = text
                current_chapter = chapter_number
                chapter_count += 1
                if verbose: print(f"Capítulo asignado: {chapter_number} -> {text}")
            continue  # No incluir títulos de capítulo en la salida final

        # Asignar el capítulo actual al bloque
        block["capítulo"] = current_chapter
        blocks_with_chapters.append(block)

    print(f"Asignación de capítulos completa. Se detectaron {chapter_count} capítulos.")
    print(f"Cantidad de bloques con capítulos asignados: {len(blocks_with_chapters)}.")
    return blocks_with_chapters, chapters


def identify_speakers(blocks, verbose=False):
    """
    Identifica los bloques dichos por speakers y asigna los textos de los speakers.
    No clasifica bloques de taquígrafos, ya que estos fueron eliminados previamente.

    Args:
        blocks (list): Lista de bloques de texto.
    
    Returns:
        list: Lista de bloques con el atributo "speaker" asignado.
    """
    annotated_blocks = []
    current_speaker = None  # Para rastrear el speaker actual
    speaker_blocks_count = 0

    for block in blocks:
        text = block["text"].strip()
        font_style = block["font_style"]
        size = block["size"]

        # Caso 1: Identificar nombres de speakers (negrita)
        if font_style == "bold" and size == 12.0:
            current_speaker = text  # Actualizamos el speaker actual
            if verbose: print(f"Speaker identificado: {current_speaker}")
            continue  # No incluimos este bloque en la salida final

        # Caso 2: Asignar texto al speaker actual
        if font_style == "normal" and size == 12.0 and current_speaker:
            block["speaker"] = current_speaker  # Asignar texto al último speaker identificado
            annotated_blocks.append(block)
            speaker_blocks_count += 1
            continue

        # Caso 3: Bloques sin speaker definido
        annotated_blocks.append(block)

    print(f"Identificación de speakers completa. Se anotaron {speaker_blocks_count} bloques con speakers.")
    return annotated_blocks

def consolidate_speaker_blocks(blocks):
    """
    Consolida bloques consecutivos del mismo speaker en un único bloque.
    
    Args:
        blocks (list): Lista de bloques con atributos "text" y "speaker".
    
    Returns:
        list: Lista de bloques consolidados.
    """
    consolidated_blocks = []
    current_block = None
    consolidated_count = 0

    for block in blocks:
        # Obtener el speaker de forma segura
        block_speaker = block.get("speaker")

        # Caso 1: Si es un bloque sin speaker, guardar directamente
        if not block_speaker:
            if current_block:
                consolidated_blocks.append(current_block)
                current_block = None
            consolidated_blocks.append(block)
            continue

        # Caso 2: Consolida bloques consecutivos del mismo speaker
        if current_block and block_speaker == current_block.get("speaker"):
            # Concatenar texto y combinar páginas
            current_block["text"] += " " + block["text"]
            current_block["pages"] = list(set(current_block["pages"] + block["pages"]))
        else:
            # Si cambia el speaker, guardar el bloque actual y comenzar uno nuevo
            if current_block:
                consolidated_blocks.append(current_block)
                consolidated_count += 1
            current_block = block

    # Añadir el último bloque si existe
    if current_block:
        consolidated_blocks.append(current_block)
        consolidated_count += 1

    print(f"Consolidación completa. Se consolidaron {consolidated_count} bloques de texto.")
    return consolidated_blocks

def clean_speaker_names(blocks, verbose=False):
    """
    Limpia los nombres de los speakers eliminando el punto y guión al final.

    Args:
        blocks (list): Lista de bloques con atributos "speaker".

    Returns:
        list: Lista de bloques con nombres de speakers corregidos.
    """
    cleaned_speakers_count = 0

    for block in blocks:
        if "speaker" in block and block["speaker"]:
            original_speaker = block["speaker"]
            # Eliminar ".-" al final del nombre del speaker
            block["speaker"] = re.sub(r"\.\-$", "", block["speaker"]).strip()
            if original_speaker != block["speaker"]:
                if verbose: print(f"Speaker limpiado: '{original_speaker}' -> '{block['speaker']}'")
                cleaned_speakers_count += 1

    print(f"Limpieza completa. Se limpiaron {cleaned_speakers_count} nombres de speakers.")
    return blocks

# Ruta a la carpeta con los PDFs
pdf_folder = "data/raw/senado/taquigraficas"

# Verbosidad configurada como variable en el flujo principal
verbose = True

# Listar todos los PDFs en la carpeta
pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")][:1]  # Limitar a 1 archivo para pruebas

print(f"Se encontraron {len(pdf_files)} archivos PDF en la carpeta: {pdf_folder}")

processing_stats = []  # Inicializar lista de estadísticas

for pdf_file in pdf_files:
    pdf_path = os.path.join(pdf_folder, pdf_file)  # Construir ruta completa
    stats = {"file_name": pdf_file}  # Diccionario para estadísticas
    try:
        # Extraer caracteres
        extracted_characters = extract_all_characters(pdf_path, max_pages=None, verbose=verbose)
        stats["characters_extracted"] = len(extracted_characters)

        # Clasificar estilos de fuente
        extracted_characters = classify_font_styles(extracted_characters)

        # Agrupar bloques
        text_blocks = group_characters_into_text_blocks(extracted_characters, verbose=verbose)
        stats["blocks_generated"] = len(text_blocks)

        # Filtrar bloques por marcador
        text_blocks = filter_blocks_by_marker(text_blocks, verbose=verbose)
        stats["blocks_after_marker_filter"] = len(text_blocks)

        # Remover encabezados
        blocks_before_headers = len(text_blocks)
        text_blocks = remove_headers(text_blocks, verbose=verbose)
        stats["headers_removed"] = blocks_before_headers - len(text_blocks)

        # Eliminar bloques vacíos
        blocks_before_empty_removal = len(text_blocks)
        text_blocks = remove_empty_blocks(text_blocks)  # No requiere verbose
        stats["empty_blocks_removed"] = blocks_before_empty_removal - len(text_blocks)

        # Eliminar bloques de taquígrafos
        blocks_before_tachygrapher_removal = len(text_blocks)
        text_blocks = remove_tachygrapher_blocks(text_blocks, verbose=verbose)
        stats["tachygrapher_blocks_removed"] = blocks_before_tachygrapher_removal - len(text_blocks)

        # Asignar capítulos
        text_blocks, chapters = assign_chapter_to_blocks(text_blocks, verbose=verbose)
        stats["chapters_detected"] = len(chapters)

        # Identificar speakers
        text_blocks = identify_speakers(text_blocks, verbose=verbose)

        # Limpiar nombres de speakers
        text_blocks = clean_speaker_names(text_blocks, verbose=verbose)

        # Consolidar bloques
        text_blocks = consolidate_speaker_blocks(text_blocks)

        # Contar bloques sin speaker
        blocks_without_speaker = [block for block in text_blocks if "speaker" not in block or not block["speaker"]]
        stats["blocks_without_speaker"] = len(blocks_without_speaker)
        stats["final_blocks"] = len(text_blocks)

        # Agregar estadísticas a la lista
        processing_stats.append(stats)

    except Exception as e:
        stats["error"] = f"{type(e).__name__}: {e}"  # Registrar error detallado
        processing_stats.append(stats)

# Generar tabla final
stats_df = pd.DataFrame(processing_stats)

# Ordenar columnas
columns_order = [
    "file_name",
    "characters_extracted",
    "blocks_generated",
    "blocks_after_marker_filter",
    "headers_removed",
    "empty_blocks_removed",
    "tachygrapher_blocks_removed",
    "chapters_detected",
    "blocks_without_speaker",
    "final_blocks",
    "error"
]

# Ensure all expected columns exist
for col in columns_order:
    if col not in stats_df.columns:
        stats_df[col] = None

# Reorder columns
stats_df = stats_df[columns_order]

# Imprimir y guardar la tabla
print("\nEstadísticas de procesamiento:")
print(stats_df.to_string(index=False))
stats_df.to_csv("processing_stats.csv", index=False)