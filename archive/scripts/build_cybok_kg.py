"""
Download official CyBOK v1.1.0 PDF, extract text, run CyBOKExtractor merge,
and rebuild NetworkX + JSON knowledge graph artifacts.

CyBOK is distributed under the Open Government Licence v3.0 (see cybok.org).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CYBOK_DIR = PROJECT_ROOT / "data" / "cybok"
PDF_NAME = "CyBOK_v1.1.0.pdf"
TEXT_NAME = "cybok_full_text.txt"
OFFICIAL_PDF_URL = "https://www.cybok.org/media/downloads/CyBOK_v1.1.0.pdf"


def ensure_src_on_path() -> None:
    src = str(PROJECT_ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)


def download_pdf(dest: Path, url: str, force: bool) -> None:
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        print(f"Using existing PDF: {dest}")
        return
    print(f"Downloading CyBOK PDF from {url} ...")
    r = requests.get(url, timeout=120, stream=True)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    n = 0
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            if chunk:
                f.write(chunk)
                n += len(chunk)
                if total:
                    print(f"  ... {n / total * 100:.1f}%", end="\r", flush=True)
    print(f"\nSaved PDF ({dest.stat().st_size // (1024 * 1024)} MB) -> {dest}")


def pdf_to_text(pdf_path: Path, text_path: Path, force: bool) -> None:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise SystemExit(
            "Missing dependency: pip install pypdf\n" + str(e)
        ) from e

    if text_path.exists() and not force:
        print(f"Using existing extracted text: {text_path}")
        return

    print(f"Extracting text from PDF ({pdf_path.name}) ...")
    reader = PdfReader(str(pdf_path))
    parts = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        parts.append(t)
        if (i + 1) % 50 == 0:
            print(f"  pages {i + 1}/{len(reader.pages)}")
    body = "\n\n".join(parts)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(body, encoding="utf-8", errors="replace")
    print(f"Wrote {len(body)} characters -> {text_path}")


def run_extractor(text_path: Path, rebuild_graph: bool) -> dict:
    ensure_src_on_path()
    from cybok_extractor import CyBOKExtractor

    extractor = CyBOKExtractor(str(text_path))
    stats = extractor.run()

    if rebuild_graph:
        print("\nRebuilding knowledge graph (NetworkX + pickle + JSON) ...")
        from kg_builder import KnowledgeGraphBuilder

        kg = KnowledgeGraphBuilder()
        kg.build_graph()
        kg.save_graph()
        kg.export_to_json()
        print("Done: knowledge_graph.pkl and knowledge_graph.json updated.")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build / refresh CyBOK-backed KG from official PDF.")
    parser.add_argument("--skip-download", action="store_true", help="Reuse PDF if present")
    parser.add_argument("--skip-extract", action="store_true", help="Reuse cybok_full_text.txt if present")
    parser.add_argument("--no-rebuild-graph", action="store_true", help="Only update CSVs, skip kg_builder")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--force-extract", action="store_true")
    args = parser.parse_args()

    cybok_dir = CYBOK_DIR
    pdf_path = cybok_dir / PDF_NAME
    text_path = cybok_dir / TEXT_NAME

    if not args.skip_download:
        download_pdf(pdf_path, OFFICIAL_PDF_URL, force=args.force_download)
    elif not pdf_path.exists():
        print(f"No PDF at {pdf_path}; run without --skip-download.")
        raise SystemExit(1)

    if not args.skip_extract:
        pdf_to_text(pdf_path, text_path, force=args.force_extract)
    elif not text_path.exists():
        print(f"No text at {text_path}; run without --skip-extract.")
        raise SystemExit(1)

    stats = run_extractor(text_path, rebuild_graph=not args.no_rebuild_graph)
    print("\nCyBOK merge stats:", stats)


if __name__ == "__main__":
    main()
