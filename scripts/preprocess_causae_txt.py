# scripts/preprocess_causae_txt.py
"""
Preprocess Hildegard von Bingen's Causae et Curae from a plain-text dump of
the archive.org "Full text of ..." HTML page (Kaiser 1903 edition, scanned
and OCR'd via Google Books), as an alternative to preprocess_causae.py,
which expects a Wikisource MediaWiki XML export.

The chunking + metadata procedure is kept identical to preprocess_causae.py
(chunk_latin_text, the output schema, the >=60-char filter, etc.). What
differs is the cleaning step: instead of stripping wikitext markup, this
script has to strip the page furniture of a scanned critical edition --
Google Books boilerplate, title pages, Kaiser's preface/apparatus criticus,
back-matter indices, running headers/footers, marginal line numbers,
footnote markers, and editorial sigla.

Note: this does NOT attempt to correct character-level OCR errors (e.g.
c/e, rn/m, u/n confusions such as "foit" for "fuit" or "£t" for "Et").
That would require a dedicated OCR-correction pass and is out of scope here.
"""
import json, re, html, unicodedata
from pathlib import Path

RAW_FILE = Path('corpus/raw/causaecurae/hildegard_causaecurae_archive.txt')
OUT_FILE = Path('corpus/processed/causaecurae_chunks.jsonl')

# The OCR dump runs: Google Books boilerplate -> title pages -> Kaiser's
# preface & apparatus criticus -> THE TREATISE -> colophon -> two
# back-of-book indices (INDEX RERUM ET NOMINUM, INDEX VERBORUM
# GERMANICORUM). These two strings bound the treatise text itself.
TEXT_START_MARKER = 'BEATAE HILDEGARDIS CAUSAE ET CUEAE'
TEXT_END_MARKER = 'Amen dicant omnia'


def extract_pre_text(txt_path):
    '''Pull the raw OCR text out of the archive.org "full text" <pre> block.'''
    raw = txt_path.read_text(encoding='utf-8', errors='replace')
    match = re.search(r'<pre>(.*?)</pre>', raw, re.DOTALL)
    if not match:
        raise ValueError(f'No <pre>...</pre> block found in {txt_path}')
    return html.unescape(match.group(1))


def isolate_treatise_text(text):
    '''Cut the OCR dump down to just the Causae et Curae text proper.'''
    start = text.find(TEXT_START_MARKER)
    end = text.find(TEXT_END_MARKER)
    if start == -1 or end == -1:
        raise ValueError('Could not locate start/end markers in OCR text; '
                          'the archive.org export may have a different layout.')
    end += len(TEXT_END_MARKER)
    return text[start + len(TEXT_START_MARKER):end]


def clean_ocr_text(text):
    '''Strip scanned-edition page furniture (the OCR-source analogue of
    clean_wikisource_xml's wikitext-markup stripping).'''
    # Rejoin words split by end-of-line hyphenation, before collapsing whitespace
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)

    # Running page header "CAUSAE ET CURAE LIB. <roman>. <page no.>", incl.
    # its many OCR misreadings ("CUBAE", "LrB", "IL", "ffl", "Up", ...)
    text = re.sub(r'\b[A-Z]{4,}\s+ET\s+[A-Z]{4,}\s+\S{1,4}\.?\s+\S{1,4}\.?', ' ', text)
    # Leftover all-caps header fragments: HILDEGARDIS, CAUSAE, CURAE and OCR
    # variants (HILDEGABDIS, etc.). None of these occur in the running Latin
    # prose, which is lowercase apart from single sentence-initial capitals.
    text = re.sub(r'\b[A-Z]{4,}\b', ' ', text)
    # Running footer "Hildegardis causae et curae ed. Kaiser. <n>" (also "Eaiser")
    text = re.sub(r'Hildegardis causae et curae ed\.\s*(Kaiser|Eaiser)\.\s*\d+', ' ', text)
    # Marginal line numbers (the editor's line counts, every 5th line).
    # Usually whitespace-delimited tokens, but sometimes OCR'd as glued
    # onto the end of the preceding word (e.g. "abs5 que" for "absque").
    text = re.sub(r'(?<=\s)\d{1,3}(?=\s)', ' ', text)
    text = re.sub(r'(?<=[a-zA-Z])\d{1,3}(?=\s)', '', text)
    # Footnote reference markers (superscript numerals OCR'd as "^)" / "1)")
    text = re.sub(r'\^?\)\s*', ' ', text)
    # Kaiser's editorial sigla: [] mark deletions/spurious passages, <> mark
    # additions, * and \u2020 (dagger) mark corrupt loci -- drop the marks,
    # keep the enclosed text
    text = re.sub(r'[\[\]<>*\u2020]', '', text)

    text = unicodedata.normalize('NFC', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def chunk_latin_text(text, max_chars=450):
    '''Split at sentence boundaries for Latin text. (identical to preprocess_causae.py)'''
    chunks, current = [], ''
    for sentence in re.split(r'(?<=[.?!])', text):
        current += sentence
        if len(current) >= max_chars:
            if current.strip(): chunks.append(current.strip())
            current = ''
    if current.strip(): chunks.append(current.strip())
    return chunks if chunks else [text]


def process_causae():
    raw_text = extract_pre_text(RAW_FILE)
    treatise_text = isolate_treatise_text(raw_text)
    clean_text = clean_ocr_text(treatise_text)
    chunks_text = chunk_latin_text(clean_text)

    all_chunks = []
    for i, chunk_text in enumerate(chunks_text):
        if len(chunk_text) < 60: continue  # Skip trivially short chunks
        chunk = {
            'chunk_id': f'causaecurae_chunk_{i:04d}',
            'source_text': 'Causae et Curae (Hildegard von Bingen), ed. Kaiser 1903',
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

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    print(f'Causae et Curae: {len(all_chunks)} chunks written to {OUT_FILE}')


if __name__ == '__main__':
    process_causae()
