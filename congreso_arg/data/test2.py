import pdfplumber
import textwrap

def extract_all_characters(pdf_path, max_pages=None):
    """
    Extrae todos los caracteres de un PDF, incluyendo texto, tipo de letra y tamaño,
    de todas las páginas especificadas.

    Args:
        pdf_path (str): Ruta al archivo PDF.
        max_pages (int): Número máximo de páginas a procesar. Si es None, se procesan todas.

    Returns:
        list: Lista de diccionarios con información de cada carácter extraído.
    """
    characters = []

    with pdfplumber.open(pdf_path) as pdf:
        # Determinar el número de páginas a procesar
        num_pages = len(pdf.pages) if max_pages is None else min(max_pages, len(pdf.pages))
        
        for i, page in enumerate(pdf.pages[:num_pages]):
            print(f"Extrayendo caracteres de la página {i + 1}...")
            for char in page.chars:
                characters.append({
                    "text": char["text"],
                    "font": char["fontname"],
                    "size": round(char["size"], 1),
                    "page": i + 1  # Agregar número de página para referencia
                })

    return characters

def group_characters_into_text_blocks(characters):
    """
    Agrupa caracteres en bloques de texto basados en tipo de letra y tamaño.
    
    Args:
        characters (list): Lista de caracteres extraídos, con sus atributos.
    
    Returns:
        list: Lista de bloques de texto, donde cada bloque es un diccionario con los atributos:
              - "text": Texto concatenado.
              - "font": Tipo de letra del bloque.
              - "size": Tamaño de letra del bloque.
              - "page": Página del bloque.
    """
    text_blocks = []
    current_block = {"text": "", "font": None, "size": None, "page": None}

    for char in characters:
        font = char["font"]
        size = char["size"]
        page = char["page"]
        text = char["text"]

        # Si el bloque actual está vacío, inicializamos con el primer carácter
        if not current_block["text"]:
            current_block.update({"text": text, "font": font, "size": size, "page": page})
            continue

        # Si el tipo o tamaño de letra cambia, almacenamos el bloque actual y comenzamos uno nuevo
        if current_block["font"] != font or current_block["size"] != size or current_block["page"] != page:
            text_blocks.append(current_block)
            current_block = {"text": text, "font": font, "size": size, "page": page}
        else:
            # Si no cambia, añadimos el carácter al texto del bloque actual
            current_block["text"] += text

    # Aseguramos guardar el último bloque
    if current_block["text"]:
        text_blocks.append(current_block)

    return text_blocks

def main(pdf_path, max_pages=10):
    """
    Flujo principal del programa. Extrae caracteres y agrupa en bloques de texto.

    Args:
        pdf_path (str): Ruta al archivo PDF.
        max_pages (int): Número máximo de páginas a procesar.
    """
    # Extraer todos los caracteres
    all_characters = extract_all_characters(pdf_path, max_pages=max_pages)

    # Agrupar caracteres en bloques de texto
    text_blocks = group_characters_into_text_blocks(all_characters)

    # Visualización de resultados iniciales
    print("Primeros bloques de texto:")
    for i, block in enumerate(text_blocks[:35]):  # Mostrar los primeros 35 bloques
        print(f"Bloque {i + 1}:")
        print(f"  Texto:")
        print(textwrap.fill(block['text'], width=80))  # Ajusta el ancho de línea
        print(f"  Fuente: {block['font']}, Tamaño: {block['size']}, Página: {block['page']}")
        print("-" * 40)

# Punto de entrada del programa
if __name__ == "__main__":
    pdf_path = "data/raw/senado/taquigraficas/13-04-2023_ORDINARIA.pdf"
    main(pdf_path, max_pages=10)