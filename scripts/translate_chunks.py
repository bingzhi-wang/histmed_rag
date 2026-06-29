# scripts/translate_chunks.py
"""
One-time batch translator: adds an English `text_translation` field to every
chunk in a processed *_chunks.jsonl file, using a local Ollama model.
Idempotent & resumable — chunks that already have a translation are skipped.

Usage:
    python scripts/translate_chunks.py corpus/processed/suwen_chunks.jsonl
    python scripts/translate_chunks.py corpus/processed/*.jsonl   # all at once
"""
import sys, json, time, glob
from pathlib import Path
import requests

OLLAMA_URL        = "http://localhost:11434/api/chat"
TRANSLATION_MODEL = "qwen3:14b"   # Qwen strongly preferred (esp. for Suwen)
NUM_CTX           = 8192          # must hold one chunk + prompt
TEMPERATURE       = 0.2           # low = faithful, less invented detail
REQUEST_TIMEOUT   = 300
MAX_RETRIES       = 3
FLUSH_EVERY       = 10            # write file back every N translations

LANG_GUIDANCE = {
    "zh-classical": "The text is Classical Chinese from the Huangdi Neijing Suwen. "
        "Keep key medical terms in hanzi with pinyin on first use, e.g. 氣 (qì), 陰陽 (yīn-yáng).",
    "grc": "The text is Ancient Greek (Hippocratic corpus). Keep key medical terms "
        "transliterated on first use, e.g. φύσις (physis), πνεῦμα (pneuma).",
    "la-medieval": "The text is Medieval Latin (Hildegard) from an OCR'd edition and may "
        "contain scan errors (e.g. 'aute'→'autem', 'foit'→'fuit'). Silently correct obvious "
        "OCR errors and translate the intended meaning. Keep key terms in Latin, e.g. humores.",
}

SYSTEM_PROMPT = (
    "You are a scholarly translator of ancient and medieval medical texts. "
    "Produce a faithful, literal English translation of the passage. {guidance} "
    "Do not summarize, explain, or add commentary. Do not invent content. If a passage is "
    "too corrupt to translate, render it as literally as possible. Output ONLY the translation."
)

def translate_one(text, language):
    payload = {
        "model": TRANSLATION_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.format(guidance=LANG_GUIDANCE.get(language, ""))},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "options": {"temperature": TEMPERATURE, "num_ctx": NUM_CTX},
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            content = r.json()["message"]["content"].strip()
            if "</think>" in content:                      # strip Qwen thinking block
                content = content.split("</think>", 1)[1].strip()
            if content:
                return content
        except Exception as e:
            print(f"    retry {attempt}/{MAX_RETRIES}: {e}")
            time.sleep(2 * attempt)
    return None   # leave untranslated so a later run retries

def _write(path, chunks):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    tmp.replace(path)   # atomic

def process_file(path):
    path = Path(path)
    chunks = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    todo = [c for c in chunks if not c.get("text_translation")]
    print(f"{path.name}: {len(chunks)} chunks, {len(todo)} to translate")
    done = 0
    for chunk in chunks:
        if chunk.get("text_translation"):
            continue
        t = translate_one(chunk["text"], chunk.get("language", ""))
        if t:
            chunk["text_translation"] = t
            done += 1
            print(f"  [{done}/{len(todo)}] {chunk['chunk_id']}")
        if done and done % FLUSH_EVERY == 0:
            _write(path, chunks)
    _write(path, chunks)
    print(f"{path.name}: {done} new translations written\n")

if __name__ == "__main__":
    files = [f for a in sys.argv[1:] for f in glob.glob(a)]
    if not files:
        print(__doc__); sys.exit(1)
    for f in files:
        process_file(f)
