from __future__ import annotations

import logging
import os
from typing import List, Dict, Any

import requests

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"


class TavilyClient:
    """Tavily 웹 검색 클라이언트.

    내부 지식(RAG 컨텍스트)으로 답변하기 어렵다고 판단될 때만 호출합니다.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY 환경변수가 설정되지 않았습니다.")

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Tavily API로 웹 검색 후 결과 리스트를 반환합니다.

        Returns:
            List of dicts with keys: title, url, content, score
        """
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True,
            "include_raw_content": False,
        }

        try:
            resp = requests.post(TAVILY_API_URL, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("Tavily 검색 요청 실패: %s", e)
            return []

        results = []
        # Tavily가 요약 답변을 제공하는 경우 첫 항목으로 포함
        tavily_answer = data.get("answer")
        if tavily_answer:
            results.append({
                "title": "Tavily 요약 답변",
                "url": "",
                "content": tavily_answer,
                "score": 1.0,
            })

        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score", 0.0),
            })

        return results[:max_results]

    def build_context(self, results: List[Dict[str, Any]]) -> str:
        """검색 결과를 LLM 프롬프트용 컨텍스트 문자열로 변환합니다."""
        if not results:
            return ""
        parts = []
        for r in results:
            source = f"[{r['title']}]" + (f"({r['url']})" if r["url"] else "")
            parts.append(f"{source}\n{r['content']}")
        return "\n\n".join(parts)
