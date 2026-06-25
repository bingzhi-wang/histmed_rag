# agents/state.py
from typing import TypedDict, List, Optional, Annotated
import operator

class AgentState(TypedDict):
    # User input
    user_query:          str

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

    # ProofreadingAgent outputs
    proofreading_report: str
    proofreading_passed: bool
    flagged_claims:      List[str]
    retrieval_needed:    bool  # Flag to trigger re-retrieval

    # CitationAgent outputs
    citations:           List[str]
    final_response:      str

    # Tracking
    iteration_count:     int
