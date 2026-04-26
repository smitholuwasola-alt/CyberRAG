"""
Complete GraphRAG pipeline — **NetworkX** graph traversal by default, optional Neo4j, Ollama + certainty.

Flow
----
1. Build in-memory KG (``KnowledgeGraphBuilder`` / **NetworkX** ``MultiDiGraph``) from ``data/knowledge_graph/*.csv``.
2. **Default:** subgraph context via ``GraphRAGOllama.collect_graph_context`` → ``EnhancedQueryEngine``
   (entity match, multi-hop over ``kg.triples`` / triple index).
3. **Optional** (``--neo4j``): if Neo4j is reachable, retrieve with Cypher first; if empty, fall back to NetworkX.
4. Optionally attach a **PDF excerpt** as document context; structured answers still follow graph facts.
5. ``GraphRAGOllama.answer_from_context`` → Ollama + graph/LLM consensus + ``certainty_score``.

Environment
-----------
  OLLAMA_HOST, OLLAMA_MODEL — Ollama HTTP API
  NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD — only when using ``--neo4j``

Examples
--------
  python src/graphrag_complete.py "What is Snort used for?"
  python src/graphrag_complete.py --neo4j "Same question but Neo4j retrieval if DB is up"
  python src/graphrag_complete.py --pdf path/to/exam.pdf "Question text from the PDF"
  python src/graphrag_complete.py --json "Question"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from graphrag_ollama import GraphRAGOllama
from kg_builder import KnowledgeGraphBuilder
from neo4j_graph_retriever import Neo4jGraphRetriever


def extract_pdf_text(pdf_path: Path, max_chars: int = 12000) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise SystemExit("pip install pypdf to use --pdf") from e
    reader = PdfReader(str(pdf_path))
    parts: List[str] = []
    for page in reader.pages[:40]:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            pass
    body = "\n\n".join(parts).strip()
    return body[:max_chars]


class GraphRAGComplete:
    """
    End-to-end GraphRAG: **NetworkX** traversal by default; Neo4j only when ``prefer_neo4j=True``.
    """

    def __init__(
        self,
        *,
        prefer_neo4j: bool = False,
        ollama_base: Optional[str] = None,
        ollama_model: Optional[str] = None,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        use_semantic_entities: Optional[bool] = None,
    ):
        self.kg = KnowledgeGraphBuilder()
        self.kg.build_graph()
        self.rag = GraphRAGOllama(
            kg_builder=self.kg,
            ollama_base=ollama_base,
            model=ollama_model,
            use_semantic_entities=use_semantic_entities,
        )
        self.neo: Optional[Neo4jGraphRetriever] = None
        if prefer_neo4j:
            self.neo = Neo4jGraphRetriever(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
            if not self.neo.ok:
                self.neo.close()
                self.neo = None

    def close(self) -> None:
        if self.neo:
            self.neo.close()

    def answer(
        self,
        question: str,
        options: Optional[List[str]] = None,
        *,
        certain: bool = True,
        force_networkx: bool = False,
        document_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        kas = self.rag.retriever.identify_cybok_kas(question)
        intents = set(self.rag.retriever.extract_relation_intent(question))

        meta: Dict[str, Any]
        ctx: str
        evidence: List[str]

        # Default path: subgraph via NetworkX (KnowledgeGraphBuilder + EnhancedQueryEngine).
        use_neo = self.neo is not None and not force_networkx
        if use_neo:
            neo = self.neo
            ctx, evidence, meta = neo.retrieve(
                question,
                relation_intents=intents,
                relevant_kas=kas,
            )
            if meta.get("triple_count", 0) < 1:
                ctx, evidence, meta = self.rag.collect_graph_context(question)
                meta["backend"] = "networkx_fallback_neo4j_empty"
                meta["traversal"] = "networkx"
        else:
            ctx, evidence, meta = self.rag.collect_graph_context(question)
            meta["backend"] = "networkx"
            meta["traversal"] = "networkx"

        if "relevant_kas" not in meta or not meta["relevant_kas"]:
            meta["relevant_kas"] = [k[0] for k in kas][:3]

        out = self.rag.answer_from_context(
            question,
            options,
            ctx,
            evidence,
            meta,
            certain=certain,
            document_context=document_context,
        )
        return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Complete GraphRAG: NetworkX traversal (default), optional Neo4j, Ollama + certainty."
    )
    parser.add_argument("question", nargs="?", help="Question (or text from a PDF quiz)")
    parser.add_argument("--options", nargs="*", help="Multiple-choice lines e.g. 'A. foo' 'B. bar'")
    parser.add_argument("--pdf", type=str, default=None, help="Optional PDF path; first pages extracted as context")
    parser.add_argument(
        "--neo4j",
        action="store_true",
        help="Use Neo4j for retrieval when connected (default is NetworkX only)",
    )
    parser.add_argument(
        "--force-networkx",
        action="store_true",
        help="For this run only, use NetworkX even if the pipeline was built with Neo4j",
    )
    parser.add_argument("--no-certain", action="store_true", help="Disable certainty merge (legacy)")
    parser.add_argument("--no-semantic", action="store_true", help="Disable SBERT in NetworkX ranking when used")
    parser.add_argument("--model", default=None, help="Ollama model")
    parser.add_argument("--ollama-host", default=None, help="Ollama base URL")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    if not args.question:
        args.question = "What is Snort used for in network security?"

    src = str(PROJECT_ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    doc = None
    if args.pdf:
        p = Path(args.pdf)
        if not p.is_absolute():
            p = PROJECT_ROOT / args.pdf
        if not p.exists():
            print(f"PDF not found: {p}", file=sys.stderr)
            sys.exit(1)
        doc = extract_pdf_text(p)

    pipe = GraphRAGComplete(
        prefer_neo4j=args.neo4j,
        ollama_base=args.ollama_host,
        ollama_model=args.model,
        use_semantic_entities=not args.no_semantic,
    )
    try:
        result = pipe.answer(
            args.question,
            options=args.options or None,
            certain=not args.no_certain,
            force_networkx=args.force_networkx,
            document_context=doc,
        )
    finally:
        pipe.close()

    if args.json:
        out = {k: v for k, v in result.items() if k != "graph_context"}
        out["graph_context"] = (result.get("graph_context") or "")[:2500]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    if result.get("error"):
        print("Error:", result["error"])
        print("\nBackend / retrieval:", result.get("retrieval", {}).get("backend"))
        print("\nGraph context (truncated):\n", (result.get("graph_context") or "")[:1500])
        print("\nEnsure Ollama is running: https://ollama.com")
        if result.get("retrieval", {}).get("backend", "").startswith("neo4j"):
            print("For Neo4j: start DB and run python src/neo4j/neo4j_integration.py …")
        return

    print(result.get("answer", ""))
    print(
        "\n=== Certainty & backend ===\n"
        f"backend={result.get('retrieval', {}).get('backend', '?')}  "
        f"retrieval_confidence={result.get('retrieval_confidence')}  "
        f"certainty_score={result.get('certainty_score')}  consensus={result.get('consensus')}\n"
        f"final_option={result.get('final_predicted_option')}  "
        f"(graph={result.get('graph_predicted_option')}  llm={result.get('llm_predicted_option')}  "
        f"margin={result.get('graph_option_margin')})"
    )


if __name__ == "__main__":
    main()
