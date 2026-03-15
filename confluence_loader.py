import os
import requests
from requests.auth import HTTPBasicAuth
from typing import List
from bs4 import BeautifulSoup
from knowledge_loader import KnowledgeChunk

class ConfluenceLoader:
    def __init__(self, domain: str = None, email: str = None, api_token: str = None, page_ids: List[str] = None):
        self.domain = domain or os.getenv("CONFLUENCE_DOMAIN", "") # e.g., your-domain.atlassian.net
        self.email = email or os.getenv("CONFLUENCE_EMAIL", "")
        self.api_token = api_token or os.getenv("CONFLUENCE_API_TOKEN", "")
        self.page_ids = page_ids or []
        
        env_pages = os.getenv("CONFLUENCE_KNOWLEDGE_PAGE_IDS", "")
        if env_pages and not self.page_ids:
            self.page_ids = [p.strip() for p in env_pages.split(",") if p.strip()]

    def load(self, chunk_size: int = 800) -> List[KnowledgeChunk]:
        if not self.domain or not self.email or not self.api_token or not self.page_ids:
            return []

        chunks = []
        auth = HTTPBasicAuth(self.email, self.api_token)
        headers = {
            "Accept": "application/json"
        }

        for pid in self.page_ids:
            url = f"https://{self.domain}/wiki/api/v2/pages/{pid}?body-format=storage"
            try:
                resp = requests.get(url, headers=headers, auth=auth, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    html_content = data.get("body", {}).get("storage", {}).get("value", "")
                    
                    # Parse HTML to plain text using BeautifulSoup
                    soup = BeautifulSoup(html_content, "html.parser")
                    text = soup.get_text(separator="\n")
                    
                    # Chunking
                    for start in range(0, len(text), chunk_size):
                        chunk_text = text[start : start + chunk_size].strip()
                        if chunk_text:
                            chunks.append(
                                KnowledgeChunk(source=f"Confluence_Page_{pid}", text=chunk_text)
                            )
            except Exception as e:
                pass

        return chunks
