# scripts/preprocess_hippocrates.py
"""
Preprocess two Hippocratic works (Greek + parallel Perseus English) into
section-aligned chunks. Replaces preprocess_perinouson.py.

Layout: corpus/raw/hippocrates/{depriscamedicina,prognosticon}_{gr,eng}.xml
"""
import json, re, copy, unicodedata
from pathlib import Path
from lxml import etree

RAW_DIR  = Path('corpus/raw/hippocrates')
OUT_FILE = Path('corpus/processed/hippocrates_chunks.jsonl')

TEI = 'http://www.tei-c.org/ns/1.0'
Q   = lambda tag: f'{{{TEI}}}{tag}'

MAX_SECTION_CHARS = 1000   # sections longer than this are split; rarely hit here
MIN_ALIGN_RATIO   = 0.60   # warn below this Greek-to-English match rate

WORKS = [
    {'key': 'depriscamedicina',
     'grc': 'depriscamedicina_gr.xml', 'eng': 'depriscamedicina_eng.xml',
     'source_text': 'Hippocrates, On Ancient Medicine (De prisca medicina)',
     'source_urn': 'urn:cts:greekLit:tlg0627.tlg001',
     'date_approx': -420, 'date_label': '~420-350 BCE'},
    {'key': 'prognosticon',
     'grc': 'prognosticon_gr.xml', 'eng': 'prognosticon_eng.xml',
     'source_text': 'Hippocrates, Prognostic (Prognosticon)',
     'source_urn': 'urn:cts:greekLit:tlg0627.tlg003',
     'date_approx': -400, 'date_label': '~400 BCE'},
]

# Non-running-text elements to drop (apparatus, editor notes, refs, headers)
STRIP = [Q(t) for t in ('note', 'bibl', 'ref', 'head', 'gap',
                        'milestone', 'figure', 'label', 'teiHeader')]

def _clean(text):
    text = unicodedata.normalize('NFC', text or '')
    text = text.replace('\ufeff', '').replace('\u200b', '')
    return re.sub(r'\s+', ' ', text).strip()

def _section_text(div):
    div = copy.deepcopy(div)                       # don't mutate the tree
    etree.strip_elements(div, *STRIP, with_tail=False)  # keep tail = main text
    return _clean(' '.join(div.itertext()))

def parse_sections(xml_path):
    """Return ordered list of (section_ref, text), robust across TEI layouts."""
    root = etree.parse(str(xml_path)).getroot()
    body = root.find(f'.//{Q("body")}')
    if body is None:
        body = root
    # Try selectors in order of specificity
    divs = (body.findall(f'.//{Q("div")}[@subtype="section"]')
            or body.findall(f'.//{Q("div")}[@type="textpart"]')
            or body.findall(f'.//{Q("div1")}[@type="section"]')
            or body.findall(f'.//{Q("div1")}')
            or [d for d in body.iter(Q('div')) if d.get('n')])
    order, sections = [], {}
    for d in divs:
        n = (d.get('n') or '').strip()
        if not n:
            continue
        txt = _section_text(d)
        if txt and n not in sections:
            sections[n] = txt
            order.append(n)
    return order, sections

def _split(text):
    if len(text) <= MAX_SECTION_CHARS:
        return [text]
    parts, cur = [], ''
    for s in re.split(r'(?<=[.;·])\s*', text):
        cur += s + ' '
        if len(cur) >= MAX_SECTION_CHARS:
            parts.append(cur.strip()); cur = ''
    if cur.strip():
        parts.append(cur.strip())
    return parts or [text]

def process_work(work):
    grc_order, grc = parse_sections(RAW_DIR / work['grc'])
    _,        eng = parse_sections(RAW_DIR / work['eng'])
    matched = sum(1 for n in grc_order if n in eng)
    ratio   = matched / len(grc_order) if grc_order else 0
    print(f"  {work['key']}: {len(grc_order)} grc sections, "
          f"{len(eng)} eng sections, {matched} aligned ({ratio:.0%})")
    if grc_order and ratio < MIN_ALIGN_RATIO:
        print(f"    ⚠ low alignment — check section numbering; "
              f"unmatched chunks will be translated by translate_chunks.py")
    if grc_order:
        print(f"    sample refs: {grc_order[:5]}")

    out = []
    for n in grc_order:
        eng_text = eng.get(n, '')
        for i, piece in enumerate(_split(grc[n])):
            out.append({
                'chunk_id': f"{work['key']}_sec{n}_chunk_{i:03d}",
                'source_text': work['source_text'],
                'source_urn': work['source_urn'],
                'language': 'grc',
                'script': 'greek-polytonic',
                'date_approx': work['date_approx'],
                'date_label': work['date_label'],
                'tradition': 'greek-medicine',
                'section': f"Section {n}",
                'section_ref': n,
                'char_count': len(piece),
                'text': piece,                       # Greek original
                'text_translation': eng_text,        # Perseus English (may be '')
                'translation_source': 'perseus-parallel' if eng_text else '',
            })
    return out

def main():
    all_chunks = []
    for work in WORKS:
        print(f"Processing {work['key']}...")
        all_chunks += process_work(work)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    print(f"\nHippocrates: {len(all_chunks)} chunks written to {OUT_FILE}")

if __name__ == '__main__':
    main()
