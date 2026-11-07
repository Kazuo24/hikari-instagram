"""Post the next unposted item from queue.json to Instagram.

Auth is injected by the environment's network secret for graph.instagram.com,
so no token is read or stored here.
Usage: python3 -I post_next.py <queue.json> <posted.json> [--dry-run]
"""
import json, sys, time, urllib.parse, urllib.request

API = "https://graph.instagram.com/v21.0"
IMG_BASE = "https://raw.githubusercontent.com/Kazuo24/hikari-instagram/main/"
EXPECTED_USER = "hikarihikari.ai.jp"
# Kazuo 2026-11-05: every post carries the note link, and a product (PR) post
# never goes out first: it always follows a non-PR post.
NOTE_URL = "https://note.com/hikarihikari01/n/n1a20f0852603"
NOTE_BLOCK = "📖 ヒカリのnote（自己紹介・お得情報まとめ）\n" + NOTE_URL


def is_pr(item):
    return item["caption"].lstrip().startswith("【PR】")


def with_note(caption):
    if NOTE_URL in caption:
        return caption
    lines = caption.rstrip().split("\n")
    # put the note link just above the hashtag line, if there is one
    if lines and lines[-1].lstrip().startswith("#"):
        return "\n".join(lines[:-1]).rstrip() + "\n\n" + NOTE_BLOCK + "\n" + lines[-1]
    return caption.rstrip() + "\n\n" + NOTE_BLOCK


def pick_next(queue, posted):
    done = {p["id"] for p in posted}
    pending = [q for q in queue if q["id"] not in done]
    if not pending:
        return None
    by_id = {q["id"]: q for q in queue}
    last = by_id.get(posted[-1]["id"]) if posted else None
    last_was_pr = last is None or is_pr(last)  # nothing posted yet counts as "no warm-up"
    if is_pr(pending[0]) and last_was_pr:
        warm = next((q for q in pending if not is_pr(q)), None)
        if warm is not None:
            return warm
    return pending[0]


def call(method, path, params=None):
    url = f"{API}/{path}"
    data = None
    if params:
        enc = urllib.parse.urlencode(params)
        if method == "GET":
            url += "?" + enc
        else:
            data = enc.encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API error {e.code}: {e.read().decode()}")


def wait_ready(cid, item_id):
    for _ in range(60):
        st = call("GET", cid, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            return
        if st == "ERROR":
            raise SystemExit(f"Container error for {item_id}")
        time.sleep(5)
    raise SystemExit(f"Container not ready for {item_id}: {st}")


def publish(cid):
    # Code 9007 means "not ready yet": nothing was published, so retrying is safe.
    for attempt in range(6):
        try:
            return call("POST", "me/media_publish", {"creation_id": cid})
        except SystemExit as e:
            if "9007" not in str(e) or attempt == 5:
                raise
            time.sleep(10)


def main():
    queue_path, posted_path = sys.argv[1], sys.argv[2]
    dry = "--dry-run" in sys.argv
    queue = json.load(open(queue_path, encoding="utf-8"))
    posted = json.load(open(posted_path, encoding="utf-8"))
    item = pick_next(queue, posted)
    if item is None:
        print("QUEUE_EMPTY")
        return

    me = call("GET", "me", {"fields": "user_id,username"})
    if me.get("username") != EXPECTED_USER:
        raise SystemExit(f"Wrong account: {me.get('username')}")

    caption = with_note(item["caption"])
    images = item.get("images") or [item["image"]]
    urls = [IMG_BASE + i for i in images]
    print(f"Next: {item['id']} {urls}")
    if dry:
        print(caption)
        return

    if len(urls) == 1:
        cid = call("POST", "me/media", {"image_url": urls[0], "caption": caption})["id"]
    else:
        children = []
        for u in urls:
            child = call("POST", "me/media", {"image_url": u, "is_carousel_item": "true"})["id"]
            wait_ready(child, item["id"])
            children.append(child)
        cid = call("POST", "me/media", {"media_type": "CAROUSEL", "children": ",".join(children),
                                        "caption": caption})["id"]
    wait_ready(cid, item["id"])
    media = publish(cid)
    # Record the post right away, so a later API error (e.g. rate limit on the
    # permalink lookup, 2026-11-07) can never lead to a second, duplicate post.
    entry = {"id": item["id"], "media_id": media["id"], "permalink": None,
             "posted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    posted.append(entry)
    with open(posted_path, "w", encoding="utf-8") as f:
        json.dump(posted, f, ensure_ascii=False, indent=2)
    try:
        info = call("GET", media["id"], {"fields": "permalink"})
        entry["permalink"] = info.get("permalink")
        with open(posted_path, "w", encoding="utf-8") as f:
            json.dump(posted, f, ensure_ascii=False, indent=2)
    except SystemExit as e:
        print(f"Permalink lookup failed (post is published): {e}")
    info = {"permalink": entry["permalink"]}
    print(f"POSTED {item['id']} {info.get('permalink')}")


if __name__ == "__main__":
    main()
