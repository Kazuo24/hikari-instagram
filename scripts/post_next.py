"""Post the next unposted item from queue.json to Instagram.

Auth is injected by the environment's network secret for graph.instagram.com,
so no token is read or stored here.
Usage: python3 -I post_next.py <queue.json> <posted.json> [--dry-run]
"""
import json, sys, time, urllib.parse, urllib.request

API = "https://graph.instagram.com/v21.0"
IMG_BASE = "https://raw.githubusercontent.com/Kazuo24/hikari-instagram/main/"
EXPECTED_USER = "hikarihikari.ai.jp"


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


def main():
    queue_path, posted_path = sys.argv[1], sys.argv[2]
    dry = "--dry-run" in sys.argv
    queue = json.load(open(queue_path, encoding="utf-8"))
    posted = json.load(open(posted_path, encoding="utf-8"))
    done = {p["id"] for p in posted}
    item = next((q for q in queue if q["id"] not in done), None)
    if item is None:
        print("QUEUE_EMPTY")
        return

    me = call("GET", "me", {"fields": "user_id,username"})
    if me.get("username") != EXPECTED_USER:
        raise SystemExit(f"Wrong account: {me.get('username')}")

    image_url = IMG_BASE + item["image"]
    print(f"Next: {item['id']} {image_url}")
    if dry:
        return

    container = call("POST", "me/media", {"image_url": image_url, "caption": item["caption"]})
    cid = container["id"]
    for _ in range(20):
        st = call("GET", cid, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            raise SystemExit(f"Container error for {item['id']}")
        time.sleep(3)
    media = call("POST", "me/media_publish", {"creation_id": cid})
    info = call("GET", media["id"], {"fields": "permalink"})

    posted.append({"id": item["id"], "media_id": media["id"],
                   "permalink": info.get("permalink"),
                   "posted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    with open(posted_path, "w", encoding="utf-8") as f:
        json.dump(posted, f, ensure_ascii=False, indent=2)
    print(f"POSTED {item['id']} {info.get('permalink')}")


if __name__ == "__main__":
    main()
