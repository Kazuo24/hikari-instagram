#!/usr/bin/env python3
"""Claude の会話ログを Obsidian 用の Markdown ノートに変換する。

使い方:
  # claude.ai の書き出しデータ（zip でも conversations.json でも可）を取り込む
  python3 scripts/claude_to_obsidian.py export ~/Downloads/data-2026-11-13.zip

  # Claude Code のセッション記録 (.jsonl) を 1 本取り込む
  python3 scripts/claude_to_obsidian.py code ~/.claude/projects/<proj>/<session>.jsonl

  # Claude Code のフックから呼ぶ（標準入力に hook の JSON が来る）
  python3 scripts/claude_to_obsidian.py hook               # 書いてコミット・push
  python3 scripts/claude_to_obsidian.py hook --write-only  # 書くだけ

同じ会話を何度取り込んでも、frontmatter の uuid を見て同じノートを上書きするので重複しない。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

def _root() -> Path:
    """書き込み先のリポジトリ。フックからは CLAUDE_PROJECT_DIR、手動なら git の最上位。"""
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        return Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve()
    here = Path(__file__).resolve().parent
    r = subprocess.run(["git", "-C", str(here), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 else here.parent


VAULT = _root()
CHAT_DIR = VAULT / "Claude" / "チャット"
# obsidian 以外のリポジトリでは CLAUDE_LOG_DIR=.claude-logs にして、そこへ書く（毎日 obsidian に集める）
CODE_DIR = VAULT / os.environ.get("CLAUDE_LOG_DIR", "Claude/Claude Code")
TZ = ZoneInfo(os.environ.get("CLAUDE_LOG_TZ", "Asia/Tokyo"))  # 表示する時刻のタイムゾーン
TOOL_RESULT_LIMIT = 1500  # ツール結果は長くなりがちなので切り詰める


# ---------- 共通 ----------

def safe_name(title: str, limit: int = 60) -> str:
    title = re.sub(r"[\\/:*?\"<>|#^\[\]\n\r\t]", " ", title or "")
    title = re.sub(r"\s+", " ", title).strip().rstrip(".")
    return (title[:limit].strip() or "無題")


def local_dt(iso: str | None) -> datetime:
    if not iso:
        return datetime.now(TZ)
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
    except ValueError:
        return datetime.now(TZ)


def yaml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def find_existing(folder: Path, uuid: str) -> Path | None:
    if not folder.exists():
        return None
    needle = f"uuid: {uuid}"
    for p in folder.rglob("*.md"):
        try:
            with p.open(encoding="utf-8") as f:
                head = f.read(1000)
        except OSError:
            continue
        if needle in head:
            return p
    return None


def write_note(folder: Path, uuid: str, created: datetime, title: str, body: str) -> Path:
    """uuid が同じノートがあれば上書き、なければ 年/月 フォルダに新規作成。"""
    existing = find_existing(folder, uuid)
    if existing:
        path = existing
    else:
        sub = folder / created.strftime("%Y") / created.strftime("%m")
        sub.mkdir(parents=True, exist_ok=True)
        base = f"{created:%Y-%m-%d} {safe_name(title)}"
        path = sub / f"{base}.md"
        n = 2
        while path.exists():
            path = sub / f"{base} ({n}).md"
            n += 1
    if not path.exists() or path.read_text(encoding="utf-8") != body:
        path.write_text(body, encoding="utf-8")
    return path


def fold(kind: str, title: str, text: str) -> str:
    """Obsidian の折りたたみ callout にする。"""
    text = text.rstrip()
    lines = [f"> [!{kind}]- {title}"]
    for line in text.splitlines() or [""]:
        lines.append(f"> {line}")
    return "\n".join(lines)


def truncate(text: str, limit: int = TOOL_RESULT_LIMIT) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n…（{len(text) - limit} 文字省略）"


def as_code(text: str, lang: str = "") -> str:
    fence = "````" if "```" in text else "```"
    return f"{fence}{lang}\n{text.rstrip()}\n{fence}"


# ---------- claude.ai の書き出しデータ ----------

def load_export(path: Path) -> list[dict]:
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.endswith("conversations.json"))
            return json.loads(z.read(name).decode("utf-8"))
    if path.is_dir():
        path = path / "conversations.json"
    return json.loads(path.read_text(encoding="utf-8"))


def render_chat_message(msg: dict) -> str:
    parts: list[str] = []
    blocks = msg.get("content") or []
    if not blocks and msg.get("text"):
        blocks = [{"type": "text", "text": msg["text"]}]
    for b in blocks:
        t = b.get("type")
        if t == "text" and b.get("text", "").strip():
            parts.append(b["text"].strip())
        elif t == "thinking" and b.get("thinking", "").strip():
            parts.append(fold("abstract", "思考", b["thinking"]))
        elif t == "tool_use":
            inp = json.dumps(b.get("input", {}), ensure_ascii=False, indent=2)
            parts.append(fold("example", f"ツール: {b.get('name', '')}", as_code(truncate(inp), "json")))
        elif t == "tool_result":
            content = b.get("content")
            if isinstance(content, list):
                content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
            parts.append(fold("quote", "ツール結果", truncate(str(content or ""))))
    for a in (msg.get("attachments") or []):
        name = a.get("file_name") or "添付"
        text = a.get("extracted_content") or ""
        parts.append(fold("note", f"添付: {name}", truncate(text) if text else "（本文なし）"))
    for f in (msg.get("files") or []):
        parts.append(f"📎 {f.get('file_name', 'ファイル')}")
    return "\n\n".join(parts)


def import_export(path: Path) -> list[Path]:
    written = []
    for conv in load_export(path):
        msgs = conv.get("chat_messages") or []
        if not msgs:
            continue
        uuid = conv["uuid"]
        title = conv.get("name") or "無題"
        created = local_dt(conv.get("created_at"))
        updated = local_dt(conv.get("updated_at"))
        out = [
            "---",
            f"uuid: {uuid}",
            f"title: {yaml_str(title)}",
            "source: claude.ai",
            f"created: {created:%Y-%m-%dT%H:%M}",
            f"updated: {updated:%Y-%m-%dT%H:%M}",
            f"messages: {len(msgs)}",
            f"url: https://claude.ai/chat/{uuid}",
            "tags: [claude, claude/chat]",
            "---",
            "",
            f"# {title}",
            "",
        ]
        if conv.get("summary"):
            out += [fold("summary", "要約", conv["summary"]), ""]
        for m in msgs:
            who = "🧑 あなた" if m.get("sender") == "human" else "🤖 Claude"
            ts = local_dt(m.get("created_at"))
            body = render_chat_message(m)
            if not body:
                continue
            out += [f"### {who} · {ts:%Y-%m-%d %H:%M}", "", body, ""]
        written.append(write_note(CHAT_DIR, uuid, created, title, "\n".join(out)))
    return written


# ---------- Claude Code のセッション記録 ----------

SKIP_PREFIXES = ("<command-", "<local-command", "<system-reminder>", "Caveat:")


def tool_summary(name: str, inp: dict) -> str:
    for key in ("command", "file_path", "pattern", "url", "query", "description", "prompt"):
        if isinstance(inp.get(key), str):
            v = inp[key].strip().splitlines()[0] if inp[key].strip() else ""
            return f"{name}: {v[:80]}"
    return name


def import_code(transcript: Path) -> Path | None:
    entries = []
    with transcript.open(encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return import_entries(entries, transcript.stem)


def import_entries(entries: list[dict], session_id: str, title: str | None = None,
                   extra: dict | None = None) -> Path | None:
    """Claude Code 形式のエントリ列を 1 本のノートにする。extra は frontmatter に足す項目。"""
    first_ts = last_ts = None
    cwd = branch = None
    out_msgs: list[str] = []
    n_user = 0
    last_role = ""

    for e in entries:
        if e.get("type") == "summary" and e.get("summary"):
            title = title or e["summary"]
        if e.get("type") not in ("user", "assistant") or e.get("isSidechain") or e.get("isMeta"):
            continue
        session_id = e.get("sessionId", session_id)
        cwd = cwd or e.get("cwd")
        branch = branch or e.get("gitBranch")
        ts = local_dt(e.get("timestamp"))
        first_ts = first_ts or ts
        last_ts = ts
        content = (e.get("message") or {}).get("content")
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        parts: list[str] = []
        is_human_text = False
        for b in content or []:
            t = b.get("type")
            if t == "text":
                text = b.get("text", "").strip()
                if not text or text.startswith(SKIP_PREFIXES):
                    continue
                parts.append(text)
                is_human_text = e["type"] == "user"
            elif t == "tool_use":
                inp = b.get("input") or {}
                parts.append(fold("example", tool_summary(b.get("name", ""), inp),
                                  as_code(truncate(json.dumps(inp, ensure_ascii=False, indent=2)), "json")))
            elif t == "tool_result":
                c = b.get("content")
                if isinstance(c, list):
                    c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
                if c:
                    parts.append(fold("quote", "結果", as_code(truncate(str(c)))))
        if not parts:
            continue
        if e["type"] == "user" and is_human_text:
            n_user += 1
            if not title:
                title = parts[0].splitlines()[0]
            out_msgs += [f"### 🧑 あなた · {ts:%Y-%m-%d %H:%M}", "", *parts, ""]
            last_role = "user"
        else:  # Claude の応答、またはツール結果だけの user エントリ
            if last_role != "claude":
                out_msgs += ["### 🤖 Claude", ""]
                last_role = "claude"
            out_msgs += ["\n\n".join(parts), ""]

    if n_user == 0:
        return None
    title = title or "Claude Code セッション"
    project = Path(cwd).name if cwd else ""
    body_lines = out_msgs

    head = [
        "---",
        f"uuid: {session_id}",
        f"title: {yaml_str(title[:100])}",
        "source: claude-code",
        f"project: {yaml_str(project)}",
        f"branch: {yaml_str(branch or '')}",
        f"created: {first_ts:%Y-%m-%dT%H:%M}",
        f"updated: {last_ts:%Y-%m-%dT%H:%M}",
        f"prompts: {n_user}",
        *[f"{k}: {yaml_str(str(v))}" for k, v in (extra or {}).items()],
        "tags: [claude, claude/code]",
        "---",
        "",
        f"# {title[:100]}",
        "",
    ]
    return write_note(CODE_DIR, session_id, first_ts, title, "\n".join(head + body_lines))


# ---------- フック ----------

def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(VAULT), *args], capture_output=True, text=True, timeout=60)


def commit_and_push(path: Path) -> None:
    if os.environ.get("CLAUDE_LOG_NO_COMMIT"):
        return
    rel = str(path.relative_to(VAULT))
    git("add", "--", rel)
    if git("diff", "--cached", "--quiet", "--", rel).returncode == 0:
        return
    git("commit", "-q", "-m", f"Claude ログ: {path.stem}", "--", rel)
    if os.environ.get("CLAUDE_LOG_NO_PUSH"):
        return
    if git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").returncode == 0:
        git("push", "-q")
    else:
        branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if branch and branch != "HEAD" and git("remote").stdout.strip():
            git("push", "-q", "-u", "origin", branch)


def run_hook(write_only: bool = False) -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    tp = data.get("transcript_path")
    if not tp or not Path(tp).exists():
        return
    path = import_code(Path(tp))
    if path and not write_only:
        commit_and_push(path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("export", help="claude.ai の書き出しデータを取り込む")
    p.add_argument("path", type=Path)
    p = sub.add_parser("code", help="Claude Code の .jsonl を取り込む")
    p.add_argument("paths", type=Path, nargs="+")
    p = sub.add_parser("hook", help="Claude Code フック用（標準入力から JSON を読む）")
    p.add_argument("--write-only", action="store_true", help="ノートを書くだけでコミット・push しない")
    args = ap.parse_args()

    if args.cmd == "hook":
        try:
            run_hook(args.write_only)
        except Exception as ex:  # フックの失敗で会話を止めない
            print(f"claude_to_obsidian: {ex}", file=sys.stderr)
        return
    if args.cmd == "export":
        written = import_export(args.path.expanduser())
    else:
        written = [p for p in (import_code(x.expanduser()) for x in args.paths) if p]
    for w in written:
        print(w.relative_to(VAULT))
    print(f"{len(written)} 件のノートを書き出しました", file=sys.stderr)


if __name__ == "__main__":
    main()
