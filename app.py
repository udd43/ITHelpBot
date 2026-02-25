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

        say(text=answer, channel=channel, thread_ts=thread_ts)

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

