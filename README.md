# DASH: Dormitory Access System Hub 
Google Sheets + Google Chat 자동화 기반 외출입 관리 시스템

---

## 📖 개요
이 프로그램은 **ID카드 리더기를 사용하거나 수동 입력을 하여서**,  
Google 스프레드시트에 출입 상태를 자동 기록하고  
Google Chat Webhook으로 알림을 전송하는 시스템입니다.

**주요 기능**
- Google Sheets를 통한 실시간 출입 로그 관리  
- Google Chat Webhook 알림 전송  
- gTTS 기반 한국어 음성 출력  
- threading 기반 비동기 로깅  

---

## 🧩 파일 구조
```
project/
├── main.py                  # 실행 파일
├── settings.py              # 설정 파일
├── service_account.json      # 구글 서비스 계정 키
└── requirements.txt          # 필요한 라이브러리 목록
```

---

## ⚙️ 사전 준비

### 1️⃣ Google Cloud에서 service_account.json 발급하기
1. [Google Cloud Console](https://console.cloud.google.com/) 접속  
2. 새 프로젝트 생성  
3. **APIs & Services → Library**로 이동  
   - “Google Sheets API” 활성화  
   - “Google Drive API” 활성화  
4. **APIs & Services → Credentials → Create credentials → Service account** 선택  
   - 서비스 계정 생성 후 “JSON 키” 다운로드  
   - 이름을 `service_account.json`으로 변경 후 프로젝트 폴더에 저장  
5. 생성된 서비스 계정 이메일(예: `example@project.iam.gserviceaccount.com`)을 복사하여  
   사용하는 **Google 스프레드시트의 공유 설정 → 편집자 권한으로 추가**해야 합니다.

---

### 2️⃣ 스프레드시트 키 얻기
스프레드시트 URL 예시:
```
https://docs.google.com/spreadsheets/d/1AbCdEfGhIJkLMNOPqrstuVWxyz1234567890/edit#gid=0
```
여기서 `/d/` 와 `/edit` 사이의 문자열이 스프레드시트 키입니다:
```
1AbCdEfGhIJkLMNOPqrstuVWxyz1234567890
```
이 값을 `settings.스프레드시트_키` 변수에 입력합니다.

---

### 3️⃣ Google Chat Webhook 만들기

1. **Google Chat** 열기 → 사용 중인 **스페이스(Space)** 선택  
2. 상단 제목 오른쪽의 `∨` 메뉴 클릭 → **앱 및 통합 관리(Manage apps & integrations)** 선택  
3. **웹훅(Webhooks)** → **구성 추가(Add webhook)** 클릭  
4. 이름은 자유롭게 (예: “EntryExit Logger”) 입력하고, 아이콘은 선택사항  
5. 저장 후 생성된 **Webhook URL**을 복사합니다.  
   예시:
   ```
   https://chat.googleapis.com/v1/spaces/AAAA12345/messages?key=xxxx&token=yyyy
   ```  
6. `settings.py`의 `지챗_웹훅_링크` 리스트에 추가:
   ```python
   지챗_웹훅_링크 = [
       "https://chat.googleapis.com/v1/spaces/AAAA12345/messages?key=xxxx&token=yyyy"
   ]
   ```

---

## 🧰 설치 방법
```bash
pip install gspread google-auth colorama gtts pystyle requests
brew install ffmpeg   # macOS 전용
```

---

## 🚀 실행
```bash
python main.py
```
- 프로그램 시작 시 터미널에 기숙사 이름이 표시됩니다.  
- 카드 ID를 입력하면 출입 상태가 자동으로 토글됩니다.  
- “q” 입력 시 종료됩니다.

---

## 🗂 로그 시트 구조
| 이름 | ID카드 정보 | 상태 | 시간 | 노트 |
|------|--------------|------|------|------|
| 홍길동 | 1234567890 | 출입 | 2025-10-05 13:22:10 |   |

---

## ⚠️ 주의사항
- `service_account.json` 은 절대 외부에 공개하지 마세요.  
- Google Sheets API 호출 한도(Quota)에 유의하세요.
- 지챗 또는 스프레드시트를 사용 안하신다면 settings.py에서 False로 설정해놓으세요
- 지챗 레이트 리밋이 걸릴수 있으니 웹훅은 **2개**이상을 추천합니다.
- Google Chat Webhook URL은 여러 개일 경우 순차적으로 순환 사용됩니다.  

---

Made by 330wns
