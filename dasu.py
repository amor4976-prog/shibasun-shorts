#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""予約表を見て、今日のぶんをインスタへ出す。GitHubが毎日呼ぶ。"""
import json, os, time, urllib.parse, urllib.request, datetime, sys

V = "v25.0"
TOK = os.environ["IG_TOKEN"]
IG = os.environ["IG_USER_ID"]
NAMA = "https://raw.githubusercontent.com/amor4976-prog/shibasun-shorts/main/"


def api(url, data=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None)
    try:
        return json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        raise SystemExit("インスタが断りました: " + e.read().decode()[:500])


def dasu(mp4_path, honbun):
    url = NAMA + urllib.parse.quote(mp4_path)
    j = api(f"https://graph.facebook.com/{V}/{IG}/media",
            {"media_type": "REELS", "video_url": url, "caption": honbun, "access_token": TOK})
    cid = j["id"]
    for _ in range(60):
        time.sleep(10)
        st = api(f"https://graph.facebook.com/{V}/{cid}?fields=status_code&access_token={TOK}")
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise SystemExit("インスタ側で失敗しました")
    r = api(f"https://graph.facebook.com/{V}/{IG}/media_publish",
            {"creation_id": cid, "access_token": TOK})
    return r.get("id")


def main():
    kyou = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")
    y = json.load(open("yotei.json", encoding="utf-8"))
    nokori, dashita = [], []
    for t in y["予定"]:
        if t.get("出した") or t["日"] > kyou:
            nokori.append(t); continue
        try:
            mid = dasu(t["動画"], t["本文"])
            t["出した"] = datetime.datetime.utcnow().isoformat()[:19]
            t["投稿ID"] = mid
            dashita.append(t["動画"])
        except Exception as e:
            t["失敗"] = str(e)[:200]
            print("出せませんでした:", t["動画"], e)
        nokori.append(t)
    y["予定"] = nokori
    json.dump(y, open("yotei.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("出した本数:", len(dashita), dashita)


if __name__ == "__main__":
    main()
