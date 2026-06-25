# agents/graph.py
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.nodes import (
    query_analysis_agent, retrieval_agent, synthesis_agent,
    proofreading_agent, citation_agent
)

def should_reretrieve(state: AgentState) -> str:
    '''Routing function: re-retrieve if proofreader says needed.'''
    if state.get('retrieval_needed') and state.get('iteration_count', 0) <= 2:
        return 'retrieval_agent'
    return 'citation_agent'

def build_graph():
    g = StateGraph(AgentState)
    
    # Add all agent nodes
    g.add_node('query_analysis',  query_analysis_agent)
    g.add_node('retrieval_agent', retrieval_agent)
    g.add_node('synthesis_agent', synthesis_agent)
    g.add_node('proofreading',    proofreading_agent)
    g.add_node('citation_agent',  citation_agent)
    
    # Define the flow
    g.set_entry_point('query_analysis')
    g.add_edge('query_analysis',  'retrieval_agent')
    g.add_edge('retrieval_agent', 'synthesis_agent')
    g.add_edge('synthesis_agent', 'proofreading')
    
    # Conditional: after proofreading, either re-retrieve or proceed to citation
    g.add_conditional_edges('proofreading', should_reretrieve)
    g.add_edge('citation_agent', END)
    
    return g.compile()

# Module-level compiled graph
graph = build_graph()
