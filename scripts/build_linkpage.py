"""Build docs/index.html (the Instagram profile link page) from data/products.json.

Newest posts first. Usage: python3 -I build_linkpage.py
"""
import html, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    prods = json.load(open(os.path.join(ROOT, "data", "products.json"), encoding="utf-8"))
    prods.sort(key=lambda p: -int(p["post"]))
    cards = []
    for p in prods:
        cards.append(
            f'<a class="card" href="{html.escape(p["url"])}" target="_blank" rel="sponsored noopener">'
            f'<span class="name">{html.escape(p["name"])}</span>'
            f'<span class="price">{int(p["price"]):,}円〜</span></a>')
    page = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ヒカリのおすすめ</title>
<style>
:root{{--bg:#fbe5ea;--card:#fff;--ink:#5c2d3a;--sub:#806c72;--pink:#e77697}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Hiragino Maru Gothic ProN","Zen Maru Gothic",sans-serif}}
main{{max-width:520px;margin:0 auto;padding:24px 16px 48px}}
h1{{font-size:22px;text-align:center;margin:8px 0 4px}}
p.lead{{text-align:center;color:var(--sub);font-size:13px;margin:0 0 20px}}
.card{{display:block;background:var(--card);border-radius:16px;padding:14px 16px;margin:10px 0;text-decoration:none;color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.no{{display:inline-block;background:var(--pink);color:#fff;border-radius:999px;font-size:11px;padding:2px 10px;margin-bottom:6px}}
.name{{display:block;font-weight:bold;font-size:15px}}
.price{{display:block;color:var(--sub);font-size:13px;margin-top:4px}}
footer{{text-align:center;color:var(--sub);font-size:11px;margin-top:24px;line-height:1.7}}
</style></head><body><main>
<h1>✨ヒカリのおすすめ✨</h1>
<p class="lead">Instagramで紹介した商品です（新しい順）</p>
{''.join(cards)}
<footer>※PR・アフィリエイト広告を含みます（楽天アフィリエイト）<br>価格は紹介時点のものです。最新の情報は各ショップでご確認ください。<br>@hikarihikari.ai.jp</footer>
</main></body></html>
"""
    open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8").write(page)
    print(len(prods), "products")


if __name__ == "__main__":
    main()
