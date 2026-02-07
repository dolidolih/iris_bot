# CI/CD Deployment Guide (배포 가이드)

이 문서는 Yoonmini Bot의 CI/CD 파이프라인(자동 배포)을 사용하기 위해 필요한 설정과 사용법을 설명합니다.

## 1. 사전 준비 (필수 설정)
배포가 정상적으로 작동하려면 GitHub Repository에 **Secrets**가 등록되어야 합니다.
GitHub 저장소의 `Settings` > `Secrets and variables` > `Actions` 메뉴에서 `New repository secret`을 클릭하여 아래 항목들을 추가해 주세요.

| Secret Name (키 이름) | Value (값 예시) | 설명 |
| :--- | :--- | :--- |
| **`DOCKER_USERNAME`** | `myusername` | Docker Hub 아이디 |
| **`DOCKER_PASSWORD`** | `********` | Docker Hub 비밀번호 (또는 Access Token) |
| **`HOST`** | `123.45.67.89` | 배포할 서버의 IP 주소 |
| **`USERNAME`** | `ubuntu` | 서버 접속 SSH 계정명 (root 등) |
| **`KEY`** | `-----BEGIN RSA...` | SSH Private Key 내용 전체 (pem 파일 내용) |
| **`IRIS_URL`** | `ws://127.0.0.1:3000` | 봇이 접속할 웹소켓 주소 (서버 로컬 주소 사용 가능) |
| **`PORT`** | `22` | (선택) SSH 포트. 기본값 22라면 생략 가능 |

## 2. 자동 배포 작동 원리
설정이 완료되면, 별도의 명령어를 실행할 필요가 없습니다.

1.  **코드 수정**: 로컬에서 코드를 수정합니다.
2.  **커밋 & 푸시**: `main` 브랜치로 코드를 푸시합니다. (`git push origin main`)
3.  **자동 실행**:
    *   GitHub Actions가 자동으로 코드를 테스트(Build)합니다.
    *   문제가 없으면 Docker 이미지를 만들어 Docker Hub에 올립니다.
    *   서버에 접속하여 옛날 봇을 끄고 **새로운 버전의 봇을 실행**합니다.

## 3. 로그 확인 방법
배포된 봇이 잘 실행되고 있는지 서버에서 확인하려면:
```bash
# 서버 접속 후
docker logs -f yoonmini-bot
```
문제가 발생하면 GitHub의 **Actions** 탭에서 어느 단계에서 실패했는지 로그를 볼 수 있습니다.
