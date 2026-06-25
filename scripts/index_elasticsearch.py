# scripts/index_elasticsearch.py
import json
import re
from pathlib import Path
from elasticsearch import Elasticsearch, helpers
from elasticsearch.helpers import BulkIndexError
from tqdm import tqdm

ES_INDEX = 'histmed_corpus'
PROCESSED = Path('corpus/processed')

es = Elasticsearch('http://localhost:9200')

# Define index mapping
# We use 'standard' analyzer for Latin/Greek and custom for Chinese
INDEX_MAPPING = {
    'mappings': {
        'properties': {
            'text': {'type': 'text', 'analyzer': 'standard'},
            'chunk_id': {'type': 'keyword'},
            'source_text': {'type': 'keyword'},
            'language': {'type': 'keyword'},
            'tradition': {'type': 'keyword'},
            'date_approx': {'type': 'integer'},
            'date_ref': {'type': 'keyword'},      # original value when not a clean int
            'chapter_num': {'type': 'integer'},   # genuine numeric chapter, nullable
            'chapter_ref': {'type': 'keyword'},   # raw citation/reference, never dropped
            'section': {'type': 'text'},
        }
    },
    'settings': {
        'number_of_shards': 1,
        'number_of_replicas': 0,
        # 'similarity' must be a nested object, not a dotted-string key.
        'similarity': {
            'default': {
                'type': 'BM25',
                'k1': 1.5,
                'b': 0.75
            }
        }
    }
}


def parse_int_field(raw):
    """Return (int_or_None, original_ref_str_or_None).

    Preserves the original value so nothing is silently dropped, and extracts a
    genuine integer only when one is unambiguously present.
    """
    if raw in ('', None):
        return None, None
    if isinstance(raw, int):
        return raw, str(raw)
    raw_str = str(raw).strip()
    # CTS URN: urn:cts:{namespace}:{work}:{passage} -> use the passage part only.
    # We must NOT scrape digits from the work id (e.g. tlg0627) — those aren't chapters.
    if raw_str.startswith('urn:cts:'):
        parts = raw_str.split(':')
        passage = parts[4] if len(parts) >= 5 else ''
        m = re.match(r'(\d+)', passage)
        return (int(m.group(1)) if m else None), raw_str
    # Plain integer string.
    if re.fullmatch(r'-?\d+', raw_str):
        return int(raw_str), raw_str
    # Something like "Book 3" / "ch. 12" — grab the first standalone integer.
    m = re.search(r'\b(\d+)\b', raw_str)
    return (int(m.group(1)) if m else None), raw_str


# Create or recreate the index
if es.indices.exists(index=ES_INDEX):
    es.indices.delete(index=ES_INDEX)
es.indices.create(index=ES_INDEX, body=INDEX_MAPPING)
print(f'Created ES index: {ES_INDEX}')


def generate_docs():
    for jsonl_file in PROCESSED.glob('*.jsonl'):
        with open(jsonl_file, encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f'Skipping bad JSON in {jsonl_file.name} line {line_num}: {e}')
                    continue

                if not doc.get('text', '').strip():
                    continue

                if not doc.get('chunk_id'):
                    print(f'Skipping doc with missing chunk_id in {jsonl_file.name} line {line_num}')
                    continue

                # chapter_num: keep an int when there is one, always keep the raw ref.
                ch_num, ch_ref = parse_int_field(doc.get('chapter_num'))
                doc['chapter_num'] = ch_num
                doc['chapter_ref'] = ch_ref

                # date_approx: same treatment.
                dt_num, dt_ref = parse_int_field(doc.get('date_approx'))
                doc['date_approx'] = dt_num
                doc['date_ref'] = dt_ref

                yield {
                    '_index': ES_INDEX,
                    '_id': doc['chunk_id'],
                    '_source': doc
                }


try:
    count, errors = helpers.bulk(
        es,
        generate_docs(),
        chunk_size=200,
        raise_on_error=False,
        raise_on_exception=False,
    )
except BulkIndexError as e:
    count, errors = 0, e.errors

print(f'Indexed {count} documents into Elasticsearch')

if errors:
    print(f'{len(errors)} document(s) failed to index. Showing first 5:')
    for err in errors[:5]:
        print(json.dumps(err, indent=2, ensure_ascii=False))

es.indices.refresh(index=ES_INDEX)
total = es.count(index=ES_INDEX)['count']
print(f'Total documents in ES: {total}')
