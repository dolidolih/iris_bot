import datetime
import logging
import sys
import threading
from zoneinfo import ZoneInfo

from iris import ChatContext, Bot
from iris.bot.models import ErrorContext
from bots.attendance import (
    get_attendance, build_attendance_message,
    get_attendance_ranking, build_attendance_ranking_message,
)
from bots.weather import get_weather_message
from bots.random_mountain import get_random_mountain_message
from bots.koseioreum_store import (
    ALERT_CHAT_ID,
    KoseioreumStore,
    REAL_NAME_CHAT_ID,
    ROOM_ALL,
    ROOM_REAL,
    WATCH_CHAT_ID,
    build_chat_stats_message,
    build_member_stats_message,
    build_nickname_index,
    build_welcome_message,
    duplicate_nicknames_for,
    fetch_members,
    now_kst,
    parse_nickname_for_room,
    parse_koseioreum_nickname,
    parse_real_name_nickname,
)

from iris.kakaolink import IrisLink

from bots.detect_nickname_change import detect_nickname_change


_KST = ZoneInfo("Asia/Seoul")


class _KSTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.datetime.fromtimestamp(record.created, _KST)
        return dt.strftime("%Y-%m-%d %H:%M:%S KST")


def _setup_logging():
    # stdout만 사용 — 파일 기록은 start.sh의 nohup >> bot.log 리다이렉션이 담당
    fmt = _KSTFormatter("[%(asctime)s] %(levelname)s %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


_setup_logging()
log = logging.getLogger(__name__)

iris_url = sys.argv[1]
bot = Bot(iris_url)
koseioreum_store = KoseioreumStore()


def is_admin_chat(chat: ChatContext) -> bool:
    return str(chat.room.id) == str(ALERT_CHAT_ID)


@bot.on_event("message")
def on_message(chat: ChatContext):
    cmd = chat.message.command
    if not cmd or not cmd.startswith("!"):
        return
    try:
        match cmd:
            case "!명령어" | "!도움말" | "!help":
                log.info("CMD !명령어 | room=%s | sender=%s", chat.room.id, chat.sender.name)
                cmd_help(chat)

            case "!통계":
                log.info("CMD !통계 | room=%s | sender=%s", chat.room.id, chat.sender.name)
                send_member_stats(chat, include_names=False)

            case "!통계_전체":
                if is_admin_chat(chat):
                    log.info("CMD !통계_전체 | room=%s | sender=%s", chat.room.id, chat.sender.name)
                    send_member_stats(chat, include_names=True)

            case "!통계_대화":
                log.info("CMD !통계_대화 | room=%s | sender=%s", chat.room.id, chat.sender.name)
                send_chat_stats(chat)

            case "!참석" | "!참가" | "!출석":
                log.info("CMD %s | room=%s | sender=%s", cmd, chat.room.id, chat.sender.name)
                send_attendance(chat)

            case "!랜덤":
                log.info("CMD !랜덤 | room=%s | sender=%s", chat.room.id, chat.sender.name)
                chat.reply(get_random_mountain_message())

            case "!참석순위" | "!참가순위":
                log.info("CMD !참석순위 | room=%s | sender=%s", chat.room.id, chat.sender.name)
                send_attendance_ranking(chat)

            case "!날씨":
                log.info("CMD !날씨 | room=%s | param=%s | sender=%s", chat.room.id, chat.message.param, chat.sender.name)
                send_weather(chat)

            case "!인원추가":
                if is_admin_chat(chat):
                    log.info("CMD !인원추가 | param=%s | sender=%s", chat.message.param, chat.sender.name)
                    cmd_add_member(chat)

            case "!인원제거":
                if is_admin_chat(chat):
                    log.info("CMD !인원제거 | param=%s | sender=%s", chat.message.param, chat.sender.name)
                    cmd_remove_member(chat)

            case "!싱크_전체":
                if is_admin_chat(chat):
                    log.info("CMD !싱크_전체 | sender=%s", chat.sender.name)
                    cmd_sync(chat, WATCH_CHAT_ID, "전체방")

            case "!싱크_실명":
                if is_admin_chat(chat):
                    log.info("CMD !싱크_실명 | sender=%s", chat.sender.name)
                    cmd_sync(chat, REAL_NAME_CHAT_ID, "실명방")

    except Exception as e:
        log.exception("CMD %s 처리 중 오류: %s", cmd, e)


#입장감지
@bot.on_event("new_member")
def on_newmem(chat: ChatContext):
    nickname = chat.sender.name or ""
    chat_id = str(chat.room.id)
    log.info("JOIN | room=%s | nickname=%s", chat_id, nickname)

    if chat_id == WATCH_CHAT_ID:
        room = ROOM_ALL
    elif chat_id == REAL_NAME_CHAT_ID:
        room = ROOM_REAL
    else:
        room = ROOM_ALL

    koseioreum_store.upsert_member(
        chat_id,
        chat.sender.id,
        nickname,
        active=True,
        joined_at=current_event_time(),
        left_at=None,
    )
    koseioreum_store.ensure_history(chat_id, chat.sender.id, nickname, "")

    if chat_id in (WATCH_CHAT_ID, REAL_NAME_CHAT_ID):
        parsed = parse_nickname_for_room(room, nickname)
        members = koseioreum_store.active_members(chat_id)
        nickname_index = build_nickname_index(members, room)
        duplicates = duplicate_nicknames_for({"nickname": nickname}, nickname_index, room)
        message = build_welcome_message(nickname, parsed, duplicates, room)
        chat.api.reply(int(chat_id), message)


#퇴장감지
@bot.on_event("del_member")
def on_delmem(chat: ChatContext):
    nickname = chat.sender.name or ""
    log.info("LEAVE | room=%s | nickname=%s", chat.room.id, nickname)
    koseioreum_store.mark_left(chat.room.id, chat.sender.id, nickname)


def cmd_help(chat: ChatContext):
    lines = [
        "[오름봇] 📖 사용 가능한 명령어",
        "",
        "👥 !통계          현재원 인원 통계",
        "💬 !통계_대화     최근 30일 대화 통계",
        "🏔️ !참석 [닉네임] 산행 참석 횟수 조회",
        "🏆 !참석순위/!참가순위  2026-1 참석 순위 (Top 5)",
        "🎲 !랜덤          오늘의 추천 산",
        "⛅ !날씨 [산이름] 산 날씨 예보 (오늘~모레)",
        "📖 !명령어        이 도움말",
    ]
    if is_admin_chat(chat):
        lines += [
            "",
            "── 관리자 전용 ──",
            "📊 !통계_전체     실명 포함 전체 통계",
            "➕ !인원추가 닉네임  멤버 수동 추가",
            "➖ !인원제거 닉네임  멤버 수동 제거",
            "🔄 !싱크_전체     전체방 카카오 DB 동기화",
            "🔄 !싱크_실명     실명방 카카오 DB 동기화",
        ]
    chat.reply("\n".join(lines))


def send_attendance_ranking(chat: ChatContext):
    sender_nickname = chat.sender.name or ""
    if str(chat.room.id) == REAL_NAME_CHAT_ID:
        parsed = parse_real_name_nickname(sender_nickname)
    else:
        parsed = parse_koseioreum_nickname(sender_nickname)
    requester = parsed.get("nickname_part") or sender_nickname
    data = get_attendance_ranking(season="2026-1", requester=requester)
    chat.reply(build_attendance_ranking_message(data))


def send_weather(chat: ChatContext):
    if not chat.message.has_param or not chat.message.param:
        chat.reply(
            "⚠️ 사용법: !날씨 [산이름]\n"
            "예시: !날씨 북한산\n"
            "예시: !날씨 청계산"
        )
        return
    mountain = chat.message.param.strip()
    chat.reply(get_weather_message(mountain))


def send_attendance(chat: ChatContext):
    if chat.message.has_param and chat.message.param:
        nickname = chat.message.param.strip()
    else:
        sender_nickname = chat.sender.name or ""
        if str(chat.room.id) == REAL_NAME_CHAT_ID:
            parsed = parse_real_name_nickname(sender_nickname)
        else:
            parsed = parse_koseioreum_nickname(sender_nickname)
        nickname = parsed["nickname_part"] or sender_nickname

    if not nickname:
        chat.reply("⚠️ 닉네임을 입력해주세요.\n예시: !참석 헿헿")
        return

    results = get_attendance(nickname)
    message = build_attendance_message(nickname, results)
    chat.reply(message)


def send_member_stats(chat: ChatContext, include_names=False):
    ensure_current_members_seeded(chat, WATCH_CHAT_ID)
    ensure_current_members_seeded(chat, REAL_NAME_CHAT_ID)
    members = koseioreum_store.active_members(WATCH_CHAT_ID)
    real_members = koseioreum_store.active_members(REAL_NAME_CHAT_ID)
    real_name_map, ambiguous, unmatched_real = koseioreum_store.real_name_by_all_user_id()
    message = build_member_stats_message(members, real_name_map, real_members, unmatched_real, include_names=include_names)
    if ambiguous and include_names:
        message += "\n\n⚠ 닉네임 부분 중복으로 본명 매핑 실패: " + ", ".join(ambiguous)
    if include_names:
        # !통계_전체는 관리자방에서만 실행되므로 관리자방으로 답장
        chat.api.reply(ALERT_CHAT_ID, message)
    else:
        # !통계는 명령어를 친 방에 직접 답장
        chat.reply(message)


def send_chat_stats(chat: ChatContext):
    ensure_current_members_seeded(chat, WATCH_CHAT_ID)
    ensure_current_members_seeded(chat, REAL_NAME_CHAT_ID)

    members_all = koseioreum_store.active_members(WATCH_CHAT_ID)
    msg_all = build_chat_stats_message(
        chat, members_all, WATCH_CHAT_ID, title="고세오름 대화 통계"
    )

    members_real = koseioreum_store.active_members(REAL_NAME_CHAT_ID)
    msg_real = build_chat_stats_message(
        chat, members_real, REAL_NAME_CHAT_ID, title="고세오름 실명방 대화 통계"
    )

    chat.reply(msg_all)
    chat.reply(msg_real)


def cmd_add_member(chat: ChatContext):
    if not chat.message.has_param or not chat.message.param:
        chat.api.reply(ALERT_CHAT_ID, "⚠️ 사용법: !인원추가 닉네임/나이/지역/학교/성별")
        return

    full_nickname = chat.message.param.strip()

    # 카톡 DB에서 해당 닉네임 가진 user 검색
    kakao_all = fetch_members(chat.api, WATCH_CHAT_ID)
    match_all = next((m for m in kakao_all.values() if m["nickname"] == full_nickname), None)

    if not match_all:
        chat.api.reply(ALERT_CHAT_ID, f"카톡 DB에 해당 닉네임이 없어요: {full_nickname}")
        return

    user_id = match_all["user_id"]
    koseioreum_store.set_active(WATCH_CHAT_ID, user_id, full_nickname, active=True)
    koseioreum_store.ensure_history(WATCH_CHAT_ID, user_id, full_nickname, "")

    # 실명방에도 같은 user_id가 있으면 활성화
    kakao_real = fetch_members(chat.api, REAL_NAME_CHAT_ID)
    in_real = user_id in kakao_real
    if in_real:
        real_member = kakao_real[user_id]
        koseioreum_store.set_active(REAL_NAME_CHAT_ID, user_id, real_member["nickname"], active=True)
        koseioreum_store.ensure_history(REAL_NAME_CHAT_ID, user_id, real_member["nickname"], "")

    total = len(koseioreum_store.active_members(WATCH_CHAT_ID))
    log.info("ADMIN 인원추가 완료 | nickname=%s | user_id=%s | 실명방=%s | 총원=%d", full_nickname, user_id, in_real, total)
    chat.api.reply(
        ALERT_CHAT_ID,
        f"✅ 추가 완료: {full_nickname}\n"
        f"🆔 {user_id}\n"
        f"🏠 실명방: {'예' if in_real else '아니오'}\n"
        f"👥 총원: {total}명"
    )


def cmd_remove_member(chat: ChatContext):
    if not chat.message.has_param or not chat.message.param:
        chat.api.reply(ALERT_CHAT_ID, "⚠️ 사용법: !인원제거 닉네임/나이/지역/학교/성별")
        return

    full_nickname = chat.message.param.strip()

    # 전체방에서 먼저 검색
    row = koseioreum_store.member_by_full_nickname(WATCH_CHAT_ID, full_nickname)
    if row:
        user_id = row["user_id"]
        koseioreum_store.mark_left(WATCH_CHAT_ID, user_id, full_nickname)

        # 실명방에 같은 user_id가 active이면 함께 제거
        real_members = koseioreum_store.active_members(REAL_NAME_CHAT_ID)
        real_match = next((m for m in real_members if m["user_id"] == user_id), None)
        if real_match:
            koseioreum_store.mark_left(REAL_NAME_CHAT_ID, user_id, real_match["nickname"])

        total = len(koseioreum_store.active_members(WATCH_CHAT_ID))
        log.info("ADMIN 인원제거(전체방) | nickname=%s | 실명방=%s | 총원=%d", full_nickname, bool(real_match), total)
        chat.api.reply(
            ALERT_CHAT_ID,
            f"✅ 제거 완료: {full_nickname}\n"
            f"🏠 실명방: {'예' if real_match else '아니오'}\n"
            f"👥 총원: {total}명"
        )
        return

    # 전체방에 없으면 실명방에서 검색 (실명방 닉네임으로 제거)
    real_row = koseioreum_store.member_by_full_nickname(REAL_NAME_CHAT_ID, full_nickname)
    if real_row:
        user_id = real_row["user_id"]
        koseioreum_store.mark_left(REAL_NAME_CHAT_ID, user_id, full_nickname)
        total = len(koseioreum_store.active_members(WATCH_CHAT_ID))
        log.info("ADMIN 인원제거(실명방) | nickname=%s | 총원=%d", full_nickname, total)
        chat.api.reply(
            ALERT_CHAT_ID,
            f"✅ 실명방 제거 완료: {full_nickname}\n"
            f"👥 총원: {total}명"
        )
        return

    log.warning("ADMIN 인원제거 실패 - DB에 없음 | nickname=%s", full_nickname)
    chat.api.reply(ALERT_CHAT_ID, f"❌ 봇 DB에 없어요: {full_nickname}")


def cmd_sync(chat: ChatContext, target_chat_id: str, label: str):
    kakao_members = fetch_members(chat.api, target_chat_id)
    result = koseioreum_store.reconcile_with_kakao(target_chat_id, kakao_members)

    added_count = len(result["added"])
    left_count = len(result["left"])

    log.info("ADMIN 싱크 | %s | 추가=%d 퇴장=%d", label, added_count, left_count)
    lines = [f"[🔄 {label}] 싱크 완료: ➕{added_count}명 추가, ➖{left_count}명 퇴장"]
    if result["added"]:
        added_nicknames = [kakao_members.get(uid, {}).get("nickname", uid) for uid in result["added"]]
        lines.append("추가: " + ", ".join(added_nicknames))
    if result["left"]:
        lines.append("퇴장: " + ", ".join(result["left"]))

    chat.reply("\n".join(lines))


def ensure_current_members_seeded(chat: ChatContext, chat_id: str):
    if koseioreum_store.active_members(chat_id):
        return
    members = fetch_members(chat.api, chat_id)
    koseioreum_store.seed_members_from_kakao(members)


def current_event_time():
    return now_kst()


@bot.on_event("error")
def on_error(err: ErrorContext):
    log.error("이벤트 오류 | event=%s | %s", err.event, err.exception)


# ── 갤럭시(Iris) 연결 헬스체크 ─────────────────────────────────────────
_CHECK_INTERVAL = 30   # 초
_FAIL_THRESHOLD = 3    # 연속 실패 횟수 (30×3=90초 이상 응답 없으면 알림)


def _connection_monitor():
    """HTTP API를 주기적으로 체크해 연결 이상/복구를 관리자 채팅방에 알림."""
    import time as _time
    fail_count = 0
    alerted = False

    _time.sleep(10)  # 봇 시작 직후 안정화 대기
    while True:
        _time.sleep(_CHECK_INTERVAL)
        try:
            bot.api.get_info()
            if alerted:
                # 연결 복구됨
                log.info("갤럭시(Iris) 연결 복구 감지")
                downtime_min = fail_count * _CHECK_INTERVAL // 60
                try:
                    bot.api.reply(
                        int(ALERT_CHAT_ID),
                        f"[오름봇] ✅ 갤럭시(Iris) 연결이 복구되었습니다.\n"
                        f"(약 {downtime_min}분 동안 연결 끊김)",
                    )
                except Exception:
                    pass
                alerted = False
            fail_count = 0
        except Exception as e:
            fail_count += 1
            log.warning("갤럭시(Iris) 헬스체크 실패 (%d회): %s", fail_count, e)
            if fail_count == _FAIL_THRESHOLD and not alerted:
                alerted = True
                log.error("갤럭시(Iris) 연결 이상 감지 — 관리자 알림 시도")
                try:
                    bot.api.reply(
                        int(ALERT_CHAT_ID),
                        "[오름봇] ⚠️ 갤럭시(Iris)와 연결이 끊어진 것 같습니다.\n"
                        "앱 상태를 확인해주세요.",
                    )
                except Exception:
                    pass  # 연결이 완전히 끊어진 경우 전송 불가 — 복구 시 알림으로 대체


if __name__ == "__main__":
    log.info("=" * 50)
    log.info("고세오름봇 시작")
    log.info("=" * 50)

    nickname_detect_thread = threading.Thread(
        target=detect_nickname_change,
        args=(bot,),
        daemon=True,
    )
    nickname_detect_thread.start()

    monitor_thread = threading.Thread(target=_connection_monitor, daemon=True)
    monitor_thread.start()

    # kl = IrisLink(bot.iris_url)
    bot.run()
