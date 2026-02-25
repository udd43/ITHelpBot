from __future__ import annotations

import os
from typing import List, Optional, Tuple

import requests


GOOGLE_SEARCH_API_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleSearchClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_SEARCH_API_KEY") or ""
        self.search_engine_id = search_engine_id or os.getenv("GOOGLE_SEARCH_ENGINE_ID") or ""
        if not self.api_key or not self.search_engine_id:
            raise ValueError("GOOGLE_SEARCH_API_KEY 또는 GOOGLE_SEARCH_ENGINE_ID 환경변수가 설정되지 않았습니다.")

    def search(self, query: str, max_results: int = 3) -> List[Tuple[str, str, str]]:
        """Google Custom Search를 통해 상위 결과를 반환합니다. (title, link, snippet)"""
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": max_results,
            "lr": "lang_ko",
        }
        resp = requests.get(GOOGLE_SEARCH_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", []) or []
        results: List[Tuple[str, str, str]] = []
        for item in items:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            if link:
                results.append((title, link, snippet))
        return results

