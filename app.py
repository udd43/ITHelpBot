from __future__ import annotations

import logging
import os
import re
from typing import Optional

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from knowledge_loader import KnowledgeLoader
from groq_client import GroqClient
from notion_client import NotionClient
from google_docs_client import GoogleDocsClient
from google_search_client import GoogleSearchClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_env() -> None:
    # 현재 디렉터리의 .env 로드
    load_dotenv()


def create_app() -> App:
    load_env()

    bot_token = os.getenv("SLACK_BOT_TOKEN")
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    app_token = os.getenv("SLACK_APP_TOKEN")

    if not bot_token or not signing_secret or not app_token:
        raise RuntimeError("Slack 환경변수(SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SLACK_APP_TOKEN)가 설정되지 않았습니다.")

    knowledge_dir = os.getenv("KNOWLEDGE_DIR", "knowledge")
    max_context_chars = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))

    knowledge_loader = KnowledgeLoader(directory=knowledge_dir)
    knowledge_loader.load()
    logger.info("Knowledge loaded from %s (chunks=%d)", knowledge_dir, len(knowledge_loader.chunks))

    try:
        groq_client = GroqClient()
    except ValueError as e:
        raise RuntimeError(str(e)) from e

    # 선택적 연동: Notion, Google Docs, Google 검색
    notion_client: Optional[NotionClient]
    google_docs_client: Optional[GoogleDocsClient]
    google_search_client: Optional[GoogleSearchClient]
    try:
        notion_client = NotionClient()
    except ValueError:
        notion_client = None
        logger.info("Notion 연동 비활성화 (환경변수 미설정)")

    try:
        google_docs_client = GoogleDocsClient()
    except Exception:
        google_docs_client = None
        logger.info("Google Docs 연동 비활성화 (환경변수 또는 자격 증명 미설정)")

    try:
        google_search_client = GoogleSearchClient()
    except ValueError:
        google_search_client = None
        logger.info("Google 검색 연동 비활성화 (환경변수 미설정)")

    app = App(token=bot_token, signing_secret=signing_secret)

    def extract_question(text: str, bot_user_id: Optional[str]) -> str:
        # 멘션(@U12345) 제거 및 양쪽 공백 정리
        if bot_user_id:
            mention_pattern = rf"<@{re.escape(bot_user_id)}>"
            text = re.sub(mention_pattern, "", text)
        return text.strip()

    @app.event("app_mention")
    def handle_app_mention(body, say, client, logger):  # type: ignore[no-untyped-def]
        event = body.get("event", {})
        text = event.get("text", "") or ""
        channel = event.get("channel")
        thread_ts = event.get("ts")

        bot_user_id = None
        try:
            auth = client.auth_test()
            bot_user_id = auth.get("user_id")
        except Exception as e:  # pragma: no cover - 런타임 에러 로깅용
            logger.error("Slack auth_test 실패: %s", e)

        question = extract_question(text, bot_user_id)
        if not question:
            say(
                text="안녕하세요! 저에게 알고 싶은 내용을 멘션과 함께 입력해주세요.\n예: `@봇이름 HTTP 상태코드 정리해줘`",
                channel=channel,
                thread_ts=thread_ts,
            )
            return

        if knowledge_loader.is_empty():
            say(
                text="아직 등록된 지식(txt 파일)이 없습니다. 프로젝트의 `knowledge/` 폴더에 txt 파일을 추가한 뒤 봇을 다시 시작해주세요.",
                channel=channel,
                thread_ts=thread_ts,
            )
            return

        try:
            context, _ = knowledge_loader.search(question, max_chars=max_context_chars)
            answer = groq_client.ask(question=question, context=context)
        except Exception as e:  # pragma: no cover - 외부 연동 에러
            logger.exception("질문 처리 중 오류 발생: %s", e)
            say(
                text="질문을 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                channel=channel,
                thread_ts=thread_ts,
            )
            return

        # IT 이슈를 Notion / Google Docs에 기록 (가능한 경우)
        notion_url: Optional[str] = None
        docs_url: Optional[str] = None
        slack_link: Optional[str] = None

        if channel and thread_ts:
            team_id = body.get("team_id")
            if team_id:
                slack_link = f"https://app.slack.com/client/{team_id}/{channel}/thread/{channel}-{thread_ts}"

        title = question[:50]
        user_name = event.get("user")

        if notion_client is not None:
            try:
                notion_url = notion_client.create_issue_page(
                    title=title,
                    question=question,
                    answer=answer,
                    slack_user=user_name,
                    slack_link=slack_link,
                )
            except Exception as e:  # pragma: no cover - 외부 연동 에러
                logger.error("Notion 페이지 생성 실패: %s", e)

        if google_docs_client is not None:
            try:
                docs_url = google_docs_client.create_issue_doc(
                    title=title,
                    question=question,
                    answer=answer,
                )
            except Exception as e:  # pragma: no cover - 외부 연동 에러
                logger.error("Google Docs 문서 생성 실패: %s", e)

        extra_links = []
        if notion_url:
            extra_links.append(f"노션 기록: {notion_url}")
        if docs_url:
            extra_links.append(f"Google Docs 기록: {docs_url}")

        final_text = answer
        if extra_links:
            final_text += "\n\n" + "\n".join(extra_links)

        # 내부 지식(txt 기반)에서 컨텍스트를 찾지 못했을 때만, 구글 검색 제안 버튼 노출
        show_google_option = google_search_client is not None and (not context.strip())

        if show_google_option:
            say(
                channel=channel,
                thread_ts=thread_ts,
                text=final_text,
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": final_text},
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "내부 자료에서는 뚜렷한 해결 방법을 찾지 못했어요.\n*구글 검색 결과도 함께 보시겠어요?*",
                        },
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "네, 구글 검색도 보여줘"},
                                "style": "primary",
                                "action_id": "google_search_yes",
                                "value": question[:300],
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "아니요, 괜찮아요"},
                                "action_id": "google_search_no",
                                "value": question[:300],
                            },
                        ],
                    },
                ],
            )
        else:
            say(text=final_text, channel=channel, thread_ts=thread_ts)

    @app.action("google_search_yes")
    def handle_google_search_yes(ack, body, say, logger):  # type: ignore[no-untyped-def]
        ack()
        if google_search_client is None:
            say(text="구글 검색 연동이 설정되어 있지 않습니다. 관리자에게 문의해주세요.")
            return

        action = (body.get("actions") or [{}])[0]
        query = action.get("value") or ""

        container = body.get("container", {}) or {}
        channel_id = container.get("channel_id")
        thread_ts = container.get("thread_ts") or container.get("message_ts")

        try:
            results = google_search_client.search(query=query, max_results=3)
        except Exception as e:  # pragma: no cover - 외부 연동 에러
            logger.error("Google 검색 실패: %s", e)
            say(
                text="구글 검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                channel=channel_id,
                thread_ts=thread_ts,
            )
            return

        if not results:
            say(
                text="구글 검색 결과에서도 특별한 해결 방법을 찾지 못했습니다.",
                channel=channel_id,
                thread_ts=thread_ts,
            )
            return

        lines = ["구글 검색 상위 결과입니다:"]
        for idx, (title, link, snippet) in enumerate(results, start=1):
            lines.append(f"{idx}. <{link}|{title}>\n   {snippet}")

        say(
            text="\n".join(lines),
            channel=channel_id,
            thread_ts=thread_ts,
        )

    @app.action("google_search_no")
    def handle_google_search_no(ack, body, say):  # type: ignore[no-untyped-def]
        ack()
        container = body.get("container", {}) or {}
        channel_id = container.get("channel_id")
        thread_ts = container.get("thread_ts") or container.get("message_ts")
        say(
            text="알겠습니다. 이번에는 내부 자료와 Groq 답변만 참고하겠습니다.",
            channel=channel_id,
            thread_ts=thread_ts,
        )

    # 필요시 DM, 슬래시 커맨드 등으로 확장 가능

    # Socket Mode 실행을 위해 app_token을 보관
    app._app_token = app_token  # type: ignore[attr-defined]
    return app


def main() -> None:
    app = create_app()
    app_token = getattr(app, "_app_token")  # type: ignore[attr-defined]
    logger.info("Starting Slack bot in Socket Mode...")
    handler = SocketModeHandler(app, app_token)
    handler.start()


if __name__ == "__main__":
    main()

