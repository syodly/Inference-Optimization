"""Validate the exact paper-only publication tree and its local dependencies."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import re
import sys


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in {"href", "src", "poster", "xlink:href"} and value:
                self.links.append(value)


def js_json(text, name):
    match = re.search(r"\bconst\s+" + re.escape(name) + r"\s*=\s*", text)
    if not match:
        raise ValueError(f"Missing public data: {name}")
    return json.JSONDecoder().raw_decode(text[match.end():])[0]


def validate(root):
    root = root.resolve()
    site = root / "site"
    manifest = json.loads((root / "public-files.json").read_text(encoding="utf-8"))
    expected = set(manifest["site_files"])
    actual = {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()}
    errors = []
    if actual != expected:
        errors.append({"unexpected_files": sorted(actual-expected), "missing_files": sorted(expected-actual)})
    approved_root_files = {"README.md", "LICENSE", ".gitignore", "public-files.json",
                           ".github/workflows/pages.yml", "tools/check_public_site.py"}
    for file in root.rglob("*"):
        rel = file.relative_to(root)
        if ".git" in rel.parts or "__pycache__" in rel.parts or not file.is_file():
            continue
        if rel.parts[0] != "site" and rel.as_posix() not in approved_root_files:
            errors.append({"unapproved_repository_file": rel.as_posix()})

    blocked = re.compile(r"topic[12][-_]|research-update-|runtime-codesign|experiments/|"
                         r"runtime-v\d|RESEARCH_LOG|/home/|C:[/\\]|10\.26\.42\.189|"
                         r"实验进展|研究进展|我们的实验|本轮实验", re.I)
    references_checked = 0

    def check_ref(owner, reference):
        nonlocal references_checked
        parsed = urlsplit(reference)
        if parsed.scheme in {"http", "https", "mailto", "data"}:
            return
        if parsed.scheme or parsed.netloc:
            errors.append({"invalid_reference": reference, "file": owner.relative_to(site).as_posix()})
            return
        if not parsed.path:
            return
        target = (owner.parent / unquote(parsed.path)).resolve()
        references_checked += 1
        if not target.is_relative_to(site) or not target.is_file():
            errors.append({"broken_local_reference": reference, "file": owner.relative_to(site).as_posix()})

    for file in site.rglob("*"):
        if file.is_symlink():
            errors.append({"symlink": file.relative_to(site).as_posix()})
        if file.suffix not in {".html", ".js", ".css", ".svg"}:
            continue
        text = file.read_text(encoding="utf-8")
        for match in blocked.finditer(text):
            errors.append({"private_content_marker": match.group(), "file": file.relative_to(site).as_posix()})
        if file.suffix in {".html", ".svg"}:
            parser = References()
            parser.feed(text)
            for reference in parser.links:
                check_ref(file, reference)
        for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", text):
            check_ref(file, match.group(2))

    archive = site / "LLM_Optimization_Milestone"
    papers = js_json((archive / "milestone-data.js").read_text(encoding="utf-8"), "PAPERS")
    catalog = js_json((archive / "architecture-catalog.js").read_text(encoding="utf-8"), "ARCHITECTURE_CATALOG")
    if len({p[0] for p in papers}) != len(papers):
        errors.append({"duplicate_paper_ids": True})
    if {p[0] for p in papers} != {p["id"] for p in catalog}:
        errors.append({"catalog_paper_mismatch": True})
    for paper in catalog:
        check_ref(archive / "architecture-catalog.js", paper["href"])
    workflow = (root / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    if not re.search(r"path:\s*site\s*$", workflow, re.M):
        errors.append({"deployment_must_upload_only_site": True})
    result = {"ok": not errors, "public_files": len(actual), "papers": len(papers),
              "paper_summary_pages": len(list((archive / "papers").glob("paper-*.html"))),
              "local_references_checked": references_checked, "errors": errors}
    return result


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = validate(Path(__file__).resolve().parents[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["ok"] else 1)
