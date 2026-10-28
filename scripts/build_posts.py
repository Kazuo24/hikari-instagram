"""Render slides for new posts and append them to queue.json.

Usage: python3 -I build_posts.py <posts.json> <queue.json>
posts.json: [{"id", "caption", "slides": [{"type": "cover"|"point"|"end", ...}]}]
Images go to images/<id>-<n>.jpg in this repo; push the repo before the post time.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_card

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    posts = json.load(open(sys.argv[1], encoding="utf-8"))
    queue_path = sys.argv[2]
    queue = json.load(open(queue_path, encoding="utf-8"))
    known = {q["id"] for q in queue}
    for p in posts:
        if p["id"] in known:
            continue
        images, n = [], len(p["slides"])
        for i, s in enumerate(p["slides"], 1):
            rel = f"images/{p['id']}-{i}.jpg"
            out = os.path.join(ROOT, rel)
            if s["type"] == "point":
                make_card.make_point(out, s["num"], f"{i}/{n}", s["head"], s["body"])
            else:
                make_card.make(out, s["tag"], s["title"], s.get("sub", []))
            images.append(rel)
        queue.append({"id": p["id"], "images": images, "caption": p["caption"]})
        print("added", p["id"], len(images))
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
