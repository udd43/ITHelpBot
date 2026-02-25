from __future__ import annotations

import os
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive.file"]


class GoogleDocsClient:
    def __init__(
        self,
        service_account_json: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
    ) -> None:
        self.service_account_json = service_account_json or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or ""
        self.parent_folder_id = parent_folder_id or os.getenv("GOOGLE_DOCS_PARENT_FOLDER_ID") or ""
        if not self.service_account_json or not self.parent_folder_id:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON 또는 GOOGLE_DOCS_PARENT_FOLDER_ID 환경변수가 설정되지 않았습니다.")

        creds = service_account.Credentials.from_service_account_file(
            self.service_account_json,
            scopes=SCOPES,
        )
        self.docs_service = build("docs", "v1", credentials=creds)
        self.drive_service = build("drive", "v3", credentials=creds)

    def create_issue_doc(self, title: str, question: str, answer: str) -> Optional[str]:
        """IT 이슈를 하나의 Google Docs 문서로 생성하고 URL을 반환합니다."""
        # 1) 빈 문서 생성
        doc = (
            self.docs_service.documents()
            .create(body={"title": title[:200]})
            .execute()
        )
        doc_id = doc.get("documentId")
        if not doc_id:
            return None

        # 2) 폴더에 이동
        self.drive_service.files().update(
            fileId=doc_id,
            addParents=self.parent_folder_id,
            fields="id, parents",
        ).execute()

        # 3) 내용 작성
        content = f"# 질문\n\n{question}\n\n# 답변\n\n{answer}\n"
        requests_body = [
            {
                "insertText": {
                    "location": {"index": 1},
                    "text": content,
                }
            }
        ]
        self.docs_service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests_body}
        ).execute()

        return f"https://docs.google.com/document/d/{doc_id}/edit"

