import logging
import time

from iris import PyKV

from bots.koseioreum_store import (
    ALERT_CHAT_ID,
    KoseioreumStore,
    WATCHED_ROOMS,
    build_change_message,
    build_nickname_change_room_message,
    build_nickname_index,
    duplicate_nicknames_for,
    fetch_members,
    migrate_pykv_history,
    parse_nickname_for_room,
)


REFRESH_SECOND = 10
HISTORY_KEY = "koseioreum.nickname_history"
LEGACY_HISTORY_KEY = "user_history"

log = logging.getLogger(__name__)


def detect_nickname_change(bot):
    store = KoseioreumStore()
    migrate_existing_pykv_history()

    # 초기 시드: 두 방 모두 처리
    for chat_id, room in WATCHED_ROOMS:
        kakao_members = fetch_members(bot, chat_id)
        existing = store.active_members(chat_id)
        if not existing:
            store.seed_members_from_kakao(kakao_members)
            log.info("INIT 멤버 DB 초기화 [%s]: %d명", room, len(kakao_members))
        else:
            store.reconcile_with_kakao(chat_id, kakao_members)
            log.info("INIT 멤버 DB 동기화 [%s]: %d명", room, len(existing))

    # room별 캐시
    caches = {
        room: {"nickname_index": {}, "last_user_ids": set()}
        for _, room in WATCHED_ROOMS
    }

    while True:
        try:
            for chat_id, room in WATCHED_ROOMS:
                _poll_room(bot, store, chat_id, room, caches[room])
        except Exception as e:
            log.error("닉변 감지 루프 오류: %s", e)

        time.sleep(REFRESH_SECOND)


def _poll_room(bot, store, chat_id, room, cache):
    kakao_members = fetch_members(bot, chat_id)

    # DB 일관성 유지용 — 메시지 없이 조용히 싱크
    store.reconcile_with_kakao(chat_id, kakao_members)

    active_members = store.active_members(chat_id)
    active_user_ids = {m["user_id"] for m in active_members}

    if active_user_ids != cache["last_user_ids"]:
        cache["nickname_index"] = build_nickname_index(active_members, room)
        cache["last_user_ids"] = active_user_ids

    for user_id, member in kakao_members.items():
        if user_id not in active_user_ids:
            continue

        result = store.record_nickname_if_changed(
            member["involved_chat_id"],
            user_id,
            member["nickname"],
        )
        if result is None:
            continue

        old_nickname, _ = result
        store.update_member_nickname(member["involved_chat_id"], user_id, member["nickname"])
        log.info("NICK 변경 [%s] %s -> %s", room, old_nickname, member["nickname"])

        history_items = store.nickname_history(member["involved_chat_id"], user_id)
        duplicates = duplicate_nicknames_for(member, cache["nickname_index"], room)
        parsed = parse_nickname_for_room(room, member["nickname"])

        admin_message = build_change_message(
            old_nickname=old_nickname,
            new_nickname=member["nickname"],
            history_items=history_items,
            duplicates=duplicates,
            room=room,
        )
        bot.api.reply(ALERT_CHAT_ID, admin_message)

        room_message = build_nickname_change_room_message(member["nickname"], parsed, duplicates, room)
        bot.api.reply(int(chat_id), room_message)


def migrate_existing_pykv_history():
    store = KoseioreumStore()
    count = store.conn().execute("SELECT COUNT(*) FROM nickname_history").fetchone()[0]
    if count > 0:
        return  # 이미 마이그레이션 완료

    for key in (HISTORY_KEY, LEGACY_HISTORY_KEY):
        try:
            kv_history = PyKV().get(key)
        except Exception as e:
            log.warning("PyKV 이력 마이그레이션 스킵 [%s]: %s", key, e)
            return

        if kv_history:
            migrate_pykv_history(kv_history)
