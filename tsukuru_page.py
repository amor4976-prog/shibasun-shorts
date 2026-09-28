#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""スマホで本文をコピーするページを作る。yotei.json と デスクトップの本文から。"""
import glob, html, json, os, re

D = os.path.expanduser("~/Desktop/ショート投稿")
HERE = os.path.dirname(os.path.abspath(__file__))

hon = {}
for f in sorted(glob.glob(f"{D}/*_本文.txt")) + sorted(glob.glob(f"{D}/_投稿ずみ/*_本文.txt")):
    n = os.path.basename(f)
    if n[:2].isdigit():
        hon[int(n[:2])] = (n[3:-8].replace("!?", "！？").replace("!", "！").replace("?", "？"),
                           open(f, encoding="utf-8").read().strip())

y = json.load(open(f"{HERE}/yotei.json", encoding="utf-8"))
hi = {t["番号"]: t["日"] for t in y["予定"]}

kumi = []
for ban in sorted(hon):
    dai, text = hon[ban]
    kumi.append(f'''<article>
  <h2>{ban:02d}　{html.escape(dai)}</h2>
  <p class="hi">{html.escape(hi.get(ban, ""))}</p>
  <pre id="t{ban}">{html.escape(text)}</pre>
  <button onclick="utsusu({ban})">この文をコピー</button>
</article>''')

open(f"{HERE}/index.html", "w", encoding="utf-8").write(f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>ショートの本文</title>
<style>
 body{{font-family:-apple-system,"Hiragino Sans",sans-serif;margin:0;padding:16px;background:#faf9f7;color:#1a1a1a;line-height:1.7}}
 h1{{font-size:18px;margin:0 0 4px}} .memo{{font-size:13px;color:#666;margin:0 0 20px}}
 article{{background:#fff;border:1px solid #e6e3de;border-radius:10px;padding:14px;margin-bottom:14px}}
 h2{{font-size:15px;margin:0 0 2px}} .hi{{font-size:12px;color:#8a8a8a;margin:0 0 8px}}
 pre{{white-space:pre-wrap;font-family:inherit;font-size:14px;background:#f6f4f1;border-radius:8px;padding:10px;margin:0 0 10px}}
 button{{width:100%;padding:12px;font-size:15px;border:0;border-radius:8px;background:#1a1a1a;color:#fff}}
 button.done{{background:#2e7d32}}
</style></head><body>
<h1>ショートの本文</h1>
<p class="memo">TikTokに貼る文です。ボタンを押すとコピーできます。</p>
{"".join(kumi)}
<script>
function utsusu(n){{
  const t=document.getElementById("t"+n).innerText;
  navigator.clipboard.writeText(t).then(()=>{{
    const b=event.target; b.textContent="コピーしました"; b.className="done";
    setTimeout(()=>{{b.textContent="この文をコピー"; b.className="";}},1600);
  }});
}}
</script></body></html>''')
print("ページを作りました:", len(kumi), "本")
