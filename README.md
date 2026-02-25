## ITHelpBot – Slack + Groq 지식 봇

`ITHelpBot`은 사용자가 작성한 `.txt` 파일을 지식 베이스로 삼아, Groq LLM을 통해 슬랙에서 각종 IT 관련 질문에 답변하는 봇입니다.

### 1. 준비 사항

- Python 3.10 이상
- Groq API 키
- Slack 워크스페이스와 앱 생성 권한
- (선택) Notion API 사용 권한 및 데이터베이스
- (선택) Google Cloud 서비스 계정 및 Google Docs/Drive API 활성화
- (선택) Google Custom Search API 사용을 위한 API 키 및 검색 엔진 ID

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

# (선택) Notion 연동
NOTION_API_KEY=secret_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id

# (선택) Google Docs 연동
GOOGLE_SERVICE_ACCOUNT_JSON=service-account.json
GOOGLE_DOCS_PARENT_FOLDER_ID=your_google_drive_folder_id

# (선택) Google 검색 연동 (Custom Search API)
GOOGLE_SEARCH_API_KEY=your_google_search_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
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

`knowledge/common_issues_ko.txt` 에는 기본적인 사내 IT 자주 발생 이슈 정리가 예시로 들어가 있으니, 회사 상황에 맞게 수정해서 사용하시면 됩니다.

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
@IT헯 VPN 접속이 자꾸 끊기는데 어떻게 해야 해?
```

봇은 `knowledge/`에 있는 `.txt` 내용을 검색해서 관련된 문맥을 Groq에 넘기고, 그 결과를 한국어로 답변합니다.

Notion/Google Docs 연동이 설정되어 있으면, 매 질문/답변이 자동으로 노션 페이지와 구글 독스 문서로도 기록되고, 슬랙 답변 하단에 링크가 함께 표시됩니다.

만약 로컬 txt/노션/구글 독스에서 뚜렷한 해결 방법을 찾지 못한 경우에는, 답변과 함께

> 내부 자료에서는 뚜렷한 해결 방법을 찾지 못했어요.  
> **구글 검색 결과도 함께 보시겠어요?**

라는 문구와 함께 두 개의 버튼이 나타납니다.

- **네, 구글 검색도 보여줘**: Google Custom Search API를 통해 상위 검색 결과(제목/링크/요약)를 같은 스레드에 추가로 보여줍니다.
- **아니요, 괜찮아요**: 추가 검색 없이 내부 자료와 Groq 답변만 참고하도록 합니다.

