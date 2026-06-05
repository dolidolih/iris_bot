# 고세오름봇 (koseioreum-bot) 아키텍처 문서

> 최종 업데이트: 2026-05-29

---

## 개요

카카오톡 오픈채팅방 **고세오름** 커뮤니티를 위한 자동화 봇.  
갤럭시 폰에서 실행 중인 [Iris](https://github.com/iris-server/iris) 앱이 카카오톡 DB를 HTTP/WebSocket API로 노출하고,  
이 봇이 Raspberry Pi(crocs)에서 해당 API에 연결해 메시지를 처리한다.

---

## 인프라 구성

```
갤럭시 S8 (Iris 앱)
  └─ KakaoTalk DB 읽기/쓰기
  └─ HTTP + WebSocket 서버 :3000
  └─ Tailscale IP: 100.94.167.89
         │
         │ WebSocket (ws://)
         ▼
Raspberry Pi (crocs) — Tailscale IP: 100.112.70.122
  └─ Python 봇 (irispy.py)
  └─ SQLite DB (koseioreum.sqlite3)
  └─ systemd user service로 자동 실행
         │
         ├─ Open-Meteo API (날씨, 키 없음)
         └─ Google Sheets CSV (참석 데이터)
```

### 핵심 설계 원칙
- Iris 앱이 카카오톡 알림을 감지 → WebSocket으로 이벤트 푸시
- 봇은 이벤트를 받아 처리 후 Iris HTTP API로 답장 전송
- 멤버 상태/닉네임 이력은 로컬 SQLite에 영구 보관
- Tailscale VPN으로 연결 — 공인 IP 불필요, 포트 포워딩 없음

---

## 디렉토리 구조

```
iris_bot/
├── irispy.py                      # 메인 봇 진입점, 이벤트 핸들러, 명령어 라우팅
├── iris.sh                        # 수동 시작/정지 스크립트 (레거시, systemd 권장)
├── koseioreum.sqlite3             # 멤버/닉네임 이력 DB (WAL 모드)
├── bot.log                        # 봇 로그 (logrotate: 7일 보관)
├── bots/
│   ├── koseioreum_store.py        # SQLite CRUD, 통계 메시지 빌더
│   ├── detect_nickname_change.py  # 닉네임 변경 감지 (백그라운드 스레드)
│   ├── attendance.py              # Google Sheets 참석 조회/순위 (1시간 캐시)
│   ├── weather.py                 # Open-Meteo 날씨 조회 (API 키 불필요)
│   └── random_mountain.py        # 수도권 35개 산 데이터 + 랜덤 추천
├── helper/
│   └── __init__.py
├── cache/                         # Google Sheets CSV 캐시 (1시간 TTL)
├── res/                           # 이미지 리소스
└── requirements.txt
```

---

## 실행 환경

| 항목 | 값 |
|------|-----|
| 런타임 | Python 3.13.5 |
| 가상환경 | `/home/alekjin/koseioreum-bot/.venv` |
| Iris URL | `http://100.94.167.89:3000` (Tailscale 고정 IP) |
| 프로세스 관리 | systemd user service (`koseioreum-bot.service`) |
| DB | SQLite (WAL 모드, `koseioreum.sqlite3`) |
| 외부 API | Open-Meteo (날씨), Google Sheets CSV (참석) |
| 의존성 | `irispy-client`, `pandas`, `requests`, `pytz` |

### systemd 서비스 관리

```bash
systemctl --user start koseioreum-bot.service
systemctl --user stop koseioreum-bot.service
systemctl --user restart koseioreum-bot.service
systemctl --user status koseioreum-bot.service

# 로그 확인
tail -f ~/koseioreum-bot/iris_bot/bot.log
```

---

## 감시 채팅방

| 변수 | 채팅방 | 역할 |
|------|--------|------|
| `WATCH_CHAT_ID` | 고세오름 전체방 | 메인 활동 공간 |
| `REAL_NAME_CHAT_ID` | 고세오름 실명방 | 본명 기반 인증 채팅방 |
| `ALERT_CHAT_ID` | 관리자 채팅방 | 봇 알림 및 관리자 명령어 전용 |

---

## 닉네임 형식 규칙

### 전체방 (`WATCH_CHAT_ID`)
```
닉네임/나이/지역/학교/성별
예: 헿헿/93/강남/연대/남
```
- 학교: `연대` 또는 `고대`만 허용
- 성별: `남` 또는 `여`만 허용

### 실명방 (`REAL_NAME_CHAT_ID`)
```
본명/나이/지역/닉네임
예: 김진우/93/강남/헿헿
```
- `nickname_part`는 **마지막 세그먼트** (닉네임)
- `!참가`, `!참석순위` 등에서 닉네임 자동 추출 시 4번째 파트 사용

---

## 명령어 목록

### `!명령어` 실제 출력 (일반 방)

```
[오름봇] 📖 사용 가능한 명령어

👥 !통계          현재원 인원 통계
💬 !통계_대화     최근 30일 대화 통계
🏔️ !참석 [닉네임] 산행 참석 횟수 조회
🏆 !참석순위/!참가순위  2026-1 참석 순위 (Top 5)
🎲 !랜덤          오늘의 추천 산
⛅ !날씨 [산이름] 산 날씨 예보 (오늘~모레)
📖 !명령어        이 도움말
```

### `!명령어` 실제 출력 (관리자 방 추가 표시)

```
── 관리자 전용 ──
📊 !통계_전체     실명 포함 전체 통계
➕ !인원추가 닉네임  멤버 수동 추가
➖ !인원제거 닉네임  멤버 수동 제거
🔄 !싱크_전체     전체방 카카오 DB 동기화
🔄 !싱크_실명     실명방 카카오 DB 동기화
```

### 명령어 상세

| 명령어 | 설명 | 비고 |
|--------|------|------|
| `!명령어` \| `!도움말` \| `!help` | 사용 가능한 명령어 목록 | |
| `!통계` | 현재원 인원 통계 (나이/학교/성별/지역 분포) | |
| `!통계_대화` | 최근 30일 대화 통계 + 실명방 통계 | 2개 메시지 분리 전송 |
| `!참석 [닉네임]` | Google Sheets 기반 산행 참석 횟수 조회 | 파라미터 없으면 발신자 자동 추출 |
| `!참가` \| `!출석` | `!참석`과 동일 | |
| `!참석순위` \| `!참가순위` | 2026-1 시즌 참가/모임장 순위 Top 5 + 본인 순위 | 공동 순위 처리, Google Sheets 캐시 |
| `!랜덤` | 오늘의 추천 산 (수도권 35개 중 랜덤) | |
| `!날씨 [산이름]` | 해당 산 오늘~모레 3일 날씨 예보 | 인기명산 299개, 부분 일치 검색 |

> **`!참석` 닉네임 자동 추출 규칙:**
> - 전체방: 발신자 닉네임 첫 번째 파트 (`헿헿/93/...` → `헿헿`)
> - 실명방: 발신자 닉네임 네 번째 파트 (`김진우/93/강남/헿헿` → `헿헿`)

> **`!날씨` 조회 가능한 산:**  
> 한국 인기명산 299개 (지리산, 설악산, 북한산, 한라산 등).  
> `bots/weather.py`의 `MOUNTAIN_COORDS`에 정의. 이름 부분 일치 검색 지원.

---

## 메시지 출력 예시

### 입장 환영 (형식 정상)
```
[오름봇] 🎉 헿헿님, 환영합니다!
```

### 입장 환영 (형식 오류)
```
[오름봇] 👋 헿헿님, 환영합니다!
⚠️ 닉네임에 문제가 있어요. 확인 후 수정해주세요.

• 학교는 연대 또는 고대만 허용됩니다.

📋 형식: 닉네임/나이/지역/학교/성별
✏️ 예시: 헿헿/93/강남/연대/남
```

### 닉네임 변경 감지 (관리자 채팅방)
```
[🔔 고세오름 닉네임 변경]
✏️ 김정민 → 이안/96/서울/연대/여
✅ 형식: 정상
✅ 중복: 없음
ㄴ[26-05-29 15:00] 이안/96/서울/연대/여
ㄴ[26-03-10 11:23] 김정민/96/서울/연대/여
```

### `!통계`
```
[오름봇] 👥 고세오름 현재원 통계
현재원: 289명  |  실명방: 125명
✅ 형식 정상: 280명  ⚠️ 오류: 9명
실명방 ✅ 122명  ⚠️ 3명

📅 나이
- 93: 15명 (5.4%)
...

🏫 학교
- 연대: 210명 (74.7%)
- 고대: 71명 (25.3%)

🚻 성별
- 남: 160명 (57.0%)
- 여: 121명 (43.0%)

📍 지역
- 강남: 45명 (16.0%)
...
```

### `!통계_대화`
```
[오름봇] 💬 고세오름 대화 통계
📅 기간: 최근 30일  |  💌 4823개

🏆 대화 순위
1. 헿헿: 144개
2. 백곰: 132개
...

📊 요일별
월 | ██████ 612
...

🕐 시간대별
22 | ████████ 401
...

🗓 요일×시간 히트맵
    00 03 06 09 12 15 18 21
월 |   . . - = + * # %
...
```

### `!참석 헿헿`
```
[오름봇] 🏔️ 헿헿님의 참석 현황

📋 2025-2: 참가 5회 / 모임장 1회
📋 2026-1: 참가 3회

🎯 합계: 참가 8회 / 모임장 1회
```

### `!참석순위` / `!참가순위`
```
[오름봇] 🏆 2026-1 참석 순위

⛰️ 참가 순위 (Top 5)
  1. 헿헿: 8회
  2. 백곰: 7회
  3. 이안: 7회
  4. 하늘: 5회
  5. 별빛: 4회
  ···
  9. 김진우: 2회 (내 순위)

🎤 모임장 순위 (Top 5)
  1. 헿헿: 3회
  2. 백곰: 2회
```

> **공동 순위 처리**: 동점자는 같은 등수 부여 (standard competition ranking).  
> 예: 7회 동점 2명 → 둘 다 2등, 다음 사람은 4등.  
> **본인이 5등 이내**: 별도 표시 없음 (이미 Top 5에 포함).  
> **본인이 6등 이하**: `···` 구분선 후 본인 등수만 추가 표시.

### `!날씨 북한산`
```
[오름봇] ⛰️ 북한산 날씨

📅 오늘 (2026-05-29)
  ☁️ 흐림
  🌡 10°C ~ 22°C
  ☔ 강수확률 0%  💨 최대 14km/h

📅 내일 (2026-05-30)
  ☁️ 흐림
  🌡 9°C ~ 23°C
  ☔ 강수확률 0%  💨 최대 14km/h

📅 모레 (2026-05-31)
  🌤 대체로 맑음
  🌡 10°C ~ 25°C
  ☔ 강수확률 0%  💨 최대 13km/h
```

---

## 자동 감지 기능

### 닉네임 변경 감지 (`detect_nickname_change.py`)
- 백그라운드 스레드에서 **10초 간격**으로 전체방/실명방 폴링
- 변경 감지 시:
  1. 관리자 채팅방에 `[🔔 닉네임 변경]` 알림 (이력 + 중복 여부 포함)
  2. 해당 채팅방에 `[오름봇] ✏️` 형식 검사 결과 알림
- 닉네임 히스토리 최대 10개까지 SQLite에 보관

### 입장/퇴장 감지 (`irispy.py`)
- `new_member` 이벤트: DB에 멤버 추가, `🎉` / `👋` 환영 메시지 전송
- `del_member` 이벤트: DB에서 멤버 비활성화 처리

---

## DB 스키마

### `current_members`
```sql
CREATE TABLE current_members (
    chat_id     TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    nickname    TEXT NOT NULL DEFAULT '',
    active      INTEGER NOT NULL DEFAULT 1,  -- 1: 현재원, 0: 퇴장
    joined_at   TEXT,
    left_at     TEXT,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
```

### `nickname_history`
```sql
CREATE TABLE nickname_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    nickname    TEXT NOT NULL DEFAULT '',
    changed_at  TEXT NOT NULL
);
```

> SQLite WAL 모드 + `PRAGMA synchronous=NORMAL` 적용으로 멀티스레드 안전

---

## 외부 데이터 연동

### 참석 조회 / 순위 (`attendance.py`)

Google Sheets 공개 CSV 엔드포인트를 파싱한다.

| 시즌 | Sheet ID |
|------|----------|
| 2025-2 | `1J4ErATN6Jnpj5_pc58a-IculN5kn5BAW3PmMvu0e1Ls` |
| 2026-1 | `1IiBwx_Hto-ZJ4UYhbF786bG7mDhNXfmciGCHam9VP6Q` |

- **캐시**: `cache/attendance_{sheet_id}.csv`에 저장, **1시간 TTL**
- `get_attendance(nickname)` — 개인 참석 횟수 조회 (전 시즌)
- `get_attendance_ranking(season, requester)` — 지정 시즌 순위 (기본값 `2026-1`)
  - 참가/모임장 각각 Top 5 반환
  - 전체 목록 기준 공동 순위(standard competition ranking) 계산
  - `requester` 닉네임 전달 시 해당 인원의 순위/횟수 포함

### 날씨 조회 (`weather.py`)

[Open-Meteo](https://open-meteo.com/) API 사용 — **무료, API 키 불필요.**

```
GET https://api.open-meteo.com/v1/forecast
    ?latitude={lat}&longitude={lon}
    &daily=weathercode,temperature_2m_max,temperature_2m_min,
           precipitation_probability_max,windspeed_10m_max
    &timezone=Asia/Seoul&forecast_days=3
```

- **`MOUNTAIN_COORDS`**: 한국 인기명산 299개의 (위도, 경도, 고도) 하드코딩
  - 출처: 산림청 공식 인기명산 300 목록 (엑셀) + OSM 정상봉 좌표 검증
  - 동명이산 처리: 설악산→대청봉, 지리산→천왕봉, 북한산→백운대 등 정상봉 기준
  - 고도 정보는 공식 목록 기준
- 산 이름 부분 일치 검색 지원 (`_find_mountain`)
- WMO 날씨 코드 → 한국어 이모지 변환 (`WMO_CODES`)

---

## 주요 설계 결정 및 이슈 해결 이력

### 연결 불안정 문제 해결
- **원인**: `IRIS_URL`이 로컬 IP(`192.168.0.6`)로 고정 → 갤럭시 WiFi 재접속 시 IP 변경으로 연결 끊김
- **해결**: Tailscale IP(`100.94.167.89`)로 변경 — 네트워크 무관 고정

### 재부팅 후 봇 미실행 문제 해결
- **원인**: `nohup` 기반 수동 실행 → crocs 재부팅 시 봇 죽음
- **해결**: systemd user service 등록, `loginctl enable-linger alekjin`

### 과도한 DB 쓰기 문제 해결
- **원인**: 닉네임 변경 없어도 전 멤버에 10초마다 UPDATE 실행
- **해결**: 실제 변경 시에만 `update_member_nickname` 호출

### ban/admin 체크 성능 문제 해결
- **원인**: 모든 메시지에 `PyKV.get('ban')` HTTP 요청
- **해결**: 60초 TTL 인메모리 캐시로 대체

### PyKV 마이그레이션 중복 호출 해결
- **원인**: 봇 시작 때마다 마이그레이션 API 호출
- **해결**: SQLite에 데이터 있으면 즉시 스킵

### 날씨 산 데이터 교체 (2026-05-29)
- **원인**: OpenStreetMap Overpass API로 수집한 8,718개 데이터에 동명이산 오매칭, 고도 오류 다수 발생
- **해결**: 산림청 공식 인기명산 300 목록(엑셀)을 기준으로 299개로 교체
  - OSM Overpass API로 한국 전체 peak 배치 조회
  - 도/시 bounding box + 고도 기준으로 정상봉 정밀 매칭
  - 설악산(대청봉), 지리산(천왕봉), 북한산(백운대) 등 주요 국립공원 봉우리 alias 처리
  - 19개 OSM 미발견 + 33개 고도 오류 산 수동 정밀 처리

### 참석순위 명령어 개선 (2026-05-29)
- **이전**: 전 시즌(2025-2, 2026-1) 모두 표시, Top 15, 메달 이모지(🥇🥈🥉), 본인 순위 미표시
- **이후**:
  - `!참가순위` alias 추가
  - **2026-1 시즌만** 표시
  - **Top 5**만 표시 + 숫자 순위(`1. 2. 3.`)
  - **공동 순위** 처리: 동점자 같은 등수 (standard competition ranking)
  - **본인 순위 자동 표시**: 5등 이내면 포함, 6등 이하면 `···` 구분선 후 추가
  - 발신자 닉네임 자동 추출 (전체방/실명방 규칙 동일하게 적용)
  - 섹션 아이콘: ⛰️ 참가 순위 / 🎤 모임장 순위

---

## 파일별 역할 요약

| 파일 | 역할 |
|------|------|
| `irispy.py` | 이벤트 핸들러, 명령어 라우팅, 봇 진입점 |
| `bots/koseioreum_store.py` | SQLite CRUD, 멤버 관리, 통계 메시지 빌더 |
| `bots/detect_nickname_change.py` | 닉네임 변경 폴링 (백그라운드 스레드) |
| `bots/attendance.py` | Google Sheets 참석 조회 + 순위 + 캐시 |
| `bots/weather.py` | Open-Meteo 날씨 조회, 인기명산 299개 좌표 DB |
| `bots/random_mountain.py` | 수도권 35개 산 데이터 + 랜덤 추천 |
| `iris.sh` | 레거시 수동 실행 스크립트 |
| `koseioreum.sqlite3` | 멤버 상태 + 닉네임 이력 영구 저장 |
| `cache/` | Google Sheets CSV 캐시 (1시간 TTL) |

---

## 확장 시 고려사항

- **새 명령어 추가**: `irispy.py`의 `on_message` match-case에 케이스 추가 + `cmd_help` 문자열도 동기화
- **새 자동 감지 추가**: `detect_nickname_change.py`의 `_poll_room` 또는 별도 스레드
- **새 채팅방 감시 추가**: `koseioreum_store.py`의 `WATCHED_ROOMS` 리스트에 추가
- **날씨 조회 산 추가/수정**: `bots/weather.py`의 `MOUNTAIN_COORDS`에 `"산이름": (위도, 경도, 고도)` 수정
- **참석 시즌 전환**: `bots/attendance.py`의 `get_attendance_ranking` 기본값 `season` 변경 + `irispy.py`의 `send_attendance_ranking` 호출 인자 변경
- **Google Sheets 시즌 추가**: `bots/attendance.py`의 `SHEETS` 딕셔너리에 `"시즌명": "sheet_id"` 추가
- **Iris 연결 URL 변경**: systemd service `ExecStart` 수정 (`iris.sh`는 레거시)
