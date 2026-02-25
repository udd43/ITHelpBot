## ITHelpBot – Slack + Groq 지식 봇

`ITHelpBot`은 사용자가 작성한 `.txt` 파일을 지식 베이스로 삼아, Groq LLM을 통해 슬랙에서 각종 IT 관련 질문에 답변하는 봇입니다.

### 1. 준비 사항

- Python 3.10 이상
- Groq API 키
- Slack 워크스페이스와 앱 생성 권한

### 2. 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 만들고, `.env.example`을 참고해 값을 채웁니다.

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_APP_TOKEN=xapp-...

GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant

KNOWLEDGE_DIR=knowledge
MAX_CONTEXT_CHARS=6000
```

### 4. knowledge 폴더에 txt 지식 추가

프로젝트 루트에 `knowledge/` 폴더를 만들고, 알고 있는 내용을 `.txt` 파일로 자유롭게 추가합니다.

예시:

```text
knowledge/
  - web_basic.txt
  - python_tips.txt
  - infra_notes.txt
```

봇은 시작 시 이 폴더의 모든 `.txt` 파일을 읽어서 내부 메모리에 로드합니다.

### 5. Slack 앱 설정 개요

Slack 관리 페이지에서 앱을 하나 생성한 뒤, 대략 다음을 설정합니다.

- OAuth & Permissions
  - `chat:write`, `app_mentions:read`, `channels:history` 등의 권한
- Event Subscriptions
  - `app_mention` 이벤트 구독
- Socket Mode
  - Socket Mode 활성화 후 App-Level Token 생성 (`xapp-...`)

자세한 설정 방법은 Slack 공식 문서(Events API + Socket Mode)를 참고하세요.

### 6. 실행

```bash
python app.py
```

정상적으로 실행되면, 슬랙 채널에서 봇을 워크스페이스에 추가한 뒤 다음과 같이 사용합니다.

```text
@봇이름 파이썬 가상환경 정리해줘
```

봇은 `knowledge/`에 있는 `.txt` 내용을 검색해서 관련된 문맥을 Groq에 넘기고, 그 결과를 한국어로 답변합니다.

