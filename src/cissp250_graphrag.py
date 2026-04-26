"""
CISSP (or similar) exam PDF → PDF chunks + NetworkX GraphRAG → Ollama (MCQ + explanation).

1. Extract text with **pypdf** (``pip install pypdf``).
2. Parse multiple-choice items (``?`` + following ``A./B./C./D.`` lines, same heuristic as ``extract_pdf_questions``).
3. **Chunk** the full PDF for lexical retrieval: top chunks per question become ``document_context``.
4. **Traverse** the in-memory **NetworkX** KG via ``GraphRAGComplete`` (default; no Neo4j).
5. Call **Ollama** for grounded generation + certainty merge (``CHOICE:`` / ``final_predicted_option``).

Place your PDF (e.g. final 250) at::
    data/qa/CISSP_Final_250.pdf
or pass ``--pdf /path/to/file.pdf``. If you only have a text export, use ``--text-file``.

Examples::
    python src/cissp250_graphrag.py --dry-parse --pdf data/qa/CISSP_Final_250.pdf
    python src/cissp250_graphrag.py --text-file exam_dump.txt --limit 3
    python src/cissp250_graphrag.py --pdf data/qa/CISSP_Final_250.pdf --limit 5
    python src/cissp250_graphrag.py --pdf exam.pdf --limit 250 --out data/qa/out.jsonl --docx data/qa/report.docx --answer-key data/qa/keys.csv

Answer key formats (``--answer-key``)::

- **CSV** with headers such as ``index,answer`` or ``question,letter`` (1-based index).
- **JSON** list: ``[{"index": 1, "answer": "B"}, ...]`` or object ``{"1": "B", "2": "A"}``.
- **JSONL**: one object per line with ``index`` and ``answer`` / ``letter``.
- **Plain text**: one line per question in order; each line is a letter (``B``) or ``1,B``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = PROJECT_ROOT / "data" / "qa" / "CISSP_Final_250.pdf"

_INDEX_HEADER_ALIASES = frozenset(
    {"index", "q", "num", "no", "n", "question", "question_id", "id", "#"}
)
_ANSWER_HEADER_ALIASES = frozenset(
    {"answer", "letter", "key", "correct", "gold", "label", "solution"}
)


def _normalize_mcq_letter(s: str) -> Optional[str]:
    s = (s or "").strip().upper()
    if not s:
        return None
    c = s[0]
    return c if c in "ABCD" else None


def load_answer_key(path: Path) -> Dict[int, str]:
    """
    Map 1-based question index -> 'A'..'D'.

    Supports .csv (header row), .json / .jsonl, or plain lines (letter per question).
    """
    path = path.resolve()
    if not path.is_file():
        raise SystemExit(f"Answer key not found: {path}")

    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".jsonl":
        out: Dict[int, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            idx_raw = o.get("index") or o.get("q") or o.get("question_id")
            if idx_raw is None:
                continue
            idx = int(idx_raw)
            let = _normalize_mcq_letter(str(o.get("answer") or o.get("letter") or ""))
            if let:
                out[idx] = let
        return out

    if suffix == ".json":
        data = json.loads(text)
        out: Dict[int, str] = {}
        if isinstance(data, list):
            for i, item in enumerate(data, start=1):
                if isinstance(item, dict):
                    idx = int(item.get("index", i))
                    let = _normalize_mcq_letter(str(item.get("answer") or item.get("letter") or ""))
                else:
                    idx = i
                    let = _normalize_mcq_letter(str(item))
                if let:
                    out[idx] = let
            return out
        if isinstance(data, dict):
            nested = data.get("answers")
            if isinstance(nested, dict):
                for k, v in nested.items():
                    let = _normalize_mcq_letter(str(v))
                    if let:
                        out[int(k)] = let
                if out:
                    return out
            skip = frozenset({"answers", "metadata", "title"})
            for k, v in data.items():
                kl = str(k).lower()
                if kl in skip:
                    continue
                if not str(k).lstrip("-").isdigit():
                    continue
                let = _normalize_mcq_letter(str(v))
                if let:
                    out[int(k)] = let
            return out
        raise SystemExit("answer-key JSON must be a list or object mapping index -> letter")

    if suffix == ".csv":
        out = {}
        rows = list(csv.DictReader(text.splitlines()))
        if not rows:
            return out
        headers = {h.strip().lower(): h for h in rows[0].keys() if h}
        idx_col = next(
            (headers[h] for h in headers if h in _INDEX_HEADER_ALIASES),
            None,
        )
        ans_col = next(
            (headers[h] for h in headers if h in _ANSWER_HEADER_ALIASES),
            None,
        )
        if not ans_col:
            raise SystemExit("answer-key CSV needs a column like answer, letter, or correct")
        if not idx_col:
            for i, row in enumerate(rows, start=1):
                let = _normalize_mcq_letter(str(row.get(ans_col, "")))
                if let:
                    out[i] = let
            return out
        for row in rows:
            raw_i = (row.get(idx_col) or "").strip()
            if not raw_i:
                continue
            try:
                idx = int(raw_i)
            except ValueError:
                continue
            let = _normalize_mcq_letter(str(row.get(ans_col, "")))
            if let:
                out[idx] = let
        return out

    # Plain lines: "B" or "1,B" per question
    out = {}
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "," in line:
            left, right = line.split(",", 1)
            try:
                idx = int(left.strip())
            except ValueError:
                idx = i
            let = _normalize_mcq_letter(right)
        else:
            idx = i
            let = _normalize_mcq_letter(line)
        if let:
            out[idx] = let
    return out


def _apply_answer_key(rows: List[Dict[str, Any]], key: Dict[int, str]) -> None:
    for r in rows:
        idx = int(r.get("index") or 0)
        gold = key.get(idx)
        r["answer_key_letter"] = gold
        final = _normalize_mcq_letter(str(r.get("final_predicted_option") or ""))
        graph = _normalize_mcq_letter(str(r.get("graph_predicted_option") or ""))
        llm = _normalize_mcq_letter(str(r.get("llm_predicted_option") or ""))
        if gold is None:
            r["matches_answer_key"] = None
            r["graph_matches_answer_key"] = None
            r["llm_matches_answer_key"] = None
        else:
            r["matches_answer_key"] = final == gold if final else False
            r["graph_matches_answer_key"] = graph == gold if graph else False
            r["llm_matches_answer_key"] = llm == gold if llm else False


def _grading_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    keyed = [r for r in rows if r.get("answer_key_letter")]
    if not keyed:
        return {"with_key": 0, "final_correct": 0, "graph_correct": 0, "llm_correct": 0}
    return {
        "with_key": len(keyed),
        "final_correct": sum(1 for r in keyed if r.get("matches_answer_key") is True),
        "graph_correct": sum(1 for r in keyed if r.get("graph_matches_answer_key") is True),
        "llm_correct": sum(1 for r in keyed if r.get("llm_matches_answer_key") is True),
    }


def extract_pdf_text(pdf_path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    parts: List[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text()
            if t:
                parts.append(t)
        except Exception:
            pass
    return "\n".join(parts)


def chunk_text(
    text: str,
    chunk_size: int = 2000,
    overlap: int = 250,
) -> List[Tuple[int, int, str]]:
    """Return (char_start, char_end, chunk) windows over the PDF text."""
    text = re.sub(r"\r\n?", "\n", text)
    chunks: List[Tuple[int, int, str]] = []
    n = len(text)
    if n == 0:
        return chunks
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append((start, end, text[start:end]))
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks


def _token_set(s: str) -> set:
    return {t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", s.lower())}


def select_book_chunks_by_graph(
    question: str,
    options: List[str],
    entities: List[str],
    triples: List[Tuple[str, str, str]],
    chunks: List[Tuple[int, int, str]],
    top_k: int = 3,
    max_chars: int = 6500,
) -> str:
    """
    Pick PDF chunks anchored to the GRAPH nodes retrieved for this question.

    Scoring: tokens from retrieved entities weigh most, triple endpoints next,
    and question/option tokens give a small tiebreaker boost. Chunks that
    overlap zero graph tokens are dropped even if they match the question.
    """
    entity_tok: set = set()
    for e in entities:
        entity_tok |= _token_set(e)
    triple_tok: set = set()
    for tri in triples:
        if len(tri) >= 3:
            triple_tok |= _token_set(tri[0])
            triple_tok |= _token_set(tri[2])
    q_tok = _token_set(question + " " + " ".join(options))

    if (not entity_tok and not triple_tok) or not chunks:
        return ""

    scored: List[Tuple[float, str]] = []
    for _a, _b, ch in chunks:
        ct = _token_set(ch)
        e_overlap = len(entity_tok & ct)
        t_overlap = len(triple_tok & ct)
        if e_overlap == 0 and t_overlap == 0:
            continue
        q_overlap = len(q_tok & ct)
        raw = 3.0 * e_overlap + 1.5 * t_overlap + 0.5 * q_overlap
        scored.append((raw / (1 + len(ct) ** 0.5), ch))

    scored.sort(key=lambda x: -x[0])
    out_parts: List[str] = []
    total = 0
    for _score, ch in scored[:top_k]:
        if total + len(ch) > max_chars:
            break
        out_parts.append(f"[PDF chunk]\n{ch.strip()}")
        total += len(ch)
    return "\n\n---\n\n".join(out_parts)


_OCR_OPTION_SPLIT = re.compile(
    r"(?:^|[\s\(])([a-dA-D])[\.\,;:\)]?\s+",
)


def _inline_options(text_after_q: str, max_chars: int = 1500) -> List[str]:
    """
    Parse A/B/C/D options from a chunk where options are inline on the same line
    (typical of OCR'd PDFs): ``a. foo b. bar c. baz d. qux``. Tolerates missing
    dots, lowercase letters, and noise tokens between options. Stops at the next
    question marker (``\\d+[\\. ]``).
    """
    chunk = text_after_q[:max_chars]
    # Cut at the next question stem if present
    cut = re.search(r"\n\s*\d+[\.\s]\s*[A-Z]", chunk)
    if cut:
        chunk = chunk[: cut.start()]

    # Split by letter markers; keep the letters in the result
    parts = _OCR_OPTION_SPLIT.split(chunk)
    if len(parts) < 3:
        return []
    options_map: Dict[str, str] = {}
    # parts: [pre, 'a', body_a, 'b', body_b, ...]
    for i in range(1, len(parts) - 1, 2):
        letter = parts[i].upper()
        body = parts[i + 1].strip()
        # Drop trailing junk: page numbers, copyright lines, very short tokens
        body = re.split(r"\s+\d+[\.\)]\s+[A-Za-z]", body, maxsplit=1)[0]
        body = re.split(r"\s+(?:Copyright|Page)\b", body, maxsplit=1, flags=re.I)[0]
        body = body.strip(" .,;:-")
        # Strip OCR noise: strings of stray digits / single chars
        body = re.sub(r"\s+\d+(?:\s+\d+)+\s*$", "", body)
        body = re.sub(r"\s{2,}", " ", body).strip()
        if 2 < len(body) < 300 and letter not in options_map:
            options_map[letter] = body

    out: List[str] = []
    for L in "ABCD":
        if L in options_map:
            out.append(f"{L}. {options_map[L]}")
    return out


def parse_mcq_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Find ``...?`` segments and extract A/B/C/D options.

    Two strategies (in order):
      1. Line-based: ``A./B./...`` on separate lines (typical of clean exports).
      2. Inline: options on the same line after the ``?`` (typical of OCR output).
    """
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    question_pattern = r"([^\n!?]*\?)"
    items: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for match in re.finditer(question_pattern, text):
        segment = match.group(1).strip()
        segment = re.sub(r"\s+", " ", segment)
        if len(segment) < 25 or len(segment) > 900:
            continue
        segment = re.sub(r"^\d+[\.\)\s]\s*", "", segment)
        segment = re.sub(r"^[Qq]uestion\s+\d+[\.\)]?\s*", "", segment, flags=re.IGNORECASE)
        if not segment.endswith("?"):
            continue
        if re.search(r"https?://", segment.lower()) or "www." in segment.lower():
            continue

        following = text[match.end() : match.end() + 1500]

        # Strategy 1: line-based options
        options: List[str] = []
        for line in following.split("\n")[:24]:
            line = line.strip()
            if not line:
                if options:
                    break
                continue
            om = re.match(r"^([A-D])[\.\)]\s*(.+)$", line, re.IGNORECASE)
            if om:
                letter = om.group(1).upper()
                body = om.group(2).strip()
                if 2 < len(body) < 400:
                    options.append(f"{letter}. {body}")
            elif options and len(line) > 5 and not re.match(r"^[A-D][\.\)]", line, re.I):
                break

        # Strategy 2: inline options (same line after ?)
        if len(options) < 2:
            options = _inline_options(following)

        key = re.sub(r"\W+", " ", segment.lower())[:100]
        if key in seen:
            continue
        seen.add(key)

        items.append(
            {
                "question": segment,
                "options": options,
                "has_four": len(options) >= 4,
            }
        )

    with4 = [x for x in items if x["has_four"]]
    rest = [x for x in items if not x["has_four"]]
    ordered = with4 + rest
    for x in ordered:
        del x["has_four"]
    return ordered


def run_pipeline(
    source: Path,
    *,
    from_text: bool = False,
    limit: int = 10,
    dry_parse: bool = False,
    certain: bool = True,
    chunk_size: int = 2000,
    chunk_overlap: int = 250,
) -> List[Dict[str, Any]]:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from graphrag_complete import GraphRAGComplete

    if from_text:
        raw = source.read_text(encoding="utf-8", errors="replace")
    else:
        raw = extract_pdf_text(source)
    if len(raw) < 200:
        raise SystemExit(f"Very little text from {source}. For PDFs: scanned pages need OCR.")

    parsed = parse_mcq_from_text(raw)
    if dry_parse:
        print(f"Parsed {len(parsed)} question blocks (with any options). Showing first 3:")
        for p in parsed[:3]:
            print("---")
            print(p["question"][:200], "...")
            print("options:", len(p["options"]), p["options"][:4])
        return []

    mcq_only = [p for p in parsed if len(p.get("options") or []) >= 2]
    if not mcq_only:
        raise SystemExit(
            "No items with at least 2 options found. PDF layout may differ; try another export or OCR."
        )

    chunks = chunk_text(raw, chunk_size=chunk_size, overlap=chunk_overlap)
    pipe = GraphRAGComplete(prefer_neo4j=False, use_semantic_entities=None)
    results: List[Dict[str, Any]] = []
    try:
        for i, item in enumerate(mcq_only[:limit]):
            q = item["question"]
            opts = item["options"]

            # Phase 1: retrieve subgraph (logic) — entities + triples + paths
            ctx, evidence, meta = pipe.rag.collect_graph_context(q)
            meta["backend"] = "networkx"
            meta["traversal"] = "networkx"

            # Phase 2: pick book chunks anchored to the retrieved graph nodes
            ranked_entities = [n for n, _s in (meta.get("ranked_entities") or [])][:10]
            retrieved_triples: List[Tuple[str, str, str]] = []
            for t in (meta.get("traversal_traces") or []):
                for tri in (t.get("one_hop_triples") or []) + (t.get("two_hop_triples") or []):
                    if isinstance(tri, (list, tuple)) and len(tri) >= 3:
                        retrieved_triples.append((str(tri[0]), str(tri[1]), str(tri[2])))
            doc_ctx = select_book_chunks_by_graph(
                q, opts, ranked_entities, retrieved_triples, chunks, top_k=3, max_chars=7000
            )

            # Phase 3: Ollama — graph (logic) + entity-anchored book passages (content)
            out = pipe.rag.answer_from_context(
                q, opts, ctx, evidence, meta,
                certain=certain,
                document_context=doc_ctx or None,
            )
            if not out.get("final_predicted_option"):
                fallback = out.get("llm_predicted_option") or out.get("graph_predicted_option")
                if fallback:
                    out["final_predicted_option"] = fallback
                    out["consensus"] = f"{out.get('consensus') or 'none'}+fallback"
            row = {
                "index": i + 1,
                "question": q,
                "options": opts,
                "pdf_chunk_chars": len(doc_ctx),
                "traversal": (out.get("retrieval") or {}).get("traversal"),
                "backend": (out.get("retrieval") or {}).get("backend"),
                "final_predicted_option": out.get("final_predicted_option"),
                "graph_predicted_option": out.get("graph_predicted_option"),
                "llm_predicted_option": out.get("llm_predicted_option"),
                "certainty_score": out.get("certainty_score"),
                "retrieval_confidence": out.get("retrieval_confidence"),
                "consensus": out.get("consensus"),
                "answer": out.get("answer"),
                "error": out.get("error"),
                "graph_path_lines": out.get("graph_path_lines") or [],
                "traversal_traces": out.get("traversal_traces") or [],
                "inter_entity_paths": out.get("inter_entity_paths") or [],
                "selected_option_text": _option_text_for_letter(
                    out.get("final_predicted_option"), opts
                ),
            }
            results.append(row)
            print(f"[{i+1}/{min(limit, len(mcq_only))}] final={row['final_predicted_option']} "
                  f"certainty={row['certainty_score']} consensus={row['consensus']}")
    finally:
        pipe.close()
    return results


def _option_text_for_letter(letter: Optional[str], options: List[str]) -> str:
    if not letter or not options:
        return ""
    L = letter.strip().upper()[:1]
    if not L.isalpha():
        return ""
    for o in options:
        s = o.strip()
        if not s:
            continue
        if s[0].upper() == L and len(s) > 1 and s[1] in ".): ":
            return o
        if s.upper().startswith(L + "."):
            return o
    return ""


def write_answers_markdown(
    rows: List[Dict[str, Any]],
    out_path: Path,
    *,
    image_dir_rel: Optional[str] = None,
) -> None:
    """
    Single Markdown file: per question, Q + options + chosen option + reasoning.
    If image_dir_rel is given, embed a reference to the per-question KG trace PNG.
    """
    lines: List[str] = []
    lines.append("# CISSP GraphRAG — answers and reasoning")
    lines.append("")
    lines.append(
        "Per question: the question, the option Ollama chose (logic from the graph, "
        "wording from the book), and the full reasoning. If trace images were rendered, "
        "each question links to its KG visualization."
    )
    lines.append("")

    stats = _grading_summary(rows)
    if stats["with_key"] > 0:
        n = stats["with_key"]
        lines.append(
            f"**Grading:** final {stats['final_correct']}/{n}  "
            f"| graph {stats['graph_correct']}/{n}  "
            f"| llm {stats['llm_correct']}/{n}"
        )
        lines.append("")

    for r in rows:
        idx = r.get("index", 0)
        chosen = str(r.get("final_predicted_option") or "—")
        sel_text = re.sub(r"^[A-D][\.\)]\s*", "", str(r.get("selected_option_text") or "").strip())

        lines.append(f"## Q{idx}. {r.get('question','')}")
        lines.append("")
        for o in (r.get("options") or []):
            lines.append(f"- {o}")
        lines.append("")

        answer_line = f"**Answer: {chosen}**"
        if sel_text:
            answer_line += f" — {sel_text}"
        lines.append(answer_line)

        gold = r.get("answer_key_letter")
        if gold:
            match = r.get("matches_answer_key")
            status = "correct" if match is True else (
                "incorrect" if match is False else "no prediction"
            )
            lines.append(f"**Gold:** {gold} ({status})")

        lines.append(
            f"`graph={r.get('graph_predicted_option') or '—'}` "
            f"`llm={r.get('llm_predicted_option') or '—'}` "
            f"`certainty={r.get('certainty_score')}` "
            f"`consensus={r.get('consensus') or '—'}`"
        )
        lines.append("")
        if r.get("error"):
            lines.append(f"**Error:** {r['error']}")
            lines.append("")

        lines.append("**Reasoning:**")
        lines.append("")
        lines.append("```")
        lines.append(r.get("answer") or "—")
        lines.append("```")
        lines.append("")

        # Text-form trace: which nodes were actually used to pick this answer
        try:
            trace = _compute_answer_trace(r)
        except Exception:
            trace = None
        if trace and (trace["seeds"] or trace["answer_nodes"]):
            lines.append("**Nodes traced to answer:**")
            lines.append("")
            connected = sorted(trace["connected_seeds"])
            isolated = sorted(s for s in trace["seeds"] if s not in trace["connected_seeds"])
            if trace["answer_nodes"]:
                lines.append(f"- **Answer-supporting nodes:** {', '.join(sorted(trace['answer_nodes']))}")
            if connected:
                lines.append(f"- **Seeds on the answer path:** {', '.join(connected)}")
            if isolated:
                lines.append(f"- **Other anchors (no short path to answer):** {', '.join(isolated)}")
            if trace["path_examples"]:
                lines.append("- **Paths traced (seed → … → answer):**")
                seen_paths: set = set()
                for path in trace["path_examples"][:8]:
                    key = tuple(path)
                    if key in seen_paths:
                        continue
                    seen_paths.add(key)
                    lines.append(f"    - {' → '.join(path)}")
            lines.append("")

        if image_dir_rel:
            img = f"{image_dir_rel.rstrip('/')}/q{idx:03d}_trace.png"
            lines.append("**Knowledge graph trace (visualization):**")
            lines.append("")
            lines.append(f"![Q{idx} trace]({img})")
            lines.append("")

        lines.append("---")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _compute_answer_trace(row: Dict[str, Any], *, max_path_len: int = 3) -> Dict[str, Any]:
    """
    Compute the nodes/edges that led to the chosen option for one result row.
    Returns: full graph (G), seeds, answer-supporting nodes, edge relations,
    bold path edges (seed→answer shortest paths), and example node sequences.
    """
    import networkx as nx

    chosen_text_raw = str(row.get("selected_option_text") or "")
    chosen_text = re.sub(r"^[A-D][\.\)]\s*", "", chosen_text_raw).strip()
    chosen_lower = chosen_text.lower()

    G = nx.DiGraph()
    seeds: set = set()
    edge_rel: Dict[Tuple[str, str], str] = {}
    for t in (row.get("traversal_traces") or []):
        seed = t.get("seed_entity")
        if seed:
            seeds.add(seed)
            G.add_node(seed)
        for tri in (t.get("one_hop_triples") or []) + (t.get("two_hop_triples") or []):
            if not isinstance(tri, (list, tuple)) or len(tri) < 3:
                continue
            s, rel, o = str(tri[0]), str(tri[1]), str(tri[2])
            G.add_edge(s, o)
            edge_rel.setdefault((s, o), str(rel).replace("_", " "))

    answer_nodes: set = set()
    if chosen_lower:
        for n in G.nodes():
            nl = str(n).lower().strip()
            if len(nl) >= 3 and nl in chosen_lower:
                answer_nodes.add(n)
        if not answer_nodes:
            chosen_tok = _token_set(chosen_lower)
            for n in G.nodes():
                if chosen_tok & _token_set(n):
                    answer_nodes.add(n)

    connected_seeds: set = set()
    path_edges: set = set()
    path_examples: List[List[str]] = []
    G_undir = G.to_undirected(as_view=True)
    for s in sorted(seeds):
        for a in sorted(answer_nodes):
            if s == a or not G_undir.has_node(s) or not G_undir.has_node(a):
                continue
            try:
                path = nx.shortest_path(G_undir, s, a)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
            if len(path) - 1 > max_path_len:
                continue
            connected_seeds.add(s)
            path_examples.append(path)
            for u, v in zip(path[:-1], path[1:]):
                if G.has_edge(u, v):
                    path_edges.add((u, v))
                if G.has_edge(v, u):
                    path_edges.add((v, u))

    return {
        "graph": G,
        "seeds": seeds,
        "connected_seeds": connected_seeds,
        "answer_nodes": answer_nodes,
        "edge_rel": edge_rel,
        "path_edges": path_edges,
        "path_examples": path_examples,
        "chosen_text": chosen_text,
    }


def render_trace_images(
    rows: List[Dict[str, Any]],
    out_dir: Path,
    *,
    max_nodes: int = 25,
    max_path_len: int = 3,
) -> List[Path]:
    """
    One PNG per question showing the KG path GraphRAG actually used to pick the
    chosen option. Uses the same rule as EnhancedQueryEngine.generate_answer:
    an entity is "answer-supporting" if its name appears in the chosen option's
    text (case-insensitive substring match, with a token-overlap fallback).

    Colors:
      - Red    = seed (retrieval anchor)
      - Green  = answer-supporting node (matches the chosen option)
      - Orange = intermediate node on a seed→answer-supporting path
    Edges on any seed→answer-supporting shortest path are drawn bold/dark;
    other context edges are light. Triples unrelated to the chosen option
    are dropped so the viz shows only the trace that led to the answer.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError as e:
        raise SystemExit(
            "matplotlib and networkx are required. pip install matplotlib networkx"
        ) from e

    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    for r in rows:
        idx = r.get("index", 0)
        chosen = r.get("final_predicted_option") or "?"
        q_full = r.get("question") or ""
        q_short = (q_full[:110] + "…") if len(q_full) > 110 else q_full

        trace = _compute_answer_trace(r, max_path_len=max_path_len)
        G_full = trace["graph"]
        seeds = trace["seeds"]
        connected_seeds = trace["connected_seeds"]
        answer_nodes = trace["answer_nodes"]
        edge_rel = trace["edge_rel"]
        path_edges = trace["path_edges"]
        chosen_text = trace["chosen_text"]

        if len(G_full.nodes()) == 0:
            continue

        if path_edges:
            # Show only nodes that lie on a seed→answer path (the actual trace)
            path_nodes: set = set()
            for u, v in path_edges:
                path_nodes.add(u)
                path_nodes.add(v)
            focus_nodes = path_nodes | answer_nodes
        else:
            # No connecting path — fall back to seeds + immediate neighborhood
            focus_nodes = set(seeds) | answer_nodes
            for n in list(seeds):
                for succ in list(G_full.successors(n))[:4]:
                    focus_nodes.add(succ)
                for pred in list(G_full.predecessors(n))[:4]:
                    focus_nodes.add(pred)

        G = G_full.subgraph(focus_nodes).copy()

        # Cap for readability — always keep seeds + answer nodes
        if len(G.nodes()) > max_nodes:
            must_keep = set(seeds) | set(answer_nodes)
            deg = dict(G.degree())
            extras = [n for n in sorted(deg, key=lambda x: -deg[x]) if n not in must_keep]
            keep = must_keep | set(extras[: max(0, max_nodes - len(must_keep))])
            G = G.subgraph(keep).copy()

        if len(G.nodes()) == 0:
            continue

        pos = nx.spring_layout(G, seed=42, k=1.1, iterations=80)

        node_colors = []
        for n in G.nodes():
            if n in seeds and n in answer_nodes:
                node_colors.append("#9467bd")  # purple — seed that also supports answer
            elif n in seeds:
                node_colors.append("#d62728")  # red — seed
            elif n in answer_nodes:
                node_colors.append("#2ca02c")  # green — answer-supporting
            else:
                node_colors.append("#ff7f0e")  # orange — intermediate

        edge_colors: List[str] = []
        edge_widths: List[float] = []
        for e in G.edges():
            if e in path_edges:
                edge_colors.append("#111111")
                edge_widths.append(2.2)
            else:
                edge_colors.append("#bbbbbb")
                edge_widths.append(1.0)

        fig_w = min(14, max(9, len(G.nodes()) * 0.55))
        fig_h = min(10, max(6, len(G.nodes()) * 0.42))
        plt.figure(figsize=(fig_w, fig_h))
        nx.draw_networkx_nodes(
            G, pos, node_color=node_colors, node_size=1200,
            edgecolors="black", linewidths=0.6,
        )
        nx.draw_networkx_labels(G, pos, font_size=9, font_weight="bold")
        nx.draw_networkx_edges(
            G, pos, edge_color=edge_colors, arrows=True, arrowsize=14,
            width=edge_widths, connectionstyle="arc3,rad=0.08",
        )
        labels = {e: edge_rel[e] for e in G.edges() if e in edge_rel}
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels=labels, font_size=7, alpha=0.9,
        )

        title = (
            f"Q{idx} — Chosen: {chosen}" + (f" ({chosen_text})" if chosen_text else "")
            + f"\n{q_short}\nRed=seed · Green=supports chosen option · Orange=intermediate · bold edge=seed→answer path"
        )
        plt.title(title, fontsize=9)
        plt.axis("off")
        plt.tight_layout()

        p = out_dir / f"q{idx:03d}_trace.png"
        plt.savefig(str(p), dpi=150, bbox_inches="tight")
        plt.close()
        written.append(p)

    return written


def main() -> None:
    ap = argparse.ArgumentParser(description="CISSP PDF + NetworkX GraphRAG + Ollama")
    ap.add_argument("--pdf", type=str, default=None, help="Path to CISSP exam PDF")
    ap.add_argument("--text-file", type=str, default=None, help="Plain-text export of the exam (same parser as PDF)")
    ap.add_argument("--limit", type=int, default=5, help="Max MCQ items to run (default 5; use 250 for full)")
    ap.add_argument("--dry-parse", action="store_true", help="Only parse PDF and print sample; no Ollama")
    ap.add_argument("--no-certain", action="store_true", help="Disable certainty merge in GraphRAG")
    ap.add_argument("--out", type=str, default=None, help="Write JSONL results to this path")
    ap.add_argument(
        "--md",
        type=str,
        default=None,
        help="Write a single Markdown file (Q + chosen option + reasoning) to this path",
    )
    ap.add_argument(
        "--trace-images",
        dest="trace_images",
        type=str,
        default=None,
        help="Directory to render per-question KG trace visualizations (PNG per question)",
    )
    ap.add_argument(
        "--answer-key",
        type=str,
        default=None,
        help="CSV, JSON, JSONL, or plain-lines file mapping 1-based question index to A–D",
    )
    ap.add_argument("--chunk-size", type=int, default=2000)
    ap.add_argument("--chunk-overlap", type=int, default=250)
    args = ap.parse_args()

    if args.text_file and args.pdf:
        print("Use only one of --pdf or --text-file", file=sys.stderr)
        sys.exit(2)

    if args.text_file:
        src = Path(args.text_file)
        if not src.is_absolute():
            src = PROJECT_ROOT / src
        from_text = True
    else:
        src = Path(args.pdf) if args.pdf else DEFAULT_PDF
        if not src.is_absolute():
            src = PROJECT_ROOT / src
        from_text = False

    if not src.exists():
        print(
            f"Input not found: {src}\n"
            f"  --pdf data/qa/CISSP_Final_250.pdf   OR   --text-file path/to/exam.txt\n"
            f"Example: python src/cissp250_graphrag.py --pdf \"%USERPROFILE%\\Downloads\\CISSP250.pdf\" --limit 3",
            file=sys.stderr,
        )
        sys.exit(1)

    rows = run_pipeline(
        src,
        from_text=from_text,
        limit=args.limit,
        dry_parse=args.dry_parse,
        certain=not args.no_certain,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    if args.answer_key and rows:
        kp = Path(args.answer_key)
        if not kp.is_absolute():
            kp = PROJECT_ROOT / kp
        _apply_answer_key(rows, load_answer_key(kp))
        st = _grading_summary(rows)
        if st["with_key"]:
            n = st["with_key"]
            print(
                f"Answer key ({n} labels): final {st['final_correct']}/{n} | "
                f"graph {st['graph_correct']}/{n} | llm {st['llm_correct']}/{n}"
            )

    if args.out and rows:
        outp = Path(args.out)
        if not outp.is_absolute():
            outp = PROJECT_ROOT / outp
        outp.parent.mkdir(parents=True, exist_ok=True)
        with open(outp, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Wrote {len(rows)} rows -> {outp}")

    trace_rel: Optional[str] = None
    if args.trace_images and rows:
        tp = Path(args.trace_images)
        if not tp.is_absolute():
            tp = PROJECT_ROOT / tp
        images = render_trace_images(rows, tp)
        print(f"Wrote {len(images)} trace images -> {tp}")
        if args.md:
            mdp_preview = Path(args.md)
            if not mdp_preview.is_absolute():
                mdp_preview = PROJECT_ROOT / mdp_preview
            try:
                trace_rel = os.path.relpath(tp, mdp_preview.parent).replace(os.sep, "/")
            except ValueError:
                trace_rel = str(tp)

    if args.md and rows:
        mdp = Path(args.md)
        if not mdp.is_absolute():
            mdp = PROJECT_ROOT / mdp
        write_answers_markdown(rows, mdp, image_dir_rel=trace_rel)
        print(f"Wrote answers markdown -> {mdp}")


if __name__ == "__main__":
    main()
