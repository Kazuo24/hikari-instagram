"""Make 'line by line' versions of a post's first slide, for a Reel that moves
in its first second (PDCA 2026-11-17: static text cards lose viewers in ~1s).

Usage: python3 -I make_reveal.py <posts.json> <id> [<id> ...]
Writes images/<id>-1r1.jpg, -1r2.jpg ... (title lines shown one more each time;
hidden lines are blanked so the layout does not jump) and prints the
make_reel.py arguments to use.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_card

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEP = 0.4  # seconds per revealed line


def main():
    posts = {p["id"]: p for p in json.load(open(sys.argv[1], encoding="utf-8"))}
    for pid in sys.argv[2:]:
        s = posts[pid]["slides"][0]
        title = s["title"]
        parts = []
        for k in range(1, len(title)):
            shown = title[:k] + ["　" * len(t) for t in title[k:]]
            rel = f"images/{pid}-1r{k}.jpg"
            make_card.make(os.path.join(ROOT, rel), s["tag"], shown, [" "] if s.get("sub") else [])
            parts.append(rel)
        rest = 8.0 - 4.0 - STEP * len(parts)
        durs = [STEP] * len(parts) + [round(rest, 2), 4.0]
        imgs = parts + [f"images/{pid}-1.jpg", f"images/{pid}-2.jpg"]
        print(pid, "--durs", ",".join(str(d) for d in durs), " ".join(imgs))


if __name__ == "__main__":
    main()
