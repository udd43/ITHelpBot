import os
import requests
from typing import List
from knowledge_loader import KnowledgeChunk

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

class NotionLoader:
    def __init__(self, api_key: str = None, page_ids: List[str] = None):
        self.api_key = api_key or os.getenv("NOTION_API_KEY", "")
        self.page_ids = page_ids or []
        
        # 콤마로 구분된 환경변수 지원
        env_pages = os.getenv("NOTION_KNOWLEDGE_PAGE_IDS", "")
        if env_pages and not self.page_ids:
            self.page_ids = [p.strip() for p in env_pages.split(",") if p.strip()]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": NOTION_VERSION,
        }

    def _get_page_blocks(self, block_id: str) -> List[dict]:
        url = f"{NOTION_API_URL}/blocks/{block_id}/children?page_size=100"
        results = []
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results.extend(data.get("results", []))
                # 페이징 생략 (단순 구현 수준)
        except Exception:
            pass
        return results

    def _extract_text(self, blocks: List[dict]) -> str:
        text_parts = []
        for block in blocks:
            b_type = block.get("type", "")
            if b_type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "quote"]:
                rich_texts = block.get(b_type, {}).get("rich_text", [])
                for rt in rich_texts:
                    text_parts.append(rt.get("plain_text", ""))
                text_parts.append("\n")
        return "".join(text_parts)

    def load(self, chunk_size: int = 800) -> List[KnowledgeChunk]:
        if not self.api_key or not self.page_ids:
            return []

        chunks = []
        for pid in self.page_ids:
            blocks = self._get_page_blocks(pid)
            text = self._extract_text(blocks)
            
            for start in range(0, len(text), chunk_size):
                chunk_text = text[start : start + chunk_size].strip()
                if chunk_text:
                    chunks.append(
                        KnowledgeChunk(source=f"Notion_Page_{pid}", text=chunk_text)
                    )
        return chunks
