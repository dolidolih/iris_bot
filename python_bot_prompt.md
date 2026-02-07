**[역할]**
너는 시스템 트레이딩의 알림 봇(Python) 개발자야.

**[상황]**
메인 트레이딩 엔진(Java/Spring Boot)에서 매매가 체결되면 **Redis Pub/Sub** 채널로 알림 메시지를 발행하도록 기능이 추가되었어.
이제 파이썬 봇에서 이 Redis 채널을 구독(Subscribe)하고 있다가, 메시지가 오면 실시간으로 사용자에게(디스코드 등) 알람을 보내는 기능을 구현해야 해.

**[요구 사항]**
아래 명세에 맞춰 Redis Subscriber 로직을 구현해줘.

1.  **Redis 연결 설정:**
    *   기존 Redis 설정을 활용하되, 별도의 비동기 리스너(Thread 또는 asyncio)로 돌아가야 해. (메인 봇 로직 차단 금지)

2.  **구독 정보 (Protocol):**
    *   **Channel Name:** `trade:alarm:evt`
    *   **Data Format:** JSON String
    *   **Payload 예시:**
        ```json
        {
          "symbol": "BTCUSDT",
          "price": 98000.5,
          "quantity": 0.005,
          "side": "BUY",   // or "SELL"
          "timestamp": 1707312345.123 // or ISO String
        }
        ```

3.  **동작 로직:**
    *   봇이 실행되면 해당 채널을 `subscribe` 한다.
    *   메시지 수신 시 JSON을 파싱한다.
    *   파싱된 데이터를 이용해 보기 좋은 포맷(예: "📈 [매수 체결] BTCUSDT @ $98,000.5 (0.005개)")으로 변환한다.
    *   변환된 메시지를 현재 연결된 메신저(디스코드/텔레그램 등)로 즉시 전송한다.

4.  **에러 처리:**
    *   Redis 연결이 끊기거나 JSON 파싱 에러가 발생해도 봇이 죽지 않고, 에러 로그를 남긴 후 재접속/복구 시도를 해야 한다.

위 내용을 바탕으로 `RedisAlarmListener` 클래스(또는 모듈) 코드를 작성해줘.
