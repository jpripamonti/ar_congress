"""Parse Argentine Senate stenographic transcript PDFs (versiones
taquigraficas) into per-session block tables.

Per-PDF pipeline (ported from the Jan 2025 test.py, behavior preserved
except where noted): extract characters with pdfplumber -> classify font
styles -> group characters into blocks by (font_style, size) -> reassign
trailing hyphens to italic blocks -> keep blocks from the bold-12 "1."
sumario marker on -> remove headers and empty blocks -> tag stenographer
blocks -> assign chapters -> identify speakers -> clean speaker names ->
consolidate consecutive same-speaker blocks.

Deliberate changes vs. the Jan 2025 version:
- Stenographer blocks (italic 12.0) are TAGGED (type="stenographer_note")
  instead of deleted: they carry context (votes, timestamps, incidents),
  and keeping them stops consolidation from fusing turns separated by an
  event. (Implements the original TODO.md note.)
- Output is persisted: one Parquet block table per session under
  data/processed/senado/blocks/, a per-session log under logs/, and a
  cumulative parse_stats.csv quality table.
- A missing sumario marker is recorded as an error, not a silent
  empty result.
- Fixed a trailing-hyphen bug: a block ending in "- " kept its hyphen
  AND prepended one to the next italic block.

Heuristics are calibrated against pdfplumber 0.11.5 (see pyproject.toml).
"""

import argparse
import contextlib
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pdfplumber

PARSER_VERSION = "0.2.0"

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "senado" / "taquigraficas"
OUT_DIR = REPO_ROOT / "data" / "processed" / "senado"
MANIFEST_PATH = REPO_ROOT / "raw_data_manifest.csv"

STATS_COLUMNS = [
    "session_id",
    "file_name",
    "characters_extracted",
    "blocks_generated",
    "blocks_after_marker_filter",
    "headers_removed",
    "empty_blocks_removed",
    "stenographer_blocks_tagged",
    "chapters_detected",
    "speech_blocks",
    "stenographer_notes",
    "other_blocks",
    "rows_written",
    "duration_s",
    "parser_version",
    "parsed_at",
    "error",
]


# ---------------------------------------------------------------------------
# Pipeline steps (Spanish docstrings kept verbatim from the Jan 2025 test.py)
# ---------------------------------------------------------------------------

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
            for char in page.chars:
                extracted_characters.append({
                    "text": char["text"],
                    "font": char["fontname"],
                    "size": round(char["size"], 1),
                    "page": i + 1  # Agregar número de página para referencia
                })

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
        elif "italic" in font_name or "oblique" in font_name:
            char["font_style"] = "italic"
        else:
            char["font_style"] = "normal"

    return extracted_characters


def group_characters_into_text_blocks(extracted_characters, verbose=False):
    """
    Agrupa caracteres en bloques de texto basados en tipo y tamaño de letra,
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
                # Fix: strip antes de rstrip — antes, un guión seguido de
                # espacios sobrevivía y además se duplicaba en el bloque cursivo
                current_block["text"] = current_block["text"].strip().rstrip("-")
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
            9.9 <= size <= 10.1 and
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


def tag_stenographer_blocks(blocks, verbose=False):
    """
    Etiqueta los bloques de taquígrafos (cursiva 12.0) con
    type="stenographer_note" en lugar de eliminarlos (TODO original:
    conservan información contextual — votaciones, horarios, incidentes —
    y mantenerlos evita que la consolidación fusione turnos separados por
    un evento).

    Args:
        blocks (list): Lista de bloques de texto.

    Returns:
        tuple: (lista de bloques, cantidad de bloques etiquetados)
    """
    tagged_count = 0

    for block in blocks:
        if block["font_style"] == "italic" and block["size"] == 12.0:
            block["type"] = "stenographer_note"
            tagged_count += 1
            if verbose: print(f"Bloque de taquígrafo etiquetado: {block['text'][:80]}")

    print(f"Etiquetado completo. Se etiquetaron {tagged_count} bloques de taquígrafos.")
    return blocks, tagged_count


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
    Los bloques de taquígrafos ya etiquetados pasan sin speaker.

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
    Un bloque sin speaker (p. ej. una nota de taquígrafo) corta la
    consolidación, preservando los turnos separados por eventos.

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


# ---------------------------------------------------------------------------
# Orchestration: per-session processing, persistence, stats
# ---------------------------------------------------------------------------

def process_pdf(pdf_path, verbose=False):
    """Run the full pipeline on one PDF. Returns (blocks, chapters, stats)."""
    stats = {}

    extracted = extract_all_characters(str(pdf_path), max_pages=None, verbose=verbose)
    stats["characters_extracted"] = len(extracted)

    extracted = classify_font_styles(extracted)

    blocks = group_characters_into_text_blocks(extracted, verbose=verbose)
    stats["blocks_generated"] = len(blocks)

    blocks = filter_blocks_by_marker(blocks, verbose=verbose)
    stats["blocks_after_marker_filter"] = len(blocks)
    if not blocks:
        stats["error"] = "marker_not_found"
        return [], {}, stats

    before = len(blocks)
    blocks = remove_headers(blocks, verbose=verbose)
    stats["headers_removed"] = before - len(blocks)

    before = len(blocks)
    blocks = remove_empty_blocks(blocks)
    stats["empty_blocks_removed"] = before - len(blocks)

    blocks, tagged = tag_stenographer_blocks(blocks, verbose=verbose)
    stats["stenographer_blocks_tagged"] = tagged

    blocks, chapters = assign_chapter_to_blocks(blocks, verbose=verbose)
    stats["chapters_detected"] = len(chapters)

    blocks = identify_speakers(blocks, verbose=verbose)
    blocks = clean_speaker_names(blocks, verbose=verbose)
    blocks = consolidate_speaker_blocks(blocks)

    return blocks, chapters, stats


def blocks_to_frame(blocks, chapters, meta):
    """Map pipeline blocks to the schema-v1 rows of the session table."""
    rows = []
    for seq, block in enumerate(blocks):
        speaker = block.get("speaker")
        chapter = block.get("capítulo")
        rows.append({
            "session_id": meta["session_id"],
            "session_date": meta["session_date"],
            "session_type": meta["session_type"],
            "sesion": meta["sesion"],
            "reunion": meta["reunion"],
            "seq": seq,
            "type": block.get("type") or ("speech" if speaker else "other"),
            "chapter": chapter,
            "chapter_title": chapters.get(chapter) if chapter else None,
            "speaker_raw": speaker,
            "text": block["text"],
            "pages": sorted(block["pages"]) if block.get("pages") else [],
            "font_style": block.get("font_style"),
            "size": block.get("size"),
            "source_pdf": meta["source_pdf"],
            "pdf_sha256": meta["pdf_sha256"],
            "parser_version": PARSER_VERSION,
        })
    return pd.DataFrame(rows)


def load_manifest():
    """Index raw_data_manifest.csv by pdf filename (empty dict if absent)."""
    if not MANIFEST_PATH.exists():
        return {}
    df = pd.read_csv(MANIFEST_PATH, dtype=str)
    return {row["pdf_filename"]: row for _, row in df.iterrows()}


def session_meta_for(pdf_path, manifest):
    """Session identity/provenance from the manifest, else from the sidecar."""
    row = manifest.get(pdf_path.name)
    if row is not None:
        date_iso = row["session_date_iso"]
        tipo, sesion, reunion = row["tipo"], row["sesion"], row["reunion"]
        sha = row["pdf_sha256"]
    else:
        sidecar = pdf_path.with_suffix(".json")
        meta = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
        try:
            date_iso = datetime.strptime(meta.get("fecha", ""), "%d-%m-%Y").date().isoformat()
        except ValueError:
            date_iso = ""
        tipo = meta.get("tipo", "")
        sesion = str(meta.get("sesion", "") or "")
        reunion = str(meta.get("reunion", "") or "")
        sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

    try:
        reunion_tag = f"r{int(reunion):02d}"
    except (TypeError, ValueError):
        reunion_tag = "rxx"
    session_id = f"{date_iso}_{reunion_tag}" if date_iso else pdf_path.stem

    return {
        "session_id": session_id,
        "session_date": date_iso,
        "session_type": tipo,
        "sesion": sesion,
        "reunion": reunion,
        "source_pdf": pdf_path.name,
        "pdf_sha256": sha,
    }


def parse_one(pdf_path_str, meta, verbose=False):
    """Worker: parse one PDF, write its Parquet table and log, return stats."""
    pdf_path = Path(pdf_path_str)
    out_path = OUT_DIR / "blocks" / f"{meta['session_id']}.parquet"
    log_path = OUT_DIR / "logs" / f"{meta['session_id']}.log"
    stats = {"session_id": meta["session_id"], "file_name": pdf_path.name}
    start = time.monotonic()

    try:
        with log_path.open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log):
            blocks, chapters, run_stats = process_pdf(pdf_path, verbose=verbose)
            stats.update(run_stats)
            if blocks:
                frame = blocks_to_frame(blocks, chapters, meta)
                frame.to_parquet(out_path, index=False)
                counts = frame["type"].value_counts()
                stats["rows_written"] = len(frame)
                stats["speech_blocks"] = int(counts.get("speech", 0))
                stats["stenographer_notes"] = int(counts.get("stenographer_note", 0))
                stats["other_blocks"] = int(counts.get("other", 0))
    except Exception as e:  # per-file isolation: one bad PDF must not kill the run
        stats["error"] = f"{type(e).__name__}: {e}"

    stats["duration_s"] = round(time.monotonic() - start, 1)
    stats["parser_version"] = PARSER_VERSION
    stats["parsed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return stats


def write_stats(new_rows, stats_path):
    """Merge this run's stats into parse_stats.csv (new rows win per file)."""
    new = pd.DataFrame(new_rows)
    if stats_path.exists():
        old = pd.read_csv(stats_path)
        if not new.empty:
            old = old[~old["file_name"].isin(new["file_name"])]
        new = pd.concat([old, new], ignore_index=True)
    if new.empty:
        return
    for col in STATS_COLUMNS:
        if col not in new.columns:
            new[col] = None
    new = new[STATS_COLUMNS].sort_values("file_name")
    new.to_csv(stats_path, index=False)


def main():
    ap = argparse.ArgumentParser(description="Parse Senate transcript PDFs into per-session Parquet block tables.")
    ap.add_argument("--only", metavar="FILENAME", help="process a single PDF by filename")
    ap.add_argument("--limit", type=int, help="process at most N PDFs")
    ap.add_argument("--force", action="store_true", help="re-parse sessions whose output already exists")
    ap.add_argument("--workers", type=int, default=6, help="parallel worker processes (default: 6)")
    ap.add_argument("--verbose", action="store_true", help="verbose per-step output in the session logs")
    args = ap.parse_args()

    if not RAW_DIR.is_dir():
        sys.exit(f"Raw data dir not found: {RAW_DIR} — is the data/ symlink in place? (see DATA.md)")
    (OUT_DIR / "blocks").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "logs").mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if args.only:
        pdfs = [p for p in pdfs if p.name == args.only]
        if not pdfs:
            sys.exit(f"No PDF named {args.only!r} in {RAW_DIR}")
    if args.limit:
        pdfs = pdfs[:args.limit]

    jobs, skipped = [], 0
    for pdf in pdfs:
        meta = session_meta_for(pdf, manifest)
        if (OUT_DIR / "blocks" / f"{meta['session_id']}.parquet").exists() and not args.force:
            skipped += 1
            continue
        jobs.append((pdf, meta))

    print(f"{len(pdfs)} PDFs selected, {skipped} already parsed, {len(jobs)} to process "
          f"(workers={args.workers}, parser {PARSER_VERSION})", flush=True)

    new_rows = []
    if jobs:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(parse_one, str(pdf), meta, args.verbose): meta["session_id"]
                for pdf, meta in jobs
            }
            for i, fut in enumerate(as_completed(futures), 1):
                stats = fut.result()
                new_rows.append(stats)
                flag = f"  ERROR: {stats['error']}" if stats.get("error") else ""
                print(f"[{i}/{len(jobs)}] {stats['session_id']} "
                      f"({stats.get('rows_written', 0)} rows, {stats['duration_s']}s){flag}", flush=True)

    stats_path = OUT_DIR / "parse_stats.csv"
    write_stats(new_rows, stats_path)

    errors = [r for r in new_rows if r.get("error")]
    print(f"\nDone: {len(new_rows)} parsed, {len(errors)} errors. Stats: {stats_path}")
    for r in errors:
        print(f"  {r['file_name']}: {r['error']}")


if __name__ == "__main__":
    main()
