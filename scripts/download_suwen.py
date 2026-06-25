# scripts/download_suwen.py
import urllib.request, json, time, os, csv

# Read chapters from CSV
with open('/home/bwang/histmed_rag/corpus/raw/suwen/chapters.csv', 'r') as file:
    reader = csv.reader(file)
    chapters = [row[0] for row in reader] 
BASE = 'https://api.ctext.org/'
OUT  = 'corpus/raw/suwen'
os.makedirs(OUT, exist_ok=True)

# CTEXT chapter IDs for Suwen chapters 1-81
# Get chapter list first
url = f'{BASE}?if=en&fn=getdynasties&rnd=0'
# Then fetch each chapter as plain text
# Full script: fetch chapters via ctext API with fn=getctext
# and urn=ctp:huangdi-neijing.suwen.N where chapter is imported 
# from spreadsheet containing the names of suwen
chapter = 0;
for chapters in chapters:
    chapter = chapter + 1
    urn = f'ctp:huangdi-neijing/{chapters}'
    api_url = f'{BASE}gettext?urn={urn}'
    try:
        with urllib.request.urlopen(api_url) as r:
            data = json.loads(r.read().decode('utf-8'))
        text = data.get('fulltext', [])
        
        # Convert to string if it's a list
        if isinstance(text, list):
            text = '\n\n'.join(str(item) for item in text)
        elif not text:
            text = ''            
        fname = f'{OUT}/suwen_ch{chapter:02d}.txt'
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'Downloaded chapter {chapters}')
        time.sleep(1.0)  # Be polite to the server
    except Exception as e:
        print(f'Chapter {chapter} failed: {e}')



