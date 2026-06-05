#!/bin/bash
# =============================================
# 고세오름봇 시작/정지 스크립트
# 사용법: ./start.sh {start|stop|restart|status}
# =============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
VENV="$SCRIPT_DIR/../.venv"
PID_FILE="$BOT_DIR/bot.pid"
LOG_FILE="$BOT_DIR/bot.log"

# === Iris URL 설정 ===
# iris init 후 표시되는 URL을 여기에 입력하세요
IRIS_URL="http://100.94.167.89:3000"
# ====================

_is_running() {
    [ -f "$PID_FILE" ] || return 1
    local pid
    pid=$(cat "$PID_FILE")
    kill -0 "$pid" 2>/dev/null
}

start() {
    if _is_running; then
        echo "이미 실행 중입니다. (PID: $(cat "$PID_FILE"))"
        exit 1
    fi

    if [ ! -f "$VENV/bin/activate" ]; then
        echo "가상환경을 찾을 수 없습니다: $VENV"
        exit 1
    fi

    echo "봇을 시작합니다..."
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    cd "$BOT_DIR" || exit 1

    PYTHONUNBUFFERED=1 nohup python -u irispy.py "$IRIS_URL" >> "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"

    sleep 1
    if _is_running; then
        echo "시작 완료. (PID: $pid)"
        echo "로그: $LOG_FILE"
    else
        echo "시작 실패. 로그를 확인하세요: $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

stop() {
    if ! _is_running; then
        echo "실행 중이 아닙니다."
        rm -f "$PID_FILE"
        return
    fi

    local pid
    pid=$(cat "$PID_FILE")
    echo "정지합니다. (PID: $pid)"
    kill "$pid"

    local count=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 1
        count=$((count + 1))
        if [ "$count" -ge 10 ]; then
            echo "강제 종료합니다..."
            kill -9 "$pid"
            break
        fi
    done

    rm -f "$PID_FILE"
    echo "정지 완료."
}

restart() {
    stop
    sleep 1
    start
}

status() {
    if _is_running; then
        echo "실행 중. (PID: $(cat "$PID_FILE"))"
    else
        echo "실행 중이 아닙니다."
    fi
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    *)
        echo "사용법: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
