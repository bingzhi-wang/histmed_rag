## agents/nodes.py 
import json, re
import ollama
from agents.state import AgentState
from scripts.retrieval import HybridRetriever

MODEL   = 'qwen3:14b'
NUM_CTX = 16384          # must hold prompt + ~12 chunks (orig + translation)

_retriever = None
def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever

def _strip_think(text: str) -> str:
    '''Remove Qwen3 <think>...</think> reasoning from the visible answer.'''
    if not text:
        return ''
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    if '</think>' in text:                 # unbalanced (open tag missing)
        text = text.split('</think>')[-1]
    return text.strip()

def call_llm(system_prompt: str, user_prompt: str,
             json_mode: bool = False, temperature: float = 0.3,
             num_ctx: int = NUM_CTX) -> str:
    '''Local Ollama call, Qwen3-aware. Fully offline.'''
    kwargs = {}
    if json_mode:
        user_prompt += ' /no_think'        # disable thinking for clean JSON
        kwargs['format'] = 'json'          # Ollama constrains output to valid JSON
    resp = ollama.chat(
        model=MODEL,
        messages=[{'role': 'system', 'content': system_prompt},
                  {'role': 'user',   'content': user_prompt}],
        options={'temperature': temperature, 'num_ctx': num_ctx},
        **kwargs,
    )
    return _strip_think(resp['message']['content'])
    
# ── B4: academic citation formatting (deterministic, no LLM) ──────────
def _translation_note(tradition: str, language: str) -> str:
    t, lang = (tradition or '').lower(), (language or '')
    if 'greek' in t or lang.startswith('grc'):
        return 'Greek text and English translation: Perseus Digital Library.'
    if 'chinese' in t or lang.startswith('zh'):
        return 'English translation: LLM-assisted (unreviewed).'
    if 'medieval' in t or 'european' in t or lang.startswith('la'):
        return 'Latin from OCR; English translation: LLM-assisted (unreviewed).'
    return ''

def _format_citation(prov: dict) -> str:
    '''Per-tradition academic citation from a B1 provenance dict.'''
    t        = (prov.get('tradition') or '').lower()
    language = (prov.get('language') or '')
    work     = (prov.get('source_text') or 'Untitled passage').strip()
    section  = (prov.get('section') or prov.get('section_ref') or '').strip()
    chapter  = (prov.get('chapter_ref') or '').strip()
    date     = (prov.get('date_label') or '').strip()
    urn      = (prov.get('source_urn') or '').strip()
    locator  = chapter or section   # Suwen/Causae prefer chapter; Hippocrates uses section

    is_zh = 'chinese' in t or language.startswith('zh')
    is_gr = 'greek'   in t or language.startswith('grc')
    is_la = 'medieval' in t or 'european' in t or language.startswith('la')

    if is_zh:
        # append canonical Han title only if the work string has no Han chars
        has_han = any('\u4e00' <= ch <= '\u9fff' for ch in work)
        cite = f'*{work}*' if has_han else f'*{work} (黄帝内经素問)*'
    elif is_gr:
        cite = f'Hippocrates, *{work}*'
    elif is_la:
        cite = f'Hildegard of Bingen, *{work}*'
    else:
        cite = f'*{work}*'

    if locator: cite += f', {locator}'
    if date:    cite += f' ({date})'
    if urn:     cite += f'. {urn}'
    note = _translation_note(prov.get('tradition'), language)
    if note:    cite += f'. {note}'
    return cite.rstrip('. ') + '.'
    
# ── AGENT 1: QueryAnalysisAgent ───────────────────────────────────────
def query_analysis_agent(state: AgentState) -> dict:
    system = '''You are a specialist in the history of medicine across Chinese,
    Greek, and Latin medical traditions. Your task is to analyze a research
    query and prepare it for multilingual corpus retrieval.
    
    Return ONLY a JSON object with these fields:
    - expanded_query: an enriched English query incorporating equivalent
      terms from relevant traditions
    - medical_concepts: list of core medical concepts in the query
    - relevant_traditions: list from [chinese-medicine, greek-medicine,
      medieval-european] — all three if the query is general
    - relevant_languages: list from [zh-classical, grc, la-medieval]
    - date_from: null or integer year (negative=BCE) if time-filtering needed
    - date_to: null or integer year if time-filtering needed
    '''
    user = f'Analyze this research query: {state["user_query"]}'
    raw = call_llm(system, user, json_mode=True)
    # Clean JSON response
    raw = raw.strip()
    if raw.startswith('```'): raw = raw.split('```')[1]
    if raw.startswith('json'): raw = raw[4:]
    try:
        parsed = json.loads(raw)
    except Exception:
        # Fallback defaults
        parsed = {
            'expanded_query': state['user_query'],
            'medical_concepts': [],
            'relevant_traditions': ['chinese-medicine','greek-medicine','medieval-european'],
            'relevant_languages': ['zh-classical','grc','la-medieval'],
            'date_from': None, 'date_to': None
        }
    return {
        'expanded_query':      parsed.get('expanded_query', state['user_query']),
        'medical_concepts':    parsed.get('medical_concepts', []),
        'relevant_traditions': parsed.get('relevant_traditions',
            ['chinese-medicine','greek-medicine','medieval-european']),
        'relevant_languages':  parsed.get('relevant_languages',
            ['zh-classical','grc','la-medieval']),
        'date_from':           parsed.get('date_from'),
        'date_to':             parsed.get('date_to'),
    }

# ── AGENT 2: RetrievalAgent ───────────────────────────────────────────
def retrieval_agent(state: AgentState) -> dict:
    retriever  = get_retriever()
    traditions = state.get('relevant_traditions') or []
    # one tradition -> hard filter (narrow intent); multiple -> no hard filter
    # but guarantee a per-tradition floor so a low-scoring tradition (e.g.
    # Causae) is never silently crowded out of top-k.
    hard_filter = traditions if len(traditions) == 1 else None
    floor       = traditions if len(traditions) > 1 else None
    chunks = retriever.retrieve(
        query=state['expanded_query'],
        top_k=12,
        filter_traditions=hard_filter,
        floor_traditions=floor,
        min_per_tradition=2,
        per_source_cap=3,
        date_from=state.get('date_from'),
        date_to=state.get('date_to'),
    )
    return {'retrieved_chunks': chunks}
    
# ── B1: Citation resolution (pure, deterministic, no LLM) ─────────────
# Matches [SOURCE 1], [Source 1], [SOURCES 1, 2], [SOURCE 1 and 3], etc.
SOURCE_BLOCK_RE = re.compile(r'\[\s*SOURCES?\s+([^\]]+?)\s*\]', re.IGNORECASE)
_INT_RE = re.compile(r'\d+')

def _chunk_provenance(c, position: int) -> dict:
    '''Full provenance for one RetrievedChunk at its 1-indexed position.
    getattr-defensive: schema fields not exposed on the object resolve to None
    rather than raising (see downstream flag re: source_urn / score).'''
    return {
        'source_n':    position,
        'chunk_id':    getattr(c, 'chunk_id', None),
        'source_urn':  getattr(c, 'source_urn', None),
        'source_text': getattr(c, 'source_text', None),
        'section':     getattr(c, 'section', None),
        'section_ref': getattr(c, 'section_ref', None),
        'tradition':   getattr(c, 'tradition', None),
        'language':    getattr(c, 'language', None),
        'date_label':  getattr(c, 'date_label', None),
        'date_approx': getattr(c, 'date_approx', None),
        'chapter_ref': getattr(c, 'chapter_ref', None),
        'score':       (getattr(c, 'score', None)
                        or getattr(c, 'rerank_score', None)
                        or getattr(c, 'rrf_score', None)),
    }

def resolve_source_markers(draft: str, chunks: list) -> dict:
    '''B1: resolve positional [SOURCE N] markers against the ordered
    retrieved_chunks list. Invariant: [SOURCE N] -> chunks[N-1].'''
    n_chunks = len(chunks)
    source_map = [_chunk_provenance(c, i) for i, c in enumerate(chunks, 1)]

    cited_ns = []
    for block in SOURCE_BLOCK_RE.findall(draft or ''):
        cited_ns.extend(int(m) for m in _INT_RE.findall(block))
    cited_ns = sorted(set(cited_ns))

    in_range = [n for n in cited_ns if 1 <= n <= n_chunks]
    dangling = [n for n in cited_ns if n < 1 or n > n_chunks]
    resolved = [source_map[n - 1] for n in in_range]
    uncited  = [n for n in range(1, n_chunks + 1) if n not in set(in_range)]

    return {
        'source_map':         source_map,
        'cited_source_ns':    cited_ns,
        'resolved_citations': resolved,
        'dangling_markers':   dangling,
        'uncited_sources':    uncited,
    }

# ── AGENT 3: SynthesisAgent ──────────────────────────────────────────
SYNTHESIS_SYSTEM = '''You are a scholar of the history of medicine writing \
comparative analyses across the ancient Chinese, Greek, and Latin medical \
traditions. Follow these rules without exception:

1. GROUND EVERYTHING. Use only the information in the provided passages. Do \
   not add facts, dates, or claims from outside knowledge.
2. CITE EVERY CLAIM. After each substantive statement, cite its [SOURCE N] \
   tag. A sentence without a citation is allowed only when it explicitly \
   states what the sources do NOT contain.
3. REFUSE GAPS HONESTLY. If the passages cannot answer the query, or cannot \
   support a comparison for a given tradition, say so plainly and name what \
   is missing. Never fill a gap with general knowledge or speculation.
4. KEEP ORIGINAL TERMS. Give key technical terms in their source language \
   with a short gloss, attributed to a tradition, e.g. qì (氣), physis \
   (φύσις), humores. Take the exact term from the "Original" field.
5. BE PRECISE, NOT GENERIC. Prefer specific wording from the passages over \
   broad generalities. Distinguish a structural analogy from a true \
   equivalence. Do not project modern medical categories onto the texts.
6. Write clear, scholarly prose.'''

SYNTHESIS_USER = '''Research query:
{query}

Retrieved passages (each has an English translation and the original text):
{context}

Write a comparative synthesis answering the query using ONLY these passages. \
Cite each claim with its [SOURCE N] tag. If the passages are insufficient for \
any part of the query, state that plainly instead of guessing.'''

def _format_context(chunks) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        cid   = getattr(c, 'chunk_id', f'chunk_{i}')
        trans = (getattr(c, 'text_translation', '') or '').strip()
        orig  = (getattr(c, 'text', '') or '').strip()
        header = (f'[SOURCE {i}] {c.source_text} | {c.section} | '
                  f'{c.tradition} | {c.date_label} | id={cid}')
        if trans:
            body = f'English: {trans}\nOriginal ({c.language}): {orig}'
        else:
            body = f'Original ({c.language}, no translation available): {orig}'
        blocks.append(header + '\n' + body)
    return '\n\n'.join(blocks)

def synthesis_agent(state: AgentState) -> dict:
    chunks = state['retrieved_chunks']
    if not chunks:
        empty = resolve_source_markers('', [])
        return {'synthesis_draft': 'No relevant passages were retrieved from '
                'the corpus, so this query cannot be answered from the '
                'available sources.', **empty}
    user = SYNTHESIS_USER.format(query=state['user_query'],
                                 context=_format_context(chunks))
    draft = call_llm(SYNTHESIS_SYSTEM, user, temperature=0.3)  # thinking on, stripped
    resolution = resolve_source_markers(draft, chunks)         # B1
    return {'synthesis_draft': draft, **resolution}

# ── AGENT 4: ProofreadingAgent (B2: citation verification) ────────────
def proofreading_agent(state: AgentState) -> dict:
    chunks    = state['retrieved_chunks']
    draft     = state['synthesis_draft']
    iteration = state.get('iteration_count', 0)

    # B1 outputs (present: synthesis_agent now resolves markers)
    source_map = state.get('source_map', [])
    dangling   = state.get('dangling_markers', [])
    cited_ns   = state.get('cited_source_ns', [])
    n_chunks   = len(chunks)

    # ---- Layer 1: structural verification (deterministic, no LLM) ----
    structural_issues = []
    if dangling:
        structural_issues.append(
            f'Draft cites nonexistent sources {dangling}; only '
            f'[SOURCE 1]\u2013[SOURCE {n_chunks}] were retrieved.')
    if n_chunks and not cited_ns:
        structural_issues.append('Draft contains no [SOURCE N] citations.')
    structural_ok = not structural_issues

    # ---- Layer 2: semantic verification (LLM, against TRANSLATIONS) ----
    blocks = []
    for prov, c in zip(source_map, chunks):
        n     = prov.get('source_n')
        trans = (getattr(c, 'text_translation', '') or '').strip()
        orig  = (getattr(c, 'text', '') or '').strip()
        label = f"[SOURCE {n}] {prov.get('source_text')} | {prov.get('tradition')}"
        if trans:
            body = f'English: {trans}'
            if orig:
                body += f'\nOriginal terms ({prov.get("language")}): {orig}'
        else:
            body = f'(no translation) Original: {orig}'
        blocks.append(f'{label}\n{body}')
    context = '\n---\n'.join(blocks)

    system = '''You are a rigorous academic proofreader specializing in the
    history of medicine. You verify that every cited claim in a synthesis is
    supported by the source it cites. The synthesis is in English; each passage
    gives an English translation plus original-language terms. Check for:
    1. UNSUPPORTED CLAIMS: a claim whose content is not in the source(s) it cites.
    2. SOURCE MISATTRIBUTION: content that exists, but in a DIFFERENT source than cited.
    3. ANACHRONISM: a modern medical concept projected onto the text.
    4. OVER-TRANSLATION: an original term rendered too freely (judge against Original terms).
    5. MISSING NUANCE: a hedge or uncertainty present in the source but dropped.

    Judge content support against the English translation; judge term fidelity
    against the Original terms. A [SOURCE N] tag is verified only if that
    passage supports the claim.

    Return ONLY a JSON object:
    - claim_checks: list of objects, each {claim, cited_sources (list of integers),
      supported (boolean), issue (string, "" if no problem)}
    - report: 2-3 sentence overall assessment
    - needs_more_retrieval: true ONLY when a claim fails because the corpus lacks
      the needed passage (a recall gap) — NOT for misattribution or invention
    '''
    user = f'''Synthesis to verify:
{draft}

Source passages (cite tag -> passage):
{context}

Verify each cited claim against the passage(s) it cites.'''

    raw = call_llm(system, user, json_mode=True)
    raw = raw.strip()
    if raw.startswith('```'): raw = raw.split('```')[1]
    if raw.startswith('json'): raw = raw[4:]
    try:
        result = json.loads(raw)
    except Exception:
        result = {'claim_checks': [],
                  'report': 'Proofreading parse failed; treated as inconclusive.',
                  'needs_more_retrieval': False}

    claim_checks = result.get('claim_checks', [])
    if not isinstance(claim_checks, list):
        claim_checks = []
    # sanitize + clamp cited_sources to the valid 1..N range
    clean = []
    for ck in claim_checks:
        if not isinstance(ck, dict):
            continue
        cs = ck.get('cited_sources', []) or []
        cs = [int(x) for x in cs if str(x).isdigit()]
        clean.append({
            'claim':         ck.get('claim', ''),
            'cited_sources': cs,
            'out_of_range':  [x for x in cs if x < 1 or x > n_chunks],
            'supported':     bool(ck.get('supported', False)),
            'issue':         ck.get('issue', '') or '',
        })
    claim_checks = clean
    unsupported = [ck for ck in claim_checks if not ck['supported']]

    # ---- combine ----
    passed = structural_ok and not unsupported

    flagged = list(structural_issues)                 # keep flagged_claims: List[str]
    for ck in unsupported:
        srcs = ','.join(map(str, ck['cited_sources'])) or '\u2014'
        flagged.append(f'[SOURCE {srcs}] {ck["issue"] or "unsupported"}: {ck["claim"]}')

    report = result.get('report', '')
    if structural_issues:
        report = ' '.join(structural_issues) + ((' ' + report) if report else '')

    needs_more = bool(result.get('needs_more_retrieval', False))
    return {
        'proofreading_passed': passed,
        'flagged_claims':      flagged,            # List[str] — unchanged type
        'claim_verifications': claim_checks,       # List[dict] — NEW (B2/B3/B4)
        'structural_issues':   structural_issues,  # List[str]  — NEW (B2/B3)
        'proofreading_report': report,
        'retrieval_needed':    needs_more and iteration < 2,
        'iteration_count':     iteration + 1,
    }

# ── B4 ext: carry original + translation per cited source ─────────────
CITE_TEXT_MAXLEN = 600   # visible-render clip only; trace stores FULL text

def _collapse(s: str) -> str:
    return ' '.join((s or '').split())       # flatten newlines/runs of space

def _clip(s: str, maxlen) -> str:
    s = _collapse(s)
    if maxlen and len(s) > maxlen:
        s = s[:maxlen].rstrip() + ' […]'
    return s
# ── AGENT 5: CitationAgent (B4 + source-text in records/traces) ───────
def citation_agent(state: AgentState) -> dict:
    draft   = state['synthesis_draft']
    report  = state.get('proofreading_report', '')
    flagged = state.get('flagged_claims', [])

    chunks            = state.get('retrieved_chunks', []) or []
    resolved          = state.get('resolved_citations', [])    # cited, in-range (B1)
    dangling          = state.get('dangling_markers', [])      # (B1)
    structural_issues = state.get('structural_issues', [])     # (B2)
    claim_checks      = state.get('claim_verifications', [])    # (B2)
    uncited           = state.get('uncited_sources', [])        # (B1)

    # [SOURCE N] -> chunk, via the B1 positional invariant (N == index+1)
    chunk_by_n = {i: c for i, c in enumerate(chunks, 1)}

    disputed, supported = set(), set()
    for ck in claim_checks:
        for n in ck.get('cited_sources', []):
            (supported if ck.get('supported') else disputed).add(n)

    citations, citation_records = [], []
    for prov in resolved:
        n         = prov.get('source_n')
        formatted = _format_citation(prov)
        chunk     = chunk_by_n.get(n)
        orig_full  = (getattr(chunk, 'text', '') or '') if chunk else ''
        trans_full = (getattr(chunk, 'text_translation', '') or '') if chunk else ''
        language   = prov.get('language') or (getattr(chunk, 'language', '') if chunk else '')

        if n in disputed:
            status, mark = 'disputed', '  \u26a0 unverified \u2014 see proofreading flags'
        elif n in supported:
            status, mark = 'verified', ''
        else:
            status, mark = 'cited', ''

        # visible reference: formatted line + clipped passages
        entry = [f'[SOURCE {n}] {formatted}{mark}']
        if trans_full:
            entry.append(f'    - *Translation:* {_clip(trans_full, CITE_TEXT_MAXLEN)}')
        if orig_full:
            entry.append(f'    - *Original ({language}):* {_clip(orig_full, CITE_TEXT_MAXLEN)}')
        citations.append('\n'.join(entry))

        # trace record: FULL text, untruncated
        citation_records.append({
            'source_n':     n,
            'chunk_id':     prov.get('chunk_id'),
            'source_urn':   prov.get('source_urn'),
            'formatted':    formatted,
            'verification': status,
            'score':        prov.get('score'),
            'language':     language,
            'original':     _collapse(orig_full),
            'translation':  _collapse(trans_full),
        })

    integrity = list(structural_issues)
    if dangling:
        integrity.append(f'Citations to nonexistent sources: {dangling}.')

    parts = [draft, '\n---', '**References**']
    parts.append('\n\n'.join(citations) if citations
                 else '_No sources were cited in the synthesis._')
    if uncited:
        parts.append(f'_{len(uncited)} additional passage(s) retrieved but not cited._')
    if report:
        parts.append(f'**Proofreading**: {report}')
    if flagged:
        parts.append('\u26a0 **Proofreading flags:**\n' +
                     '\n'.join(f'\u2022 {f}' for f in flagged))
    if integrity:
        parts.append('\u26a0 **Citation integrity:**\n' +
                     '\n'.join(f'\u2022 {w}' for w in integrity))
    final = '\n\n'.join(p for p in parts if p)

    return {
        'citations':        citations,          # List[str] — now multi-line per source
        'citation_records': citation_records,   # List[dict] — now carries original + translation
        'final_response':   final,
    }
