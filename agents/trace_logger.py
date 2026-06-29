# agents/trace_logger.py — B3: persist full query trace (append-only JSONL)
import json, os, uuid, datetime
from agents.answer_exporter import _slug      # reuse slug for matching filenames

LOG_DIR    = 'logs'
TRACE_PATH = os.path.join(LOG_DIR, 'query_traces.jsonl')

def _chunk_brief(c) -> dict:
    '''Retrieval record for one RetrievedChunk: ids + score + locators.'''
    return {
        'chunk_id':    getattr(c, 'chunk_id', None),
        'source_urn':  getattr(c, 'source_urn', None),
        'source_text': getattr(c, 'source_text', None),
        'section':     getattr(c, 'section', None),
        'chapter_ref': getattr(c, 'chapter_ref', None),
        'tradition':   getattr(c, 'tradition', None),
        'score':       getattr(c, 'score', None),
    }

def build_trace(state: dict) -> dict:
    '''Assemble a serializable trace from the final AgentState.'''
    chunks = state.get('retrieved_chunks', []) or []
    return {
        'trace_id':  uuid.uuid4().hex,
        'timestamp': datetime.datetime.now().isoformat(timespec='seconds'),
	 'input_timestamp': state.get('query_timestamp'), 
	 
        # query analysis
        'user_query':          state.get('user_query', ''),
        'expanded_query':      state.get('expanded_query', ''),
        'medical_concepts':    state.get('medical_concepts', []),
        'relevant_traditions': state.get('relevant_traditions', []),
        'relevant_languages':  state.get('relevant_languages', []),
        'date_from':           state.get('date_from'),
        'date_to':             state.get('date_to'),

        # retrieval — ids+scores in [SOURCE N] order (source_n == N)
        'retrieved': [{'source_n': i, **_chunk_brief(c)}
                      for i, c in enumerate(chunks, 1)],

        # answer
        'synthesis_draft': state.get('synthesis_draft', ''),
        'final_response':  state.get('final_response', ''),

        # citation resolution (B1)
        'cited_source_ns':    state.get('cited_source_ns', []),
        'resolved_citations': state.get('resolved_citations', []),
        'dangling_markers':   state.get('dangling_markers', []),
        'uncited_sources':    state.get('uncited_sources', []),

        # verification (B2)
        'proofreading_passed': state.get('proofreading_passed'),
        'proofreading_report': state.get('proofreading_report', ''),
        'structural_issues':   state.get('structural_issues', []),
        'claim_verifications': state.get('claim_verifications', []),
        'flagged_claims':      state.get('flagged_claims', []),

        # formatting (B4)
        'citation_records': state.get('citation_records', []),

        # loop
        'iteration_count': state.get('iteration_count', 0),
    }

def write_trace(state: dict, input_dt: datetime.datetime = None,
                out_dir: str = LOG_DIR) -> tuple:
    '''Append one timestamped JSONL file per run. Returns (trace_id, path).
    File is still valid JSONL (one record/line): glob logs/*.jsonl to read all.'''
    if input_dt is None:
        input_dt = datetime.datetime.now()
    trace = build_trace(state)
    short = trace['trace_id'][:8]
    stamp = input_dt.strftime('%Y-%m-%d_%H%M%S')
    fname = f'{stamp}_{_slug(state.get("user_query", ""))}_{short}.jsonl'
    path  = os.path.join(out_dir, fname)

    os.makedirs(out_dir, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(trace, ensure_ascii=False, default=str) + '\n')
    return trace['trace_id'], path
