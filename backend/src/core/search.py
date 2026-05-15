from __future__ import annotations

from dataclasses import dataclass
import re

from storage.embeddings import EmbeddingProvider
from storage.repositories import DocumentRepository, SourceRepository, TextSearchHit
from storage.vector_store import VectorSearchHit


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    score: float
    text: str
    source_id: str
    path: str
    title: str


@dataclass(frozen=True)
class _SearchCandidate:
    result: SearchResult
    document_id: str


class SearchService:
    def __init__(
        self,
        embeddings: EmbeddingProvider,
        vector_store,
        documents: DocumentRepository | None = None,
        sources: SourceRepository | None = None,
        *,
        overfetch_multiplier: int = 2,
        max_overfetch: int = 100,
        vector_multiplier: int = 10,
        max_vector_overfetch: int = 500,
        max_cluster_gap: int = 2,
        context_window: int = 1,
        max_context_chars: int = 4_800,
        use_fts: bool = True,
    ) -> None:
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.documents = documents
        self.sources = sources
        self.overfetch_multiplier = overfetch_multiplier
        self.max_overfetch = max_overfetch
        self.vector_multiplier = vector_multiplier
        self.max_vector_overfetch = max_vector_overfetch
        self.max_cluster_gap = max_cluster_gap
        self.context_window = context_window
        self.max_context_chars = max_context_chars
        self.use_fts = use_fts

    async def search(self, query: str, limit: int = 8, source_id: str | None = None) -> list[SearchResult]:
        limit = max(1, limit)
        query_embedding = (await self.embeddings.embed([query]))[0]
        overfetch_limit = min(max(limit * self.overfetch_multiplier, limit), self.max_overfetch)
        vector_limit = min(max(overfetch_limit * self.vector_multiplier, overfetch_limit), self.max_vector_overfetch)
        vector_hits = self.vector_store.search(
            query_embedding,
            limit=vector_limit,
            source_id=source_id,
            embedding_model=self.embeddings.identity,
        )
        fts_hits = (
            self.documents.search_text(query, limit=overfetch_limit, source_id=source_id)
            if self.documents and self.use_fts
            else []
        )
        hits = self._rank_hybrid(vector_hits, fts_hits)
        candidates = self._build_candidates(hits, query)
        return [candidate.result for candidate in self._diversify(candidates, limit)]

    def _rank_hybrid(
        self,
        vector_hits: list[VectorSearchHit],
        fts_hits: list[TextSearchHit],
    ) -> list[VectorSearchHit]:
        if not fts_hits:
            return vector_hits
        if not vector_hits:
            return [
                _text_hit_to_vector_hit(hit, _rrf_score(fts_rank=index + 1, channel_count=1))
                for index, hit in enumerate(fts_hits)
            ]

        by_chunk_id: dict[str, VectorSearchHit] = {hit.chunk_id: hit for hit in vector_hits}
        by_chunk_id.update({hit.chunk_id: _text_hit_to_vector_hit(hit, hit.score) for hit in fts_hits})
        vector_ranks = {hit.chunk_id: index + 1 for index, hit in enumerate(vector_hits)}
        fts_ranks = {hit.chunk_id: index + 1 for index, hit in enumerate(fts_hits)}

        fused_hits: list[VectorSearchHit] = []
        for chunk_id, hit in by_chunk_id.items():
            score = _rrf_score(
                vec_rank=vector_ranks.get(chunk_id),
                fts_rank=fts_ranks.get(chunk_id),
                channel_count=2,
            )
            if chunk_id in fts_ranks:
                score += 0.001
            fused_hits.append(
                VectorSearchHit(
                    chunk_id=hit.chunk_id,
                    score=score,
                    text=hit.text,
                    metadata=hit.metadata,
                )
            )
        return sorted(fused_hits, key=lambda hit: hit.score, reverse=True)

    def _build_candidates(self, hits: list[VectorSearchHit], query: str) -> list[_SearchCandidate]:
        if not hits:
            return []

        if self.documents is None:
            return [self._raw_candidate(hit, query) for hit in hits]

        grouped: dict[str, list[VectorSearchHit]] = {}
        raw_hits: list[VectorSearchHit] = []
        for hit in hits:
            document_id = str(hit.metadata.get("document_id", ""))
            ordinal = _metadata_int(hit.metadata.get("ordinal"))
            if document_id and ordinal is not None:
                grouped.setdefault(document_id, []).append(hit)
            else:
                raw_hits.append(hit)

        candidates = [self._raw_candidate(hit, query) for hit in raw_hits]
        for document_id, document_hits in grouped.items():
            candidates.extend(self._document_candidates(document_id, document_hits, query))

        return sorted(candidates, key=lambda candidate: candidate.result.score, reverse=True)

    def _document_candidates(
        self,
        document_id: str,
        hits: list[VectorSearchHit],
        query: str,
    ) -> list[_SearchCandidate]:
        chunks = self.documents.list_chunks_by_document(document_id)
        if not chunks:
            return [self._raw_candidate(hit, query) for hit in hits]

        chunks_by_ordinal = {int(chunk["ordinal"]): chunk for chunk in chunks}
        clusters = _cluster_hits_by_ordinal(hits, self.max_cluster_gap)
        candidates: list[_SearchCandidate] = []

        for cluster in clusters:
            primary_hit = max(cluster, key=lambda hit: hit.score)
            cluster_ordinals = [
                ordinal
                for hit in cluster
                if (ordinal := _metadata_int(hit.metadata.get("ordinal"))) is not None
            ]
            if not cluster_ordinals:
                candidates.append(self._raw_candidate(primary_hit, query))
                continue

            selected_chunks = self._select_structured_chunks(chunks, cluster_ordinals)
            if not selected_chunks:
                context_ordinals = range(
                    max(0, min(cluster_ordinals) - self.context_window),
                    max(cluster_ordinals) + self.context_window + 1,
                )
                selected_chunks = [
                    chunks_by_ordinal[ordinal]
                    for ordinal in context_ordinals
                    if ordinal in chunks_by_ordinal
                ]

            text = _assemble_text(selected_chunks, self.max_context_chars) or primary_hit.text
            score = self._score_with_metadata_boost(primary_hit, query)

            candidates.append(
                _SearchCandidate(
                    result=SearchResult(
                        chunk_id=primary_hit.chunk_id,
                        document_id=document_id,
                        score=score,
                        text=text,
                        source_id=str(primary_hit.metadata.get("source_id", "")),
                        path=str(primary_hit.metadata.get("path", "")),
                        title=str(primary_hit.metadata.get("title", "")),
                    ),
                    document_id=document_id,
                )
            )

        return candidates

    def _select_structured_chunks(
        self,
        chunks: list[dict[str, object]],
        cluster_ordinals: list[int],
    ) -> list[dict[str, object]]:
        chunks_by_ordinal = {int(chunk["ordinal"]): chunk for chunk in chunks}
        selected_ordinals: set[int] = set()

        for ordinal in cluster_ordinals:
            chunk = chunks_by_ordinal.get(ordinal)
            if not chunk:
                continue
            section_path = _section_path(chunk)
            if not section_path:
                continue

            selected_ordinals.add(ordinal)
            parent_path = section_path[:-1]
            if parent_path:
                parent = _nearest_chunk_by_section_path(chunks, parent_path, before_ordinal=ordinal)
                if parent:
                    selected_ordinals.add(int(parent["ordinal"]))

            siblings = [
                candidate
                for candidate in chunks
                if _section_path(candidate) == section_path and int(candidate["ordinal"]) != ordinal
            ]
            preceding = [
                candidate for candidate in siblings if int(candidate["ordinal"]) < ordinal
            ][-self.context_window :]
            subsequent = [
                candidate for candidate in siblings if int(candidate["ordinal"]) > ordinal
            ][: max(2, self.context_window)]
            selected_ordinals.update(int(candidate["ordinal"]) for candidate in preceding + subsequent)

            child_prefix = section_path + [""]
            children = [
                candidate
                for candidate in chunks
                if _section_path(candidate)[: len(section_path)] == section_path
                and len(_section_path(candidate)) == len(child_prefix)
                and int(candidate["ordinal"]) > ordinal
            ][:3]
            selected_ordinals.update(int(candidate["ordinal"]) for candidate in children)

        return [chunks_by_ordinal[ordinal] for ordinal in sorted(selected_ordinals) if ordinal in chunks_by_ordinal]

    def _raw_candidate(self, hit: VectorSearchHit, query: str) -> _SearchCandidate:
        document_id = str(hit.metadata.get("document_id", ""))
        return _SearchCandidate(
            result=SearchResult(
                chunk_id=hit.chunk_id,
                document_id=document_id,
                score=self._score_with_metadata_boost(hit, query),
                text=hit.text,
                source_id=str(hit.metadata.get("source_id", "")),
                path=str(hit.metadata.get("path", "")),
                title=str(hit.metadata.get("title", "")),
            ),
            document_id=document_id or hit.chunk_id,
        )

    def _score_with_metadata_boost(self, hit: VectorSearchHit, query: str) -> float:
        score = max(0.0, float(hit.score))
        terms = _query_terms(query)
        if not terms:
            return score

        title = str(hit.metadata.get("title", "")).lower()
        path = str(hit.metadata.get("path", "")).lower()
        source_name = ""
        source_id = str(hit.metadata.get("source_id", ""))
        if self.sources and source_id:
            source = self.sources.get(source_id)
            source_name = source.name.lower() if source else ""

        boost = 0.0
        title_coverage = _coverage(terms, title)
        path_coverage = _coverage(terms, path)
        if title_coverage:
            boost += 0.08 * title_coverage
        if path_coverage:
            boost += 0.04 * path_coverage
        if path.startswith("docs/en/framework/"):
            boost += 0.03
        elif "/community-articles/" in path:
            boost -= 0.015
        if terms:
            text = hit.text.lower()
            coverage = sum(1 for term in terms if term in text) / len(terms)
            boost += min(0.025, coverage * 0.025)
        if source_name and any(term in source_name for term in terms):
            boost += 0.005

        return max(0.0, score + boost)

    def _diversify(self, candidates: list[_SearchCandidate], limit: int) -> list[_SearchCandidate]:
        if len(candidates) <= limit:
            return candidates

        sorted_candidates = sorted(candidates, key=lambda candidate: candidate.result.score, reverse=True)
        top_score = sorted_candidates[0].result.score
        selected: list[_SearchCandidate] = []
        selected_keys: set[str] = set()
        document_counts: dict[str, int] = {}

        for candidate in sorted_candidates:
            if len(selected) >= limit:
                break
            document_count = document_counts.get(candidate.document_id, 0)
            is_close_extra = candidate.result.score >= top_score - 0.08
            if document_count == 0 or is_close_extra:
                selected.append(candidate)
                selected_keys.add(candidate.result.chunk_id)
                document_counts[candidate.document_id] = document_count + 1

        for candidate in sorted_candidates:
            if len(selected) >= limit:
                break
            if candidate.result.chunk_id in selected_keys:
                continue
            selected.append(candidate)
            selected_keys.add(candidate.result.chunk_id)

        return selected


def _cluster_hits_by_ordinal(hits: list[VectorSearchHit], max_gap: int) -> list[list[VectorSearchHit]]:
    ordered_hits = sorted(
        hits,
        key=lambda hit: (_metadata_int(hit.metadata.get("ordinal")) or 0, -hit.score),
    )
    clusters: list[list[VectorSearchHit]] = []
    current: list[VectorSearchHit] = []
    previous_ordinal: int | None = None

    for hit in ordered_hits:
        ordinal = _metadata_int(hit.metadata.get("ordinal"))
        if ordinal is None:
            if current:
                clusters.append(current)
                current = []
                previous_ordinal = None
            clusters.append([hit])
            continue

        if previous_ordinal is None or ordinal - previous_ordinal <= max_gap:
            current.append(hit)
        else:
            clusters.append(current)
            current = [hit]
        previous_ordinal = ordinal

    if current:
        clusters.append(current)
    return clusters


def _assemble_text(chunks: list[dict[str, object]], max_chars: int) -> str:
    parts: list[str] = []
    used = 0
    for chunk in chunks:
        text = str(chunk.get("text", "")).strip()
        if not text:
            continue
        if parts and text == parts[-1]:
            continue
        if parts:
            text = _trim_overlap(parts[-1], text)
            if not text:
                continue
        separator = "\n\n" if parts else ""
        next_length = used + len(separator) + len(text)
        if next_length > max_chars:
            remaining = max_chars - used - len(separator)
            if remaining > 120:
                parts.append(f"{separator}{text[:remaining].rstrip()}...")
            break
        parts.append(f"{separator}{text}")
        used = next_length
    return "".join(parts)


def _trim_overlap(previous: str, current: str, max_overlap: int = 400) -> str:
    limit = min(len(previous), len(current), max_overlap)
    for size in range(limit, 39, -1):
        if previous[-size:] == current[:size]:
            return current[size:].lstrip()
    return current


def _metadata_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _section_path(chunk: dict[str, object]) -> list[str]:
    metadata = chunk.get("metadata", {})
    if not isinstance(metadata, dict):
        return []
    path = metadata.get("section_path", [])
    if isinstance(path, list):
        return [str(part) for part in path if str(part)]
    return []


def _nearest_chunk_by_section_path(
    chunks: list[dict[str, object]],
    section_path: list[str],
    before_ordinal: int,
) -> dict[str, object] | None:
    candidates = [
        chunk
        for chunk in chunks
        if _section_path(chunk) == section_path and int(chunk["ordinal"]) < before_ordinal
    ]
    return candidates[-1] if candidates else None


def _query_terms(query: str) -> set[str]:
    stopwords = {
        "and",
        "for",
        "how",
        "the",
        "with",
        "what",
        "when",
        "where",
    }
    return {
        term
        for term in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", query.lower())
        if term not in stopwords
    }


def _coverage(terms: set[str], value: str) -> float:
    if not terms or not value:
        return 0.0
    return sum(1 for term in terms if term in value) / len(terms)


def _text_hit_to_vector_hit(hit: TextSearchHit, score: float) -> VectorSearchHit:
    return VectorSearchHit(
        chunk_id=hit.chunk_id,
        score=score,
        text=hit.text,
        metadata=hit.metadata,
    )


def _rrf_score(
    vec_rank: int | None = None,
    fts_rank: int | None = None,
    *,
    channel_count: int,
    k: int = 60,
) -> float:
    score = 0.0
    if vec_rank is not None:
        score += 1 / (k + vec_rank)
    if fts_rank is not None:
        score += 1 / (k + fts_rank)
    max_score = channel_count / (k + 1)
    return score / max_score if max_score else 0.0
