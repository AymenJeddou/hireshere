"""Build the technical guide: docs/guide/*.html chapters -> one HTML -> PDF (headless Edge).

    python docs/guide/build.py [--pdf PATH]

Chapters are plain HTML with placeholders, so every code excerpt is copied from the real source
at build time and never drifts from it:
    {{py path name}}      a Python function or class (by name, via ast)
    {{js path name}}      a TS/JS/Astro `function name` / `const name` block (to its closing brace)
    {{lines path a-b}}    lines a to b of a file
    {{file path}}         a whole (short) file
"""

import argparse
import ast
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def code(text: str, path: str, label: str = "") -> str:
    lang = Path(path).suffix.lstrip(".")
    cap = f"{path}{' · ' + label if label else ''}"
    body = html.escape(text.rstrip("\n").expandtabs(4))
    return (
        f'<figure class="code"><figcaption>{html.escape(cap)}</figcaption>'
        f'<pre class="{lang}"><code>{body}</code></pre></figure>'
    )


def py_block(path: str, name: str) -> str:
    src = (ROOT / path).read_text("utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name == name
        ):
            lines = src.splitlines()
            start = min([d.lineno for d in node.decorator_list] + [node.lineno]) - 1
            return "\n".join(lines[start : node.end_lineno])
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == name for t in node.targets
        ):
            return ast.get_source_segment(src, node)
    raise SystemExit(f"not found: {name} in {path}")


def js_block(path: str, name: str) -> str:
    lines = (ROOT / path).read_text("utf-8").splitlines()
    pat = re.compile(
        rf"^\s*(export\s+)?(default\s+)?(async\s+)?(function\s+{re.escape(name)}\b|const\s+{re.escape(name)}\b|class\s+{re.escape(name)}\b)"
    )
    for i, line in enumerate(lines):
        if pat.match(line):
            indent = len(line) - len(line.lstrip())
            # one-liners end on the same line
            if line.rstrip().endswith((";", ")")) and "{" not in line:
                return line
            depth = 0
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth <= 0 and j > i or (depth <= 0 and lines[j].rstrip().endswith(("};", "}"))):
                    return "\n".join(
                        x[indent:] if x[:indent].strip() == "" else x for x in lines[i : j + 1]
                    )
    raise SystemExit(f"not found: {name} in {path}")


def expand(text: str) -> str:
    def rep(m):
        kind, arg = m.group(1), m.group(2).strip()
        if kind == "py":
            path, name = arg.split()
            return code(py_block(path, name), path, name)
        if kind == "js":
            path, name = arg.split()
            return code(js_block(path, name), path, name)
        if kind == "lines":
            path, rng = arg.split()
            a, b = (int(x) for x in rng.split("-"))
            lines = (ROOT / path).read_text("utf-8").splitlines()
            return code("\n".join(lines[a - 1 : b]), path, f"lines {a} to {b}")
        if kind == "file":
            return code((ROOT / arg).read_text("utf-8"), arg)
        raise SystemExit(f"unknown placeholder {kind}")

    return re.sub(r"\{\{(py|js|lines|file)\s+([^}]+)\}\}", rep, text)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", default=str(ROOT / "docs/guide/HiresHere-technical-guide.pdf"))
    args = p.parse_args()
    parts = sorted(HERE.glob("[0-9][0-9]-*.html"))
    body = "\n".join(expand(f.read_text("utf-8")) for f in parts)
    shell = (HERE / "shell.html").read_text("utf-8").replace("{{BODY}}", body)
    out = HERE / "guide.html"
    out.write_text(shell, "utf-8")
    pdf = Path(args.pdf)
    subprocess.run(
        [
            EDGE,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--allow-file-access-from-files",
            f"--print-to-pdf={pdf}",
            "--virtual-time-budget=10000",
            out.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    print(f"{len(parts)} chapters -> {out.name} -> {pdf} ({pdf.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
