# scripts/preprocess_suwen.py
import os, json, re, unicodedata
from pathlib import Path

RAW_DIR  = Path('corpus/raw/suwen')
OUT_FILE = Path('corpus/processed/suwen_chunks.jsonl')

# Classical Chinese sentence-final particles used as natural boundaries
SENTENCE_ENDINGS = ['。', '；', '？', '！']

def normalize(text):
    # NFC normalization
    text = unicodedata.normalize('NFC', text)
    # Remove byte-order marks and zero-width characters
    text = text.replace('\ufeff', '').replace('\u200b', '')
    # Normalize whitespace (Classical Chinese has no spaces, but clean anyway)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def chunk_classical_chinese(text, chapter_num, max_chars=400):
    '''Chunk at sentence boundaries, targeting ~400 Chinese characters.'''
    chunks = []
    current = ''
    for char in text:
        current += char
        if char in SENTENCE_ENDINGS and len(current) >= max_chars:
            chunks.append(current.strip())
            current = ''
    if current.strip():
        chunks.append(current.strip())
    return chunks

def process_suwen():
    all_chunks = []
    chapter_files = sorted(RAW_DIR.glob('suwen_ch*.txt'))
    
    for cf in chapter_files:
        chapter_num = int(re.search(r'ch(\d+)', cf.stem).group(1))
        raw_text = cf.read_text(encoding='utf-8')
        clean_text = normalize(raw_text)
        
        chunks = chunk_classical_chinese(clean_text, chapter_num)
        for i, chunk_text in enumerate(chunks):
            chunk = {
                'chunk_id': f'suwen_ch{chapter_num:02d}_chunk_{i:03d}',
                'source_text': 'Huangdi Neijing Suwen',
                'language': 'zh-classical',
                'script': 'han-traditional',
                'date_approx': -200,
                'date_label': '~300-100 BCE',
                'tradition': 'chinese-medicine',
                'chapter_num': chapter_num,
                'section': f'Chapter {chapter_num}',
                'char_count': len(chunk_text),
                'text': chunk_text,
            }
            all_chunks.append(chunk)
    
    OUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    print(f'Suwen: {len(all_chunks)} chunks written to {OUT_FILE}')

if __name__ == '__main__':
    process_suwen()
