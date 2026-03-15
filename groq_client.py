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

    def _call(self, messages: List[Dict[str, Any]]) -> str:
        """Groq API 공통 호출 헬퍼."""
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

    def ask(self, question: str, context: str) -> str:
        """내부 RAG 컨텍스트를 이용해 질문에 답변합니다."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "당신은 IT 헬프데스크 어시스턴트입니다. "
                    "제공된 내부 지식 컨텍스트를 우선적으로 신뢰하고, "
                    "컨텍스트에 없는 내용은 모른다고 솔직하게 말하세요."
                ),
            },
            {
                "role": "user",
                "content": (
                    "다음은 내부 지식 컨텍스트입니다.\n\n"
                    f"{context or '(컨텍스트 없음)'}\n\n"
                    "위 내용을 참고해서, 아래 질문에 한국어로 자세히 답변하세요.\n\n"
                    f"질문: {question}"
                ),
            },
        ]
        return self._call(messages)

    def can_answer_from_context(self, question: str, context: str) -> bool:
        """현재 컨텍스트만으로 질문에 충분히 답변 가능한지 판단합니다.

        LLM에게 yes/no 자기 평가를 요청하고, 'yes'가 포함되면 True를 반환합니다.
        컨텍스트가 비어 있으면 즉시 False를 반환합니다.
        """
        if not context or not context.strip():
            return False

        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "당신은 IT 헬프데스크 전문가입니다. "
                    "주어진 컨텍스트만으로 질문에 충분하고 정확하게 답변할 수 있는지 "
                    "판단하는 역할을 맡습니다."
                ),
            },
            {
                "role": "user",
                "content": (
                    "아래 [컨텍스트]와 [질문]을 보고, "
                    "컨텍스트만으로 질문에 충분하고 정확하게 답변 가능한지 판단하세요.\n"
                    "판단 기준: 컨텍스트에 질문과 직접 관련된 구체적인 정보가 있어야 합니다.\n"
                    "반드시 'yes' 또는 'no' 한 단어로만 답하세요.\n\n"
                    f"[컨텍스트]\n{context}\n\n"
                    f"[질문]\n{question}"
                ),
            },
        ]
        try:
            result = self._call(messages).lower().strip()
            return "yes" in result
        except Exception:
            # 판단 실패 시 웹 검색을 시도하도록 False 반환
            return False

    def ask_with_web(self, question: str, rag_context: str, web_context: str) -> str:
        """내부 RAG 컨텍스트와 Tavily 웹 검색 결과를 함께 사용해 답변합니다."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "당신은 IT 헬프데스크 어시스턴트입니다. "
                    "내부 지식 컨텍스트와 최신 웹 검색 결과를 모두 활용해 "
                    "정확하고 도움이 되는 답변을 한국어로 제공하세요. "
                    "웹 검색 결과를 인용할 때는 출처(URL)를 함께 언급하세요."
                ),
            },
            {
                "role": "user",
                "content": (
                    "[내부 지식 컨텍스트]\n"
                    f"{rag_context or '(내부 컨텍스트 없음)'}\n\n"
                    "[웹 검색 결과]\n"
                    f"{web_context or '(웹 검색 결과 없음)'}\n\n"
                    "위 두 가지 정보를 종합해서, 아래 질문에 한국어로 자세히 답변하세요.\n\n"
                    f"질문: {question}"
                ),
            },
        ]
        return self._call(messages)

