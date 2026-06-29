# agents/state.py
from typing import TypedDict, List, Optional, Annotated
import operator

class AgentState(TypedDict):
    # User input
    user_query:          str
    query_timestamp:     str   # NEW — ISO timestamp captured at input time
    # QueryAnalysisAgent outputs
    expanded_query:      str
    relevant_traditions: List[str]
    relevant_languages:  List[str]
    date_from:           Optional[int]
    date_to:             Optional[int]
    medical_concepts:    List[str]

    # RetrievalAgent outputs
    retrieved_chunks:    list  # List of RetrievedChunk objects

    # SynthesisAgent outputs
    synthesis_draft:     str
    
    # CitationResolver outputs (B1)
    source_map:          List[dict]   # provenance for every retrieved chunk (1-indexed)
    cited_source_ns:     List[int]    # unique [SOURCE N] actually referenced in draft
    resolved_citations:  List[dict]   # provenance for cited, in-range N (ordered)
    dangling_markers:    List[int]    # cited N out of range — invalid citations
    uncited_sources:     List[int]    # retrieved but never cited
    
    # ProofreadingAgent outputs
    proofreading_report: str
    proofreading_passed: bool
    flagged_claims:      List[str]
    retrieval_needed:    bool  # Flag to trigger re-retrieval
    # B2 additions
    claim_verifications: List[dict]   # per-claim audit: claim, cited_sources, supported, issue, out_of_range
    structural_issues:   List[str]    # deterministic citation-integrity failures

    # CitationAgent outputs
    citations:           List[str]
    final_response:      str
    citation_records: List[dict]  #(B4 addition) per-source: formatted citation, verification status, score, ids

    # Tracking
    iteration_count:     int
