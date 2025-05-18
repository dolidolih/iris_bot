
---

# Iris + IrisPy2 기반 샘플 봇

### `2025.05.18 변경사항` :
- 이제 irispy2가 아닌 irispy-client 모듈을 사용합니다. import는 iris로 합니다.
- 기본 venv 디렉토리가 .venv가 아닌 venv로 변경되었습니다.
- iris 커맨드라인 툴을 사용하도록 가이드를 변경하였습니다.
- 더이상 BotManager를 사용하지 않습니다.
- kv는 PyKV() 를 init하면 자동으로 쓰레드 safe한 kv 인스턴스가 반환됩니다.
- 실행파일명이 irispy.py로 변경되었습니다.
- kv의 디폴트 path가 project_root의 iris.db로 변경되었습니다.
- addon이 iris.decorators로 변경되었습니다.
- DatabaseHelper를 삭제하였습니다.
- chat.reply_media() 내 "IMAGE"를 삭제하고 인자를 하나만 받습니다. 인자는 filepath, url, PIL.Image, bytes, BufferedReader 를 모두 지원합니다.

### `2025.04.12 변경사항` : 데코레이터의 불필요한 ()가 제거되었습니다. 기존 사용중인 코드 중 데코레이터를 사용한 코드가 있다면 변경이 필요합니다.

## 초기 설정

1.  **저장소 복제 및 Python 가상 환경 설정:**
    터미널에서 다음 명령어를 실행하세요:
    ```bash
    cd ~
    git clone https://github.com/dolidolih/iris_bot
    cd iris_bot
    python -m venv venv
    
    # 가상 환경 활성화 (Windows의 경우 venv/Scripts/Activate.ps1)
    source venv/bin/activate
    
    pip install -U pip
    pip install -r requirements.txt

    iris init
    ```

2.  **Admin User ID 설정:**
    ```bash
    iris admin add <user_id>
    ```

3.  **KakaoLink 설정(Optional):**
    ```bash
    iris kakaolink <app_key> <origin>
    ```

4.  **서비스 설정(Optional):**
    ```bash
    iris service create
    iris service start/stop/status
    ```

## 환경 변수 설정

몇 가지 환경 변수를 설정해야 합니다. 시스템 환경 변수로 직접 설정하거나, 프로젝트 루트 디렉토리에 `.env` 파일을 생성하여 관리할 수 있습니다.

*   `SECURE_1PSID`, `SECURE_1PSIDTS`: **Imagen3 무료 Web API 이용을 위한 쿠키.**
    *   Google Gemini 웹 인터페이스를 통해 비공식 Imagen3 API를 사용하기 위해 필요합니다.
    *   **얻는 방법:**
        1.  Chrome 브라우저에서 **시크릿 모드**로 새 창을 엽니다.
        2.  [https://gemini.google.com](https://gemini.google.com) 에 방문하여 Google 계정으로 로그인합니다.
        3.  개발자 도구를 엽니다 (F12 키 누름).
        4.  `Application` 탭(일부 브라우저 버전에서는 `Storage` 아래에 있을 수 있음)으로 이동합니다.
        5.  `Storage` -> `Cookies` 아래에서 `https://gemini.google.com` 을 선택합니다.
        6.  이름이 `__Secure-1PSID` 와 `__Secure-1PSIDTS` 인 쿠키를 찾습니다.
        7.  각각의 값을 복사합니다.
        8.  복사한 값을 환경 설정에 붙여넣습니다.
        9.  **중요:** 값을 복사한 후 즉시 시크릿 창을 닫습니다.

*   `GEMINI_KEY`: **Google Gemini API 키.**
    *   공식 Gemini API(예: 텍스트 생성)를 사용하기 위한 키입니다.
    *   무료 또는 유료 키 모두 사용 가능합니다. 무료 키는 분당/일일 사용량 제한이 있습니다.
    *   [Google AI Studio](https://aistudio.google.com/apikey) 에서 키를 발급받으세요.

*   `X_NAVER_CLIENT_ID`, `X_NAVER_CLIENT_SECRET`: **네이버 이미지 검색을 위한 네이버 API 키.**
    *   봇의 네이버 이미지 검색 기능을 위해 필요합니다.
    *   **얻는 방법:**
        1.  [네이버 개발자 센터](https://developers.naver.com/apps/#/list) 로 이동합니다.
        2.  새 애플리케이션을 등록하거나 기존 애플리케이션을 사용합니다.
        3.  애플리케이션 설정에서 "검색" API 사용을 추가하고 활성화합니다.
        4.  애플리케이션 상세 정보에서 `Client ID`와 `Client Secret` 값을 복사합니다.

## 환경 변수 적용 방법

봇을 배포하고 실행하는 방식에 따라 아래 방법 중 **하나**를 선택하세요:

### 1. 직접 실행 (`python` 명령어 사용)

systemd와 같은 서비스 관리자 없이 봇을 직접 실행하는 경우:

1.  쉘 설정 파일을 편집합니다 (Bash의 경우 `~/.bashrc`, Zsh의 경우 `~/.zshrc` 등):
    ```bash
    nano ~/.bashrc
    ```
2.  파일 끝에 다음 줄들을 추가하고, 따옴표 안의 값을 실제 키와 쿠키 값으로 변경하세요:
    ```bash
    export PYTHONUNBUFFERED=1 # Python 앱 로깅 시 권장
    export SECURE_1PSID="YOUR_ACTUAL_1PSID_VALUE"
    export SECURE_1PSIDTS="YOUR_ACTUAL_1PSIDTS_VALUE"
    export GEMINI_KEY="YOUR_ACTUAL_GEMINI_KEY"
    export X_NAVER_CLIENT_ID="YOUR_NAVER_CLIENT_ID"
    export X_NAVER_CLIENT_SECRET="YOUR_NAVER_CLIENT_SECRET"
    ```
3.  파일을 저장하고 (`nano`에서 Ctrl+x y Enter) 편집기를 종료합니다 (Ctrl+X).
4.  `source ~/.bashrc` 명령어를 실행하거나 새 터미널 세션을 시작하여 변경 사항을 적용합니다.

### 2. `systemd` 사용

`systemd` 서비스를 사용하여 봇 프로세스를 관리하는 경우:

*   **`EnvironmentFile` 사용**
    *   환경 변수 파일(예: `/home/YOUR_USER/iris_bot/.env`)에 아래의 내용을 포함시킵니다. **이 파일은 비밀 정보를 포함하므로 안전한 권한(`chmod 600`)을 설정해야 합니다.**
        ```ini
        # /home/YOUR_USER/iris_bot/.env 파일 내용 예시
        PYTHONUNBUFFERED=1
        SECURE_1PSID="YOUR_ACTUAL_1PSID_VALUE"
        SECURE_1PSIDTS="YOUR_ACTUAL_1PSIDTS_VALUE"
        GEMINI_KEY="YOUR_ACTUAL_GEMINI_KEY"
        X_NAVER_CLIENT_ID="YOUR_NAVER_CLIENT_ID"
        X_NAVER_CLIENT_SECRET="YOUR_NAVER_CLIENT_SECRET"
        ```

### 3. Docker 사용

봇을 Docker 컨테이너 내부에서 실행하는 경우:

*   **옵션 A: `docker run` 시 `--env-file` 사용**
    *   키-값 쌍으로 환경 변수 파일(예: `./docker.env`)을 생성합니다 (systemd 예시와 동일한 형식).
    *   컨테이너를 실행합니다:
        ```bash
        docker run -d --name iris-bot --env-file ./docker.env YOUR_BOT_IMAGE_NAME
        ```
*   **옵션 B: `docker run` 시 `-e` 플래그 사용**
    ```bash
    docker run -d --name iris-bot \
      -e PYTHONUNBUFFERED=1 \
      -e SECURE_1PSID="YOUR_ACTUAL_1PSID_VALUE" \
      -e SECURE_1PSIDTS="YOUR_ACTUAL_1PSIDTS_VALUE" \
      -e GEMINI_KEY="YOUR_ACTUAL_GEMINI_KEY" \
      -e X_NAVER_CLIENT_ID="YOUR_NAVER_CLIENT_ID" \
      -e X_NAVER_CLIENT_SECRET="YOUR_NAVER_CLIENT_SECRET" \
      YOUR_BOT_IMAGE_NAME
    ```
*   **옵션 C: `docker-compose.yml` 사용**
    *   `environment` 또는 `env_file`을 사용하여 환경 변수를 정의합니다:
    ```yaml
    version: '3.8'
    services:
      iris_bot:
        image: YOUR_BOT_IMAGE_NAME
        container_name: iris-bot
        restart: always
        # 옵션 C.1: env_file 사용
        env_file:
          - ./docker.env # docker-compose.yml 파일 기준 상대 경로
        # 옵션 C.2: environment 블록 사용
        # environment:
        #   PYTHONUNBUFFERED: 1
        #   SECURE_1PSID: "YOUR_ACTUAL_1PSID_VALUE"
        #   SECURE_1PSIDTS: "YOUR_ACTUAL_1PSIDTS_VALUE"
        #   GEMINI_KEY: "YOUR_ACTUAL_GEMINI_KEY"
        #   X_NAVER_CLIENT_ID: "YOUR_NAVER_CLIENT_ID"
        #   X_NAVER_CLIENT_SECRET: "YOUR_NAVER_CLIENT_SECRET"
        # 필요한 경우 볼륨이나 포트 추가
        # volumes:
        #   - .:/app
    ```

---