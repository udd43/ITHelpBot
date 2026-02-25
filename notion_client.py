from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests


NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"


class NotionClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        database_id: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("NOTION_API_KEY") or ""
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID") or ""
        if not self.api_key or not self.database_id:
            raise ValueError("NOTION_API_KEY 또는 NOTION_DATABASE_ID 환경변수가 설정되지 않았습니다.")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    def create_issue_page(
        self,
        title: str,
        question: str,
        answer: str,
        slack_user: Optional[str] = None,
        slack_link: Optional[str] = None,
    ) -> Optional[str]:
        """IT 이슈 한 건을 노션 DB에 페이지로 기록합니다. 성공 시 페이지 URL을 반환합니다."""
        properties: Dict[str, Any] = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": title[:200],
                        }
                    }
                ]
            }
        }

        if slack_user:
            properties["RequestedBy"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": slack_user,
                        }
                    }
                ]
            }

        children = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "질문"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": question}}]},
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "답변"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": answer}}]},
            },
        ]

        if slack_link:
            children.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "원본 Slack 스레드 바로가기",
                                    "link": {"url": slack_link},
                                },
                            }
                        ]
                    },
                }
            )

        payload: Dict[str, Any] = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
            "children": children,
        }

        resp = requests.post(NOTION_API_URL, headers=self._headers(), json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        url = data.get("url")
        return url

