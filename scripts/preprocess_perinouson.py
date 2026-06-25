# scripts/preprocess_perinouson.py
import json, re, unicodedata
from pathlib import Path
from lxml import etree

RAW_GRK  = Path('corpus/raw/perinouson/perinouson_book1.xml')
RAW_ENG  = Path('corpus/raw/perinouson/perinouson_eng.xml')
OUT_FILE = Path('corpus/processed/perinouson_chunks.jsonl')

# TEI namespace
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

def strip_tei(xml_path):
    '''Parse TEI-XML and extract text by section with metadata.'''
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    sections = []
    
    # Find all div elements (chapters/sections in TEI)
    for div in root.iter('{http://www.tei-c.org/ns/1.0}div'):
        n = div.get('n', '')
        type_ = div.get('type', '')
        # Get all text content of this div
        texts = []
        for elem in div.iter():
            if elem.text:  texts.append(elem.text.strip())
            if elem.tail: texts.append(elem.tail.strip())
        full_text = ' '.join(t for t in texts if t)
        full_text = unicodedata.normalize('NFC', full_text)
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        if len(full_text) > 80:  # Skip trivially short sections
            sections.append({'n': n, 'type': type_, 'text': full_text})
    return sections

def chunk_greek_section(section_text, max_chars=500):
    '''Split on sentence-ending punctuation (. ; ·) at target length.'''
    chunks, current = [], ''
    for sentence in re.split(r'(?<=[.;·])', section_text):
        current += sentence
        if len(current) >= max_chars:
            if current.strip(): chunks.append(current.strip())
            current = ''
    if current.strip(): chunks.append(current.strip())
    return chunks if chunks else [section_text]

def process_perinouson():
    sections = strip_tei(RAW_GRK)
    all_chunks = []
    for sec in sections:
        for i, chunk_text in enumerate(chunk_greek_section(sec['text'])):
            chunk = {
                'chunk_id': f'perinouson_sec{sec["n"]}_chunk_{i:03d}',
                'source_text': 'Hippocratic De Morbis (Peri Nouson)',
                'language': 'grc',
                'script': 'greek-polytonic',
                'date_approx': -400,
                'date_label': '~420-370 BCE',
                'tradition': 'greek-medicine',
                'chapter_num': sec['n'],
                'section': f'Section {sec["n"]} ({sec["type"]})',
                'char_count': len(chunk_text),
                'text': chunk_text,
            }
            all_chunks.append(chunk)
    
    OUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    print(f'Peri Nouson: {len(all_chunks)} chunks written to {OUT_FILE}')

if __name__ == '__main__':
    process_perinouson()
