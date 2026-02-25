from __future__ import annotations

import os
from typing import Any, Dict, List

import requests


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY 환경변수가 설정되지 않았습니다.")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def ask(self, question: str, context: str) -> str:
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "당신은 사용자가 작성한 txt 지식을 기반으로 답변하는 어시스턴트입니다. "
                    "제공된 컨텍스트를 우선적으로 신뢰하고, 컨텍스트에 없는 내용은 모른다고 솔직하게 말하세요."
                ),
            },
            {
                "role": "user",
                "content": (
                    "다음은 사용자가 제공한 지식 컨텍스트입니다.\n\n"
                    f"{context or '(컨텍스트 없음)'}\n\n"
                    "위 내용을 참고해서, 아래 질문에 한국어로 자세히 답변하세요.\n\n"
                    f"질문: {question}"
                ),
            },
        ]

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        resp = requests.post(GROQ_API_URL, headers=self._headers(), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return "Groq 응답을 해석하는 중 오류가 발생했습니다."

