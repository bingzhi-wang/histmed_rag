# scripts/preprocess_causae.py
import json, re, unicodedata
from pathlib import Path
from lxml import etree

RAW_FILE = Path('corpus/raw/causaecurae/causaecurae_wikisource.xml')
OUT_FILE = Path('corpus/processed/causaecurae_chunks.jsonl')

def clean_wikisource_xml(xml_path):
    '''Extract text from Wikisource MediaWiki XML export.'''
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    ns = {'mw': 'http://www.mediawiki.org/xml/export-0.10/'}
    # Get the text node from MediaWiki XML
    text_nodes = root.findall('.//mw:text', ns)
    if not text_nodes:
        # Try without namespace
        text_nodes = root.findall('.//text')
    full_text = ' '.join(n.text or '' for n in text_nodes)
    # Remove wikitext markup
    full_text = re.sub(r'\[\[.*?\]\]', '', full_text)  # Remove wiki links
    full_text = re.sub(r'\{\{.*?\}\}', '', full_text)  # Remove templates
    full_text = re.sub(r'==+.*?==+', '', full_text)       # Remove headers
    full_text = re.sub(r"'''+", '', full_text)            # Remove bold/italic markup
    full_text = unicodedata.normalize('NFC', full_text)
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    return full_text

def chunk_latin_text(text, max_chars=450):
    '''Split at sentence boundaries for Latin text.'''
    chunks, current = [], ''
    for sentence in re.split(r'(?<=[.?!])', text):
        current += sentence
        if len(current) >= max_chars:
            if current.strip(): chunks.append(current.strip())
            current = ''
    if current.strip(): chunks.append(current.strip())
    return chunks if chunks else [text]

def process_causae():
    raw_text = clean_wikisource_xml(RAW_FILE)
    chunks_text = chunk_latin_text(raw_text)
    all_chunks = []
    for i, chunk_text in enumerate(chunks_text):
        if len(chunk_text) < 60: continue  # Skip trivially short chunks
        chunk = {
            'chunk_id': f'causaecurae_chunk_{i:04d}',
            'source_text': 'Causae et Curae (Hildegard von Bingen)',
            'language': 'la-medieval',
            'script': 'latin',
            'date_approx': 1155,
            'date_label': '~1150-1160 CE',
            'tradition': 'medieval-european',
            'chapter_num': None,
            'section': f'Passage {i+1}',
            'char_count': len(chunk_text),
            'text': chunk_text,
        }
        all_chunks.append(chunk)
    
    OUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    print(f'Causae et Curae: {len(all_chunks)} chunks written to {OUT_FILE}')

if __name__ == '__main__':
    process_causae()
