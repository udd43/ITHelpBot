from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class KnowledgeChunk:
    source: str
    text: str


class KnowledgeLoader:
    def __init__(self, directory: str, chunk_size: int = 800, encoding: str = "utf-8") -> None:
        self.directory = Path(directory)
        self.chunk_size = chunk_size
        self.encoding = encoding
        self.chunks: List[KnowledgeChunk] = []

    def load(self) -> None:
        self.chunks.clear()
        if not self.directory.exists():
            return

        for path in sorted(self.directory.rglob("*.txt")):
            text = path.read_text(encoding=self.encoding, errors="ignore")
            for start in range(0, len(text), self.chunk_size):
                chunk_text = text[start : start + self.chunk_size].strip()
                if chunk_text:
                    self.chunks.append(
                        KnowledgeChunk(source=os.path.relpath(path, self.directory), text=chunk_text)
                    )

    def is_empty(self) -> bool:
        return len(self.chunks) == 0

    def search(self, query: str, top_k: int = 5, max_chars: int = 6000) -> Tuple[str, List[KnowledgeChunk]]:
        """
        매우 단순한 키워드 기반 스코어링으로 관련 chunk를 뽑아냅니다.
        한국어/영어 모두에 대해 공통적으로 동작하는 최소 구현입니다.
        """
        if not query.strip() or self.is_empty():
            return "", []

        query_lower = query.lower()
        keywords = [w for w in query_lower.split() if len(w) > 1]

        def score(chunk: KnowledgeChunk) -> int:
            text_lower = chunk.text.lower()
            base = text_lower.count(query_lower)
            bonus = sum(text_lower.count(k) for k in keywords)
            return base * 10 + bonus

        ranked = sorted(self.chunks, key=score, reverse=True)
        selected = [c for c in ranked if score(c) > 0][:top_k] or ranked[: top_k]

        context_parts: List[str] = []
        used_chars = 0
        limited_selected: List[KnowledgeChunk] = []

        for chunk in selected:
            chunk_text = f"[{chunk.source}]\n{chunk.text}\n"
            if used_chars + len(chunk_text) > max_chars:
                remaining = max_chars - used_chars
                if remaining <= 0:
                    break
                chunk_text = chunk_text[:remaining]
            context_parts.append(chunk_text)
            used_chars += len(chunk_text)
            limited_selected.append(chunk)
            if used_chars >= max_chars:
                break

        return "\n\n".join(context_parts), limited_selected

