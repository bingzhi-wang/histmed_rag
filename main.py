# main.py
import datetime                                          # NEW
from agents.graph import graph
from agents.trace_logger import write_trace
from agents.answer_exporter import export_answer         # NEW
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
console = Console()

def query(user_question: str) -> str:
    user_question = (user_question or '').strip()
    if not user_question:
        msg = 'Empty query — please enter a research question.'
        console.print(f'[yellow]{msg}[/yellow]')
        return msg
    input_dt = datetime.datetime.now()                   # NEW — date of input
    console.print(Panel(
        f'[bold cyan]Query:[/] {user_question}',
        title='HistMed RAG System'
    ))

    initial_state = {
        'user_query':          user_question,
        'query_timestamp':     input_dt.isoformat(timespec='seconds'),  # NEW
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

    trace_id, trace_path = write_trace(result, input_dt)
    export_path = export_answer(result, input_dt, trace_id=trace_id)
    console.print(Markdown(result['final_response']))
    console.print(f'[dim]trace  → {trace_path}[/dim]')  
    console.print(f'[dim]answer → {export_path}[/dim]')               
    return result['final_response']

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        q = ' '.join(sys.argv[1:]).strip()
    else:
        q = ''
        while not q:
            q = input('Enter research query: ').strip()
    query(q)
