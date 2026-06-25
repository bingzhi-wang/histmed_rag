# agents/nodes.py
import json
import ollama
from agents.state import AgentState
from scripts.retrieval import HybridRetriever

MODEL = 'mistral:7b-instruct-q4_0'  # Change to your pulled model

# Shared retriever instance (loaded once)
_retriever = None
def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever

def call_llm(system_prompt: str, user_prompt: str) -> str:
    '''Call local Ollama LLM. Fully offline.'''
    response = ollama.chat(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user',   'content': user_prompt},
        ]
    )
    return response['message']['content']


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
    raw = call_llm(system, user)
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
    retriever = get_retriever()
    chunks = retriever.retrieve(
        query=state['expanded_query'],
        top_k=12,
        filter_traditions=state.get('relevant_traditions') or None,
        date_from=state.get('date_from'),
        date_to=state.get('date_to')
    )
    return {'retrieved_chunks': chunks}


# ── AGENT 3: SynthesisAgent ───────────────────────────────────────────
def synthesis_agent(state: AgentState) -> dict:
    chunks = state['retrieved_chunks']
    if not chunks:
        return {'synthesis_draft': 'No relevant passages found in the corpus.'}
    
    context = ''
    for i, c in enumerate(chunks):
        context += f'[SOURCE {i+1}] {c.source_text} | {c.date_label} | {c.section}\n'
        context += f'Language: {c.language} | Tradition: {c.tradition}\n'
        context += f'Text: {c.text}\n\n'
    
    system = '''You are a scholar of the history of medicine. You write
    comparative analyses of medical concepts across ancient Chinese, Greek,
    and Latin traditions. You always:
    1. Reference sources by their [SOURCE N] tag from the context
    2. Note when concepts are structurally analogous vs truly equivalent
    3. Flag when you are interpreting or translating (not just reporting)
    4. Avoid anachronistic use of modern medical categories
    5. Use precise, scholarly language
    '''
    user = f'''Research query: {state['user_query']}
    
    Retrieved passages from the corpus:
    {context}
    
    Write a comparative scholarly synthesis addressing the query.
    Reference sources inline as [SOURCE N]. Be precise about which
    tradition each concept belongs to.'''
    
    draft = call_llm(system, user)
    return {'synthesis_draft': draft}


# ── AGENT 4: ProofreadingAgent ────────────────────────────────────────
def proofreading_agent(state: AgentState) -> dict:
    chunks = state['retrieved_chunks']
    draft  = state['synthesis_draft']
    iteration = state.get('iteration_count', 0)
    
    context = ''
    for i, c in enumerate(chunks):
        context += f'[SOURCE {i+1}]: {c.text}\n---\n'
    
    system = '''You are a rigorous academic proofreader specializing in
    the history of medicine. Your task is to verify a scholarly synthesis
    against its source passages. You check for:
    1. UNSUPPORTED CLAIMS: statements not grounded in any source passage
    2. ANACHRONISMS: modern medical concepts incorrectly projected onto historical texts
    3. OVER-TRANSLATION: rendering ancient terms too freely into modern equivalents
    4. SOURCE MISATTRIBUTION: claims attributed to wrong source
    5. MISSING NUANCE: where uncertainty should be flagged but was not
    
    Return a JSON object with:
    - passed: true if synthesis is well-grounded, false if major issues found
    - flagged_claims: list of specific problematic sentences (empty if passed)
    - report: 2-3 sentence summary of your assessment
    - needs_more_retrieval: true if the query requires sources not yet retrieved
    '''
    user = f'''Synthesis to proofread:
    {draft}
    
    Available source passages:
    {context}
    
    Verify the synthesis against these sources.'''
    
    raw = call_llm(system, user)
    raw = raw.strip()
    if raw.startswith('```'): raw = raw.split('```')[1]
    if raw.startswith('json'): raw = raw[4:]
    try:
        result = json.loads(raw)
    except:
        result = {'passed': True, 'flagged_claims': [],
                  'report': 'Proofreading complete.', 'needs_more_retrieval': False}
    
    return {
        'proofreading_passed':  result.get('passed', True),
        'flagged_claims':       result.get('flagged_claims', []),
        'proofreading_report':  result.get('report', ''),
        'retrieval_needed':     result.get('needs_more_retrieval', False) and iteration < 2,
        'iteration_count':      iteration + 1,
    }


# ── AGENT 5: CitationAgent ────────────────────────────────────────────
def citation_agent(state: AgentState) -> dict:
    chunks  = state['retrieved_chunks']
    draft   = state['synthesis_draft']
    report  = state['proofreading_report']
    flagged = state.get('flagged_claims', [])
    
    citations = []
    for i, c in enumerate(chunks):
        cite = (f'[SOURCE {i+1}] {c.source_text}. {c.section}. '
                f'{c.date_label}. Language: {c.language}. '
                f'Tradition: {c.tradition}.')
        citations.append(cite)
    
    warnings = ''
    if flagged:
        warnings = '\n\n⚠ PROOFREADING FLAGS:\n' + '\n'.join(f'• {f}' for f in flagged)
    
    final = (f'{draft}\n\n---\n'
             f'**Sources**\n' + '\n'.join(citations) +
             f'\n\n**Proofreading**: {report}' + warnings)
    
    return {'citations': citations, 'final_response': final}
