# main.py
from agents.graph import graph
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

def query(user_question: str) -> str:
    console.print(Panel(
        f'[bold cyan]Query:[/] {user_question}',
        title='HistMed RAG System'
    ))
    
    initial_state = {
        'user_query':          user_question,
        'expanded_query':      '',
        'relevant_traditions': [],
        'relevant_languages':  [],
        'date_from':           None,
        'date_to':             None,
        'medical_concepts':    [],
        'retrieved_chunks':    [],
        'synthesis_draft':     '',
        'proofreading_report': '',
        'proofreading_passed': False,
        'flagged_claims':      [],
        'retrieval_needed':    False,
        'citations':           [],
        'final_response':      '',
        'iteration_count':     0,
    }
    
    with console.status('[bold green]Agents processing...') as status:
        result = graph.invoke(initial_state)
    
    console.print(Markdown(result['final_response']))
    return result['final_response']

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        q = ' '.join(sys.argv[1:])
    else:
        q = input('Enter research query: ')
    query(q)
