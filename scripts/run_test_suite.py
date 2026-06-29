#!/usr/bin/env python3
# scripts/run_test_suite.py
# Run a battery of probe questions through the HistMed RAG pipeline in one process
# (models load once, retriever singleton reused), collecting each run's trace +
# answer export and writing a summary.
#
# Usage (from project root, services already up — see start.sh):
#   python scripts/run_test_suite.py                # run all
#   python scripts/run_test_suite.py 5 7 11         # run only #5, #7, #11
#   python scripts/run_test_suite.py --list         # print questions, run nothing
#
# Each question also produces the usual logs/<...>.jsonl trace and
# exports/<...>.md answer; this runner additionally writes:
#   test_runs/<timestamp>/NN_<slug>.md      per-question answer copy
#   test_runs/<timestamp>/summary.tsv|.md   one row per question

import os
import sys
import re
import glob
import json
import time
import datetime

# ---- make project root importable and the working directory ------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

# (id, category, probes, question)
QUESTIONS = [
    ("single-tradition-zh", "Cross-lingual retrieval -> Suwen; hard filter; term fidelity",
     "According to the Huangdi Neijing Suwen, how does each season correspond to a specific "
     "organ, and what happens when the seasonal qi is violated?"),

    ("single-tradition-grc-prognostic", "Retrieves Prognostic specifically, not only OAM",
     "In Hippocrates' Prognostic, what bodily signs are used to forecast the outcome of a disease?"),

    ("single-tradition-la", "Causae retrieval on its strong vocabulary",
     "What does Hildegard's Causae et Curae say about melancholy and black bile?"),

    ("two-tradition-compare", "Structural analogy vs equivalence (humors vs yin-yang)",
     "Compare how Greek humoral theory and Chinese yin-yang explain the balance and imbalance "
     "that cause disease."),

    ("three-tradition-floor", "Diversification floor: all three traditions present",
     "How do all three traditions explain the relationship between seasonal change and disease onset?"),

    ("three-tradition-terms", "Term fidelity + attribution across qi / physis / viriditas",
     "Compare the vital principle in each tradition: qi in Chinese medicine, innate heat and "
     "physis in Greek medicine, and viriditas and humoral vitality in Hildegard."),

    ("limit-total-gap", "REFUSE GAPS: antibiotics/germ theory absent from all corpora",
     "What do these texts say about bacterial infection and the use of antibiotics?"),

    ("limit-anachronism-gap", "Anachronism + gap: microscope diagnosis",
     "How did these ancient physicians use the microscope to diagnose disease?"),

    ("partial-coverage-pulse", "Honest partial coverage: strong zh, some grc, thin la",
     "How does each tradition describe the pulse as a diagnostic tool?"),

    ("single-topic-acupuncture", "Topic in one tradition only; absence elsewhere",
     "What does the corpus say about acupuncture and needling, and which traditions discuss it?"),

    ("limit-anachronism-circulation", "Subtle anachronism: blood circulation (Harvey 1628)",
     "Explain how each tradition understood the circulation of blood through the body."),

    ("temporal-filter-edge", "Date filter; only Causae (~1150 CE) qualifies",
     "Considering only sources written after 1000 CE, what theory of disease causation is presented?"),

    ("causae-weak-relevance", "Causae seasonal/cosmological retrieval ceiling; honest if thin",
     "What does Causae et Curae say about how the seasons and the cosmos affect the humors and health?"),

    ("duplicate-section-stress", "OAM heavy chunking; dedup; no repeated-section citations",
     "What does On Ancient Medicine argue about the origins of the medical art and the role of diet?"),

    ("non-english-query", "Multilingual query embedding; filename slug fallback",
     "\u9ec4\u5e1d\u5185\u7ecf\u4e2d\u5173\u4e8e\u4e94\u810f\u4e0e\u5b63\u8282\u5173\u7cfb\u7684\u8bba\u8ff0\u662f\u4ec0\u4e48\uff1f"),

    ("contrastive-meta-honesty", "Contrast + explicit corpus-limit acknowledgement",
     "Where do the three traditions fundamentally disagree about what causes disease, and where is "
     "the evidence in the corpus too thin to judge?"),
]


def slug(text, maxlen=40):
    s = re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')
    return (s[:maxlen].rstrip('-')) or 'query'


def snapshot(d, ext):
    return set(glob.glob(os.path.join(d, f'*{ext}')))


def newest_new(before, d, ext):
    new = snapshot(d, ext) - before
    return max(new, key=os.path.getmtime) if new else ''


def trace_signals(path):
    """Pull a few headline signals from a trace file for the summary."""
    sig = {'traditions': '', 'cited': '', 'passed': '', 'iters': '', 'n_retrieved': ''}
    if not path:
        return sig
    try:
        r = json.loads(open(path, encoding='utf-8').read())
        retr = r.get('retrieved', [])
        sig['n_retrieved'] = len(retr)
        sig['traditions'] = ','.join(sorted({c.get('tradition', '?') for c in retr}))
        sig['cited'] = ','.join(map(str, r.get('cited_source_ns', [])))
        sig['passed'] = r.get('proofreading_passed', '')
        sig['iters'] = r.get('iteration_count', '')
    except Exception as e:
        sig['traditions'] = f'(trace read error: {e})'
    return sig


def main():
    args = sys.argv[1:]
    if '--list' in args:
        for i, (qid, probes, _q) in enumerate(QUESTIONS, 1):
            print(f'{i:2d}. [{qid}] {probes}')
            print(f'      {_q}')
        return

    # optional subset of 1-based indices
    sel = [int(a) for a in args if a.isdigit()]
    items = [(i, *QUESTIONS[i - 1]) for i in sel] if sel else \
            [(i, *q) for i, q in enumerate(QUESTIONS, 1)]

    ts = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    outdir = os.path.join('test_runs', ts)
    os.makedirs(outdir, exist_ok=True)
    print(f'>> Test run: {outdir}  ({len(items)} question(s))')
    print('>> Loading pipeline (models load on first query) ...')

    # deferred import so --list works without torch/FlagEmbedding installed
    from main import query

    rows = []
    suite_t0 = time.time()
    for n, qid, probes, q in items:
        print('\n' + '=' * 100)
        print(f'[{n}/{len(QUESTIONS)}] ({qid}) {probes}')
        print(f'Q: {q}')
        print('-' * 100)

        lb = snapshot('logs', '.jsonl')
        eb = snapshot('exports', '.md')
        t0 = time.time()
        status, err, answer = 'ok', '', ''
        try:
            answer = query(q)
        except Exception as e:
            status, err = 'error', repr(e)
        dt = time.time() - t0

        trace = newest_new(lb, 'logs', '.jsonl')
        export = newest_new(eb, 'exports', '.md')
        sig = trace_signals(trace)

        # per-question answer copy in the test-run folder
        with open(os.path.join(outdir, f'{n:02d}_{slug(qid)}.md'), 'w', encoding='utf-8') as f:
            f.write(f'# [{qid}] {probes}\n\n**Q:** {q}\n\n'
                    f'- status: {status}{(" — " + err) if err else ""}\n'
                    f'- duration: {dt:.1f}s\n'
                    f'- traditions retrieved: {sig["traditions"]}\n'
                    f'- cited sources: {sig["cited"]}\n'
                    f'- proofread passed: {sig["passed"]}  | iterations: {sig["iters"]}\n'
                    f'- trace: {trace}\n- export: {export}\n\n---\n\n'
                    + (answer or '(no answer)') + '\n')

        rows.append({
            'n': n, 'id': qid, 'probes': probes, 'status': status,
            'sec': f'{dt:.1f}', 'n_retrieved': sig['n_retrieved'],
            'traditions': sig['traditions'], 'cited': sig['cited'],
            'passed': sig['passed'], 'iters': sig['iters'],
            'trace': os.path.basename(trace), 'export': os.path.basename(export),
            'err': err,
        })
        print(f'   -> {status} in {dt:.1f}s | traditions: {sig["traditions"]} | '
              f'cited: [{sig["cited"]}] | passed: {sig["passed"]} | iters: {sig["iters"]}')

    # ---- summaries -----------------------------------------------------------
    cols = ['n', 'id', 'status', 'sec', 'n_retrieved', 'traditions',
            'cited', 'passed', 'iters', 'trace', 'export', 'probes', 'err']
    with open(os.path.join(outdir, 'summary.tsv'), 'w', encoding='utf-8') as f:
        f.write('\t'.join(cols) + '\n')
        for r in rows:
            f.write('\t'.join(str(r.get(c, '')) for c in cols) + '\n')

    with open(os.path.join(outdir, 'summary.md'), 'w', encoding='utf-8') as f:
        f.write(f'# Test suite summary — {ts}\n\n')
        f.write('| # | id | status | sec | traditions retrieved | cited | passed | iters |\n')
        f.write('|---|----|--------|-----|----------------------|-------|--------|-------|\n')
        for r in rows:
            f.write(f"| {r['n']} | {r['id']} | {r['status']} | {r['sec']} | "
                    f"{r['traditions']} | {r['cited']} | {r['passed']} | {r['iters']} |\n")

    total = time.time() - suite_t0
    ok = sum(1 for r in rows if r['status'] == 'ok')
    print('\n' + '=' * 100)
    print(f'>> Done: {ok}/{len(rows)} ok in {total/60:.1f} min')
    print(f'>> Summary: {os.path.join(outdir, "summary.md")}  /  summary.tsv')
    print(f'>> Per-question answers: {outdir}/NN_*.md')


if __name__ == '__main__':
    main()
