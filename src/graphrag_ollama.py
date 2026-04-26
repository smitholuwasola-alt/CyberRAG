"""
GraphRAG + Ollama — graph-first retrieval, optional dense entity matching, LLM synthesis.

1. Rank entities: lexical scores from EnhancedQueryEngine + optional SBERT similarity
   (entity name + description vs question) to extend matching beyond exact string hits.
2. Collect multi-hop triples around top entities (same relation-intent cues as enhanced engine).
3. Call Ollama (/api/chat) with a strict system prompt: answer only from the supplied graph facts.

Requires Ollama running locally (or set OLLAMA_HOST). Default model: OLLAMA_MODEL or llama3.2.

Usage (from repo root, with src on PYTHONPATH or run as script):
  python src/graphrag_ollama.py "What is Snort used for?"
  python src/graphrag_ollama.py --no-semantic "Explain TLS and certificates"
  python src/graphrag_ollama.py --no-certain "Legacy: LLM choice only"

By default ``answer(..., certain=True)`` merges graph MCQ scores with the LLM and
exposes ``retrieval_confidence``, ``certainty_score``, and ``consensus`` for the
most grounded multiple-choice output.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    import requests
except ImportError:
    requests = None  # type: ignore

# Avoid importing sentence_transformers (and TF/torch) unless semantic ranking is used
_HAS_ST = importlib.util.find_spec("sentence_transformers") is not None

from enhanced_query_engine import EnhancedQueryEngine
from kg_builder import KnowledgeGraphBuilder

SYSTEM_PROMPT = """You are a cybersecurity tutor answering with two distinct sources:

1. KNOWLEDGE GRAPH (logic) — structured triples (subject — relation — object) and traversed paths. Drives which option is correct and the reasoning about entities and relationships.
2. BOOK PASSAGES (content) — excerpts from the source textbook/exam document. Supplies definitions, wording, and supporting explanation text.

Rules:
- Decide CHOICE using the KNOWLEDGE GRAPH only. If the graph does not support any option, end with: CHOICE: NONE
- Use BOOK PASSAGES to flesh out the explanation, but do not let them introduce tools, standards, or relationships that are not in the graph. If the book and graph conflict on entities/relations, the graph wins.
- Be concise and precise.
- Structure your response exactly like this:
  LOGIC (graph): <1–3 sentences citing the specific triples/paths that point to the chosen option>
  EXPLANATION (book): <1–3 sentences of book-grounded supporting content; write "(no relevant passage)" if none>
  CHOICE: X
  where X is A, B, C, D, or NONE.
"""

SYSTEM_PROMPT_CERTAIN = SYSTEM_PROMPT + """
- If a GRAPH-ANCHORED HINT line is present, treat it as the retrieval system's best grounded letter; your CHOICE must match it unless a specific cited triple explicitly contradicts it (note the override in the LOGIC line).
- Add a final line after CHOICE: CERTAINTY: high | medium | low — based only on how directly the graph supports your CHOICE.
"""


class GraphRAGOllama:
    def __init__(
        self,
        kg_builder: Optional[KnowledgeGraphBuilder] = None,
        ollama_base: Optional[str] = None,
        model: Optional[str] = None,
        use_semantic_entities: Optional[bool] = None,
        sbert_model: str = "all-MiniLM-L6-v2",
    ):
        self.ollama_base = (ollama_base or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2")
        self.sbert_model_name = sbert_model
        if use_semantic_entities is None:
            use_semantic_entities = _HAS_ST
        self.use_semantic = bool(use_semantic_entities and _HAS_ST)
        self._st_model: Any = None
        self._st_matrix = None
        self._st_names: List[str] = []

        if kg_builder is None:
            kg_builder = KnowledgeGraphBuilder()
            kg_builder.build_graph()
        self.kg = kg_builder
        self.retriever = EnhancedQueryEngine(kg_builder)

    def _ensure_semantic_index(self) -> None:
        if not self.use_semantic or self._st_model is not None:
            return
        from sentence_transformers import SentenceTransformer

        import numpy as np

        self._st_model = SentenceTransformer(self.sbert_model_name)
        texts: List[str] = []
        names: List[str] = []
        seen: set[str] = set()
        for node in self.kg.graph.nodes():
            key = node.lower()
            if key in seen:
                continue
            seen.add(key)
            info = self.kg.get_entity_info(node) or {}
            desc = str(info.get("description", "") or "")[:400]
            texts.append(f"{node}. {desc}")
            names.append(node)

        emb = self._st_model.encode(
            texts, batch_size=64, show_progress_bar=False, convert_to_numpy=True
        )
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._st_matrix = emb / norms
        self._st_names = names

    def semantic_entity_scores(self, question: str, top_k: int = 35) -> Dict[str, float]:
        if not self.use_semantic:
            return {}
        import numpy as np

        self._ensure_semantic_index()
        if self._st_model is None or self._st_matrix is None:
            return {}
        q = self._st_model.encode([question], convert_to_numpy=True)[0]
        q = q / (np.linalg.norm(q) + 1e-9)
        sims = self._st_matrix @ q
        idx = np.argsort(-sims)[:top_k]
        return {self._st_names[int(i)]: float(sims[i]) for i in idx}

    def merged_entity_ranking(self, question: str) -> List[Tuple[str, float]]:
        """Lexical + optional dense similarity."""
        lex = self.retriever.find_relevant_entities(question)
        scores: Dict[str, float] = {n: float(s) for n, s in lex}
        for n, sim in self.semantic_entity_scores(question).items():
            scores[n] = scores.get(n, 0.0) + sim * 14.0
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return ranked[:25]

    def collect_graph_context(
        self,
        question: str,
        top_entities: int = 8,
        max_triples: int = 45,
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Retrieve subgraph text for RAG using **NetworkX** (via ``self.kg.graph`` / ``self.kg.triples``):
        ``EnhancedQueryEngine.multi_hop_query`` walks the in-memory graph built by ``KnowledgeGraphBuilder``.
        """
        relevant_kas = self.retriever.identify_cybok_kas(question)
        relation_intents = set(self.retriever.extract_relation_intent(question))
        ranked = self.merged_entity_ranking(question)

        all_triples: List[Tuple[str, str, str]] = []
        traversal_traces: List[Dict[str, Any]] = []
        path_line_set: set[str] = set()
        path_lines_ordered: List[str] = []

        def _add_path_line(s: str) -> None:
            if s not in path_line_set:
                path_line_set.add(s)
                path_lines_ordered.append(s)

        for ename, escore in ranked[:top_entities]:
            hop = self.retriever.multi_hop_query(ename, max_hops=2)
            one_h = [list(t) for t in hop["direct_relations"][:18]]
            two_h = [list(t) for t in hop["two_hop_relations"][:10]]
            traversal_traces.append(
                {
                    "seed_entity": ename,
                    "seed_score": round(float(escore), 3),
                    "one_hop_triples": one_h,
                    "two_hop_triples": two_h,
                }
            )
            for t in hop["direct_relations"]:
                all_triples.append(t)
            for t in hop["two_hop_relations"][:6]:
                all_triples.append(t)
            for t in one_h + two_h:
                if len(t) >= 3:
                    r_disp = str(t[1]).replace("_", " ")
                    _add_path_line(f"{t[0]} —[{r_disp}]→ {t[2]}")

        seen = set()
        unique: List[Tuple[str, str, str]] = []
        for t in all_triples:
            k = (t[0].lower(), t[1], t[2].lower())
            if k not in seen:
                seen.add(k)
                unique.append(t)
        if relation_intents:
            unique.sort(
                key=lambda tr: (0 if tr[1] in relation_intents else 1, -len(tr[0]) - len(tr[2]))
            )
        unique = unique[:max_triples]

        tops = [e[0] for e in ranked[: min(4, len(ranked))]]
        inter_paths: List[Dict[str, Any]] = []
        for i in range(len(tops)):
            for j in range(i + 1, len(tops)):
                try:
                    raw_paths = self.kg.get_path_between_entities(tops[i], tops[j], max_length=3)
                except Exception:
                    raw_paths = []
                for pseq in raw_paths[:2]:
                    if not pseq:
                        continue
                    inter_paths.append(
                        {"from_entity": tops[i], "to_entity": tops[j], "node_sequence": list(pseq)}
                    )
                    _add_path_line(" → ".join(pseq))

        lines: List[str] = []
        if relevant_kas:
            lines.append("Relevant CyBOK knowledge areas (hint): " + ", ".join(k[0] for k in relevant_kas[:3]))
        lines.append("Top entities (ranked): " + ", ".join(f"{n} ({s:.2f})" for n, s in ranked[:12]))
        lines.append("Triples (subject — relation — object):")
        for e1, r, e2 in unique:
            lines.append(f"  - {e1} — {r.replace('_', ' ')} — {e2}")
        if path_lines_ordered:
            lines.append("Distinct traversed paths (edges / node chains):")
            for pl in path_lines_ordered[:35]:
                lines.append(f"  · {pl}")

        ctx = "\n".join(lines)
        evidence = [f"{a} {r} {b}" for a, r, b in unique[:15]]
        meta = {
            "relevant_kas": [k[0] for k in relevant_kas],
            "ranked_entities": ranked[:15],
            "triple_count": len(unique),
            "relation_intents": sorted(relation_intents),
            "top_entity_score": float(ranked[0][1]) if ranked else 0.0,
            "traversal": "networkx",
            "traversal_traces": traversal_traces,
            "inter_entity_paths": inter_paths,
            "path_lines": path_lines_ordered[:50],
        }
        return ctx, evidence, meta

    def answer_from_context(
        self,
        question: str,
        options: Optional[List[str]],
        ctx: str,
        evidence: List[str],
        meta: Dict[str, Any],
        extra_system: str = "",
        *,
        certain: bool = True,
        document_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run Ollama + certainty merge using a caller-supplied graph context
        (e.g. from Neo4j Cypher instead of in-memory NetworkX).
        ``meta`` should include ``triple_count``, ``ranked_entities``, ``top_entity_score`` when possible.

        ``document_context``: optional raw text (e.g. PDF excerpt) shown to the model as non-graph
        background; answers must still be consistent with KNOWLEDGE GRAPH CONTEXT when they overlap.
        """
        graph_letter: Optional[str] = None
        graph_margin = 0.0
        option_analysis: List[Dict[str, Any]] = []
        enhanced_conf = 0.0
        if options:
            g = self.retriever.generate_answer(question, options)
            graph_letter = g.get("matched_option")
            enhanced_conf = float(g.get("confidence") or 0.0)
            option_analysis = list(g.get("option_analysis") or [])
            graph_margin = self._graph_option_margin(option_analysis)

        retrieval_conf = self._compute_retrieval_confidence(meta, graph_margin)

        sys_prompt = (SYSTEM_PROMPT_CERTAIN if certain else SYSTEM_PROMPT) + (
            "\n" + extra_system if extra_system else ""
        )

        user_parts = ["QUESTION:\n" + question.strip()]
        user_parts.append("\nKNOWLEDGE GRAPH (logic — triples and paths used to decide the answer):\n" + ctx)
        if document_context and document_context.strip():
            user_parts.append(
                "\nBOOK PASSAGES (content — textbook/exam excerpts for wording and definitions):\n"
                + document_context.strip()[:8000]
            )
        if options and graph_letter:
            user_parts.append(
                f"\nGRAPH-ANCHORED HINT (from triple/entity overlap scores): {graph_letter} "
                f"(score margin vs runner-up: {graph_margin:.2f}; retrieval confidence: {retrieval_conf:.2f})"
            )
        if options:
            user_parts.append("\nOPTIONS:\n" + "\n".join(options))
        user_msg = "\n".join(user_parts)

        if certain and meta.get("triple_count", 0) < 1 and not options:
            return {
                "question": question,
                "answer": "Not enough triples were retrieved from the knowledge graph to answer reliably.",
                "predicted_option": None,
                "final_predicted_option": None,
                "certainty_score": retrieval_conf,
                "retrieval_confidence": retrieval_conf,
                "graph_predicted_option": graph_letter,
                "graph_option_margin": graph_margin,
                "llm_predicted_option": None,
                "consensus": "abstain_no_triples",
                "graph_context": ctx,
                "supporting_evidence": evidence,
                "retrieval": meta,
                "graph_path_lines": meta.get("path_lines", []),
                "traversal_traces": meta.get("traversal_traces", []),
                "inter_entity_paths": meta.get("inter_entity_paths", []),
                "model": self.model,
                "ollama_base": self.ollama_base,
                "enhanced_engine_confidence": enhanced_conf,
            }

        try:
            answer_text = self._ollama_generate(sys_prompt, user_msg)
        except Exception as e:
            return {
                "error": str(e),
                "question": question,
                "graph_context": ctx,
                "supporting_evidence": evidence,
                "retrieval": meta,
                "graph_path_lines": meta.get("path_lines", []),
                "traversal_traces": meta.get("traversal_traces", []),
                "inter_entity_paths": meta.get("inter_entity_paths", []),
                "model": self.model,
                "ollama_base": self.ollama_base,
                "retrieval_confidence": retrieval_conf,
                "graph_predicted_option": graph_letter,
                "graph_option_margin": graph_margin,
            }

        llm_choice: Optional[str] = None
        m = re.search(r"CHOICE:\s*([A-Da-d]|NONE)\b", answer_text, re.IGNORECASE)
        if m:
            g = m.group(1).upper()
            llm_choice = None if g == "NONE" else g

        final_letter: Optional[str] = None
        consensus = "open_ended"
        if options and certain:
            final_letter, consensus = self._merge_mc(
                graph_letter, llm_choice, graph_margin, retrieval_conf
            )
        elif options:
            final_letter = llm_choice or graph_letter
            consensus = "llm_or_graph"

        certainty_score = retrieval_conf
        if certain and graph_letter and llm_choice and graph_letter == llm_choice:
            certainty_score = min(1.0, retrieval_conf + 0.18)
        if certain and consensus == "abstain_low_evidence":
            certainty_score = min(certainty_score, 0.25)

        return {
            "question": question,
            "answer": answer_text,
            "predicted_option": final_letter if certain else (llm_choice or graph_letter),
            "final_predicted_option": final_letter,
            "certainty_score": round(certainty_score, 3),
            "retrieval_confidence": retrieval_conf,
            "graph_predicted_option": graph_letter,
            "graph_option_margin": round(graph_margin, 3),
            "llm_predicted_option": llm_choice,
            "consensus": consensus,
            "graph_context": ctx,
            "supporting_evidence": evidence,
            "retrieval": meta,
            "graph_path_lines": meta.get("path_lines", []),
            "traversal_traces": meta.get("traversal_traces", []),
            "inter_entity_paths": meta.get("inter_entity_paths", []),
            "model": self.model,
            "ollama_base": self.ollama_base,
            "enhanced_engine_confidence": enhanced_conf,
            "option_analysis": option_analysis if options else [],
        }

    @staticmethod
    def _compute_retrieval_confidence(
        meta: Dict[str, Any],
        graph_margin: float,
    ) -> float:
        """0–1 score from graph signals only (no LLM)."""
        top = float(meta.get("top_entity_score") or 0.0)
        ntri = int(meta.get("triple_count") or 0)
        s1 = min(1.0, top / 28.0)
        s2 = min(1.0, ntri / 35.0)
        s3 = min(1.0, max(0.0, graph_margin) / 12.0)
        return round(0.34 * s1 + 0.36 * s2 + 0.30 * s3, 3)

    @staticmethod
    def _graph_option_margin(option_analysis: List[Dict[str, Any]]) -> float:
        if not option_analysis:
            return 0.0
        scores = sorted((float(x.get("score", 0)) for x in option_analysis), reverse=True)
        if len(scores) >= 2:
            return scores[0] - scores[1]
        return scores[0]

    def _merge_mc(
        self,
        graph_letter: Optional[str],
        llm_letter: Optional[str],
        graph_margin: float,
        retrieval_conf: float,
    ) -> Tuple[Optional[str], str]:
        """Return (final_letter, consensus_code) prioritizing grounded graph when strong."""
        if not graph_letter and not llm_letter:
            return None, "no_choice"
        if graph_letter and llm_letter and graph_letter == llm_letter:
            return graph_letter, "llm_graph_agree"
        if graph_margin >= 5.0 and graph_letter:
            return graph_letter, "graph_high_margin"
        if graph_margin >= 2.0 and graph_letter and retrieval_conf >= 0.35:
            return graph_letter, "graph_margin_ok"
        if retrieval_conf < 0.22 and graph_margin < 1.5:
            return None, "abstain_low_evidence"
        if graph_letter:
            return graph_letter, "graph_default"
        return llm_letter, "llm_only"

    def _ollama_generate(self, system: str, user: str, timeout: int = 180) -> str:
        if requests is None:
            raise RuntimeError("The requests package is required for Ollama. pip install requests")

        url = f"{self.ollama_base}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message") or {}
        text = (msg.get("content") or "").strip()
        if text:
            return text
        # Fallback for older response shapes
        return (data.get("response") or "").strip()

    def answer(
        self,
        question: str,
        options: Optional[List[str]] = None,
        extra_system: str = "",
        *,
        certain: bool = True,
    ) -> Dict[str, Any]:
        """
        If ``certain`` is True (default), combines:
        - deterministic graph MCQ scores (EnhancedQueryEngine),
        - retrieval confidence from entity/triple strength and option margin,
        - Ollama narrative with a stricter system prompt and merged final letter.
        """
        ctx, evidence, meta = self.collect_graph_context(question)
        return self.answer_from_context(
            question, options, ctx, evidence, meta, extra_system, certain=certain
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="GraphRAG Q&A via KG retrieval + Ollama.")
    parser.add_argument("question", nargs="?", help="Question text")
    parser.add_argument("--no-semantic", action="store_true", help="Disable SBERT entity expansion")
    parser.add_argument("--model", default=None, help="Ollama model name (default env OLLAMA_MODEL or llama3.2)")
    parser.add_argument("--ollama-host", default=None, help="Ollama base URL")
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    parser.add_argument(
        "--no-certain",
        action="store_true",
        help="Disable graph+margin consensus and simpler system prompt (legacy behavior)",
    )
    args = parser.parse_args()

    if not args.question:
        args.question = "What is Snort used for in network security?"

    src = str(PROJECT_ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    kg = KnowledgeGraphBuilder()
    kg.build_graph()
    rag = GraphRAGOllama(
        kg_builder=kg,
        model=args.model,
        ollama_base=args.ollama_host,
        use_semantic_entities=not args.no_semantic,
    )

    result = rag.answer(args.question, certain=not args.no_certain)
    if args.json:
        out = {k: v for k, v in result.items() if k != "graph_context"}
        out["graph_context"] = result.get("graph_context", "")[:2000]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    if result.get("error"):
        print("Ollama error:", result["error"])
        print("\n--- Retrieved graph context (still useful) ---\n")
        print(result.get("graph_context", ""))
        print("\nInstall/run Ollama: https://ollama.com — then `ollama pull", rag.model + "`")
        return

    print(result["answer"])
    if not args.no_certain:
        print(
            "\n--- Certainty (graph-backed) ---\n"
            f"retrieval_confidence={result.get('retrieval_confidence')}  "
            f"certainty_score={result.get('certainty_score')}  "
            f"consensus={result.get('consensus')}\n"
            f"graph_option={result.get('graph_predicted_option')}  "
            f"margin={result.get('graph_option_margin')}  "
            f"llm_choice={result.get('llm_predicted_option')}  "
            f"final={result.get('final_predicted_option')}"
        )
    elif result.get("predicted_option"):
        print("\nParsed CHOICE:", result["predicted_option"])


if __name__ == "__main__":
    main()
