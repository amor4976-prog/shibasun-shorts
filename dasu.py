#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""予約表を見て、今日のぶんをインスタへ出す。GitHubが毎日呼ぶ。"""
import subprocess, hashlib, fcntl
import json, os, time, urllib.parse, urllib.request, datetime, sys

V = "v25.0"
BASE = f"https://graph.instagram.com/{V}"
TOK = os.environ.get("IG_TOKEN", "")
NAMA = "https://raw.githubusercontent.com/amor4976-prog/shibasun-shorts/main/"


def api(url, data=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None)
    try:
        return json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        raise SystemExit("インスタが断りました: " + e.read().decode()[:500])


def watashi():
    """この鍵でつながっているインスタの番号を聞く"""
    j = api(f"{BASE}/me?fields=user_id,username&access_token={TOK}")
    return str(j.get("user_id") or j.get("id")), j.get("username")


def dasu(mp4_path, honbun, byou=4.0):
    ig, username = watashi()
    if username != "shibasun_daiku":
        raise RuntimeError("投稿先が社長のアカウントと一致しません")
    url = NAMA + urllib.parse.quote(mp4_path)
    j = api(f"{BASE}/{ig}/media",
            {"media_type": "REELS", "video_url": url, "caption": honbun,
             "thumb_offset": str(int(float(byou) * 1000)),   # 表紙＝テロップが一番出ている所
             "access_token": TOK})
    cid = j["id"]
    for _ in range(60):
        time.sleep(10)
        st = api(f"{BASE}/{cid}?fields=status_code&access_token={TOK}")
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise SystemExit("インスタ側で失敗しました")
    else:
        raise RuntimeError("インスタの処理が完了していません。公開せず停止します")
    r = api(f"{BASE}/{ig}/media_publish",
            {"creation_id": cid, "access_token": TOK})
    return r.get("id")


def tameshi():
    """鍵が生きているかだけ見る。中身は出さない。"""
    try:
        ig, name = watashi()
        print("鍵は生きています。つながっている先:", name)
    except SystemExit as e:
        print("鍵が使えません:", e)
        raise


def save(y):
    with open("yotei.json.tmp", "w", encoding="utf-8") as f:
        json.dump(y, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace("yotei.json.tmp", "yotei.json")


def keys(t):
    """Use both episode identity and video identity, including re-numbered copies."""
    result = {"number:" + str(t["番号"]), "path:" + t["動画"]}
    if os.path.isfile(t["動画"]):
        h = hashlib.sha256()
        with open(t["動画"], "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        result.add("sha256:" + h.hexdigest())
    return result


def checkpoint(y):
    save(y)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # No publishing request until its intent is durably stored on main.
        for args in (["git", "config", "user.name", "shibasun-bot"],
                     ["git", "config", "user.email", "bot@shibasun.jp"],
                     ["git", "add", "yotei.json"]):
            subprocess.run(args, check=True, capture_output=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if diff.returncode == 1:
            subprocess.run(["git", "commit", "-m", "投稿状態を記録"], check=True, capture_output=True)
        elif diff.returncode != 0:
            raise RuntimeError("投稿記録の差分を確認できません")
        subprocess.run(["git", "push", "origin", "HEAD:main"], check=True, capture_output=True)


def main():
    # Protect local invocations too, not only GitHub workflow concurrency.
    with open(".instagram-publisher.lock", "a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("別の投稿処理が動作中です")
        return run_schedule()


def run_schedule():
    kyou = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")
    with open("yotei.json", encoding="utf-8") as f:
        y = json.load(f)
    identity = [(t, keys(t)) for t in y["予定"]]
    blocked = set()
    for t, ids in identity:
        if t.get("投稿ID") or t.get("出した") or t.get("要確認"):
            blocked.update(ids)
    sent, failed = [], False
    for t, ids in identity:
        if ids & blocked or t["日"] > kyou:
            continue
        blocked.update(ids)
        t["要確認"] = "送信開始。結果不明時は再送禁止・投稿先で照合"
        try:
            checkpoint(y)
            mid = dasu(t["動画"], t["本文"], t.get("表紙秒", 4.0))
            if not mid:
                raise RuntimeError("投稿IDが取得できませんでした")
            t["投稿ID"] = mid
            t["出した"] = datetime.datetime.utcnow().isoformat()[:19]
            t.pop("要確認", None)
            t.pop("失敗", None)
            checkpoint(y)
            sent.append(t["動画"])
        except (Exception, SystemExit) as e:
            # A previous remote intent remains even if this final write fails.
            t["失敗"] = type(e).__name__ + ": 要確認・自動再送停止"
            save(y)
            print("出せませんでした:", t["動画"], "要確認・自動再送停止")
            failed = True
            break
    save(y)
    print("出した本数:", len(sent), sent)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    if os.environ.get("TAMESHI"):
        tameshi()
    else:
        main()
