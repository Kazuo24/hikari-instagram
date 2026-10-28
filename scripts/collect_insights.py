"""Fetch insights for every posted item and write a Markdown table.

Usage: python3 -I collect_insights.py <posted.json> <queue.json> <out.md>
"""
import json, sys, urllib.parse, urllib.request

API = "https://graph.instagram.com/v21.0"
METRICS = "reach,likes,saved,shares,comments,total_interactions"


def get(path, params):
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:200]}


def main():
    posted = json.load(open(sys.argv[1], encoding="utf-8"))
    queue = {q["id"]: q for q in json.load(open(sys.argv[2], encoding="utf-8"))}
    me = get("me", {"fields": "followers_count,media_count"})
    rows = []
    for p in posted:
        d = get(f"{p['media_id']}/insights", {"metric": METRICS})
        v = {m["name"]: m["values"][0]["value"] for m in d.get("data", [])}
        first = queue.get(p["id"], {}).get("caption", "").splitlines()[0][:40]
        rows.append((p["id"], p["posted_at"][:16], first, v, p.get("permalink", "")))
    rows.sort(key=lambda r: -(r[3].get("saved", 0) * 3 + r[3].get("shares", 0) * 3 + r[3].get("likes", 0)))
    lines = [f"# Instagram 投稿の数字（{me.get('followers_count')}フォロワー / {me.get('media_count')}投稿）", "",
             "スコア順（保存×3＋シェア×3＋いいね）", "",
             "| ID | 投稿日時(UTC) | 1行目 | リーチ | いいね | 保存 | シェア | コメント | リンク |", "|---|---|---|---|---|---|---|---|---|"]
    for i, t, first, v, link in rows:
        lines.append(f"| {i} | {t} | {first} | {v.get('reach','-')} | {v.get('likes','-')} | {v.get('saved','-')} | {v.get('shares','-')} | {v.get('comments','-')} | {link} |")
    open(sys.argv[3], "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
