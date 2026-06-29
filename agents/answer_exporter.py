# agents/answer_exporter.py — export each query's answer to a dated Markdown file
import os, re, uuid, datetime

EXPORT_DIR = 'exports'

def _slug(text: str, maxlen: int = 50) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')
    return (s[:maxlen].rstrip('-')) or 'query'

def export_answer(state: dict, input_dt: datetime.datetime,
                  trace_id: str = '', out_dir: str = EXPORT_DIR) -> str:
    '''Write the final answer to exports/<date>_<slug>_<id>.md. Returns the path.'''
    query  = state.get('user_query', '')
    answer = state.get('final_response', '') or '(no answer produced)'
    short  = (trace_id[:8] if trace_id else uuid.uuid4().hex[:8])

    stamp_file = input_dt.strftime('%Y-%m-%d_%H%M%S')
    stamp_human = input_dt.strftime('%Y-%m-%d %H:%M:%S')
    fname = f'{stamp_file}_{_slug(query)}_{short}.md'
    path  = os.path.join(out_dir, fname)

    header = (f'# HistMed RAG — Query Answer\n\n'
              f'- **Date of input:** {stamp_human}\n'
              f'- **Query:** {query}\n'
              + (f'- **Trace ID:** {trace_id}\n' if trace_id else '')
              + '\n---\n\n')

    os.makedirs(out_dir, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(header + answer + '\n')
    return path
