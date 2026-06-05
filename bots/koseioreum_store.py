import datetime
import os
import sqlite3
import threading
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "koseioreum.sqlite3")
WATCH_CHAT_ID = "18395441345102104"
REAL_NAME_CHAT_ID = "18395442868252954"
ALERT_CHAT_ID = 465280136383018

ROOM_ALL = "all"
ROOM_REAL = "real"

ROOM_LABELS = {
    ROOM_ALL: "고세오름",
    ROOM_REAL: "고세오름 실명방",
}

ROOM_FORMAT_HINTS = {
    ROOM_ALL: ("닉네임/나이/지역/학교/성별", "헿헿/93/강남/연대/남"),
    ROOM_REAL: ("본명/나이/지역/닉네임", "김진우/93/강남/헿헿"),
}

CHAT_ID_TO_ROOM = {
    WATCH_CHAT_ID: ROOM_ALL,
    REAL_NAME_CHAT_ID: ROOM_REAL,
}

WATCHED_ROOMS = [
    (WATCH_CHAT_ID, ROOM_ALL),
    (REAL_NAME_CHAT_ID, ROOM_REAL),
]

ALLOWED_SCHOOLS = {"연대", "고대"}
ALLOWED_GENDERS = {"남", "여"}

_LOCK = threading.RLock()


class KoseioreumStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self.init_schema()

    def conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def init_schema(self):
        with _LOCK:
            conn = self.conn()
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS current_members (
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    nickname TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    joined_at TEXT,
                    left_at TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nickname_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    nickname TEXT NOT NULL DEFAULT '',
                    changed_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_current_members_active "
                "ON current_members (chat_id, active)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_nickname_history_member "
                "ON nickname_history (chat_id, user_id, id)"
            )
            conn.commit()

    def upsert_member(self, chat_id, user_id, nickname, active=True, joined_at=None, left_at=None):
        now = now_kst()
        chat_id = str(chat_id)
        user_id = str(user_id)
        nickname = nickname or ""

        with _LOCK:
            self.conn().execute(
                """
                INSERT INTO current_members
                    (chat_id, user_id, nickname, active, joined_at, left_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    nickname = excluded.nickname,
                    active = excluded.active,
                    joined_at = COALESCE(excluded.joined_at, current_members.joined_at),
                    left_at = excluded.left_at,
                    updated_at = excluded.updated_at
                """,
                (chat_id, user_id, nickname, 1 if active else 0, joined_at, left_at, now),
            )
            self.conn().commit()

    def seed_members_from_kakao(self, members):
        now = now_kst()
        with _LOCK:
            conn = self.conn()
            with conn:
                for member in members.values():
                    chat_id = str(member["involved_chat_id"])
                    user_id = str(member["user_id"])
                    nickname = member["nickname"] or ""

                    # Upsert member
                    conn.execute(
                        """
                        INSERT INTO current_members
                            (chat_id, user_id, nickname, active, joined_at, left_at, updated_at)
                        VALUES (?, ?, ?, 1, '', NULL, ?)
                        ON CONFLICT(chat_id, user_id) DO UPDATE SET
                            nickname = excluded.nickname,
                            active = excluded.active,
                            left_at = excluded.left_at,
                            updated_at = excluded.updated_at
                        """,
                        (chat_id, user_id, nickname, now),
                    )

                    # Ensure history exists
                    exists = conn.execute(
                        """
                        SELECT 1 FROM nickname_history
                        WHERE chat_id = ? AND user_id = ?
                        LIMIT 1
                        """,
                        (chat_id, user_id),
                    ).fetchone()
                    if not exists:
                        conn.execute(
                            """
                            INSERT INTO nickname_history (chat_id, user_id, nickname, changed_at)
                            VALUES (?, ?, ?, '')
                            """,
                            (chat_id, user_id, nickname),
                        )

    def mark_left(self, chat_id, user_id, nickname=""):
        chat_id = str(chat_id)
        user_id = str(user_id)
        nickname = nickname or self.get_member_nickname(chat_id, user_id) or ""
        self.upsert_member(chat_id, user_id, nickname, active=False, left_at=now_kst())

    def ensure_history(self, chat_id, user_id, nickname, changed_at):
        chat_id = str(chat_id)
        user_id = str(user_id)
        nickname = nickname or ""
        with _LOCK:
            conn = self.conn()
            with conn:
                exists = conn.execute(
                    """
                    SELECT 1 FROM nickname_history
                    WHERE chat_id = ? AND user_id = ?
                    LIMIT 1
                    """,
                    (chat_id, user_id),
                ).fetchone()
                if exists:
                    return
                conn.execute(
                    """
                    INSERT INTO nickname_history (chat_id, user_id, nickname, changed_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chat_id, user_id, nickname, changed_at),
                )

    def record_nickname_if_changed(self, chat_id, user_id, nickname):
        chat_id = str(chat_id)
        user_id = str(user_id)
        nickname = nickname or ""
        changed_at = now_kst()

        with _LOCK:
            conn = self.conn()
            with conn:
                previous = conn.execute(
                    """
                    SELECT nickname FROM nickname_history
                    WHERE chat_id = ? AND user_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (chat_id, user_id),
                ).fetchone()

                if previous is None:
                    conn.execute(
                        """
                        INSERT INTO nickname_history (chat_id, user_id, nickname, changed_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (chat_id, user_id, nickname, ""),
                    )
                    return None

                old_nickname = previous["nickname"]
                if old_nickname == nickname:
                    return None

                conn.execute(
                    """
                    INSERT INTO nickname_history (chat_id, user_id, nickname, changed_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chat_id, user_id, nickname, changed_at),
                )
                return old_nickname, changed_at

    def update_member_nickname(self, chat_id, user_id, nickname):
        chat_id = str(chat_id)
        user_id = str(user_id)
        nickname = nickname or ""
        with _LOCK:
            conn = self.conn()
            with conn:
                conn.execute(
                    """
                    UPDATE current_members
                    SET nickname = ?, updated_at = ?
                    WHERE chat_id = ? AND user_id = ?
                    """,
                    (nickname, now_kst(), chat_id, user_id),
                )

    def active_members(self, chat_id=WATCH_CHAT_ID):
        rows = self.conn().execute(
            """
            SELECT chat_id, user_id, nickname, joined_at, updated_at
            FROM current_members
            WHERE chat_id = ? AND active = 1
            ORDER BY nickname COLLATE NOCASE
            """,
            (str(chat_id),),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_member_nickname(self, chat_id, user_id):
        row = self.conn().execute(
            """
            SELECT nickname FROM current_members
            WHERE chat_id = ? AND user_id = ?
            """,
            (str(chat_id), str(user_id)),
        ).fetchone()
        return row["nickname"] if row else None

    def nickname_history(self, chat_id, user_id):
        rows = self.conn().execute(
            """
            SELECT nickname, changed_at
            FROM nickname_history
            WHERE chat_id = ? AND user_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (str(chat_id), str(user_id)),
        ).fetchall()
        return [dict(row) for row in rows]

    def reconcile_with_kakao(self, chat_id, kakao_members):
        chat_id = str(chat_id)
        now = now_kst()

        with _LOCK:
            conn = self.conn()
            # Get currently active members in DB
            active_rows = conn.execute(
                "SELECT user_id, nickname FROM current_members WHERE chat_id = ? AND active = 1",
                (chat_id,),
            ).fetchall()
            db_active = {row["user_id"]: row["nickname"] for row in active_rows}

            # Get all known members in DB
            rows = conn.execute(
                "SELECT user_id FROM current_members WHERE chat_id = ?",
                (chat_id,),
            ).fetchall()
            db_known = {row["user_id"] for row in rows}

            added = []
            left = []

            with conn:
                # 1. Reconcile added / re-joined members
                for user_id, member in kakao_members.items():
                    nickname = member["nickname"] or ""
                    if user_id not in db_known:
                        # Completely new member
                        conn.execute(
                            """
                            INSERT INTO current_members
                                (chat_id, user_id, nickname, active, joined_at, left_at, updated_at)
                            VALUES (?, ?, ?, 1, ?, NULL, ?)
                            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                                nickname = excluded.nickname,
                                active = excluded.active,
                                joined_at = COALESCE(excluded.joined_at, current_members.joined_at),
                                left_at = excluded.left_at,
                                updated_at = excluded.updated_at
                            """,
                            (chat_id, user_id, nickname, now, now),
                        )
                        # Ensure history exists
                        exists = conn.execute(
                            "SELECT 1 FROM nickname_history WHERE chat_id = ? AND user_id = ? LIMIT 1",
                            (chat_id, user_id),
                        ).fetchone()
                        if not exists:
                            conn.execute(
                                """
                                INSERT INTO nickname_history (chat_id, user_id, nickname, changed_at)
                                VALUES (?, ?, ?, '')
                                """,
                                (chat_id, user_id, nickname),
                            )
                        added.append(user_id)
                    else:
                        # Existing member in DB: check if they re-joined
                        if user_id not in db_active:
                            conn.execute(
                                """
                                UPDATE current_members
                                SET active = 1, nickname = ?, left_at = NULL, updated_at = ?
                                WHERE chat_id = ? AND user_id = ?
                                """,
                                (nickname, now, chat_id, user_id),
                            )
                            added.append(user_id)

                # 2. Reconcile left members
                for user_id, nickname in db_active.items():
                    if user_id not in kakao_members:
                        conn.execute(
                            """
                            UPDATE current_members
                            SET active = 0, left_at = ?, updated_at = ?
                            WHERE chat_id = ? AND user_id = ?
                            """,
                            (now, now, chat_id, user_id),
                        )
                        left.append(nickname)

        return {"added": added, "left": left}

    def set_active(self, chat_id, user_id, nickname, active=True):
        self.upsert_member(str(chat_id), str(user_id), nickname, active=active,
                           left_at=None if active else now_kst())

    def member_by_full_nickname(self, chat_id, full_nickname):
        row = self.conn().execute(
            """
            SELECT user_id, nickname, active FROM current_members
            WHERE chat_id = ? AND nickname = ?
            LIMIT 1
            """,
            (str(chat_id), full_nickname),
        ).fetchone()
        return dict(row) if row else None

    def real_name_by_all_user_id(self):
        real_members = self.active_members(REAL_NAME_CHAT_ID)
        all_members = self.active_members(WATCH_CHAT_ID)

        all_by_nickname_part = {}
        duplicate_parts = set()
        for m in all_members:
            parsed = parse_all_nickname(m["nickname"])
            part = parsed["nickname_part"]
            if not part:
                continue
            if part in all_by_nickname_part:
                duplicate_parts.add(part)
            else:
                all_by_nickname_part[part] = m["user_id"]

        result = {}
        unmatched_real = []

        for m in real_members:
            parsed = parse_real_name_nickname(m["nickname"])
            part = parsed["nickname_part"]
            real_name = parsed.get("name", "")
            if not part or not real_name:
                unmatched_real.append(m["nickname"])
                continue
            if part in duplicate_parts:
                unmatched_real.append(m["nickname"])
                continue
            all_uid = all_by_nickname_part.get(part)
            if all_uid:
                result[all_uid] = real_name
            else:
                unmatched_real.append(m["nickname"])

        return result, list(duplicate_parts), unmatched_real


def fetch_members(bot, chat_id=WATCH_CHAT_ID):
    api = bot.api if hasattr(bot, "api") else bot
    rows = api.query(
        query=(
            "SELECT enc, nickname, user_id, involved_chat_id "
            "FROM db2.open_chat_member "
            "WHERE involved_chat_id = ?"
        ),
        bind=[str(chat_id)],
    )

    members = {}
    for row in rows:
        user_id = str(row["user_id"])
        members[user_id] = {
            "user_id": user_id,
            "nickname": row.get("nickname") or "",
            "involved_chat_id": str(row["involved_chat_id"]),
        }
    return members


def parse_all_nickname(nickname):
    parts = [part.strip() for part in (nickname or "").split("/")]
    errors = []

    if len(parts) != 5:
        return {
            "valid": False,
            "nickname_part": parts[0] if parts else "",
            "age": None,
            "region": "",
            "school": "",
            "gender": "",
            "parts": parts,
            "errors": ["형식은 닉네임/나이/지역/학교/성별 이어야 합니다."],
        }

    nickname_part, age, region, school, gender = parts

    if not nickname_part:
        errors.append("닉네임이 비어 있습니다.")
    if not age.isdigit():
        errors.append("나이는 숫자만 허용됩니다.")
    if not region:
        errors.append("지역이 비어 있습니다.")
    if school not in ALLOWED_SCHOOLS:
        errors.append("학교는 연대 또는 고대만 허용됩니다.")
    if gender not in ALLOWED_GENDERS:
        errors.append("성별은 남 또는 여만 허용됩니다.")

    return {
        "valid": len(errors) == 0,
        "nickname_part": nickname_part,
        "age": int(age) if age.isdigit() else None,
        "region": region,
        "school": school,
        "gender": gender,
        "parts": parts,
        "errors": errors,
    }


def parse_real_name_nickname(nickname):
    parts = [part.strip() for part in (nickname or "").split("/")]
    errors = []

    if len(parts) != 4:
        return {
            "valid": False,
            "name": parts[0] if parts else "",
            "age": None,
            "region": "",
            "nickname_part": parts[3] if len(parts) >= 4 else "",
            "parts": parts,
            "errors": ["형식은 본명/나이/지역/닉네임 이어야 합니다."],
        }

    name, age, region, nickname_part = parts

    if not name:
        errors.append("본명이 비어 있습니다.")
    if not age.isdigit():
        errors.append("나이는 숫자만 허용됩니다.")
    if not region:
        errors.append("지역이 비어 있습니다.")
    if not nickname_part:
        errors.append("닉네임이 비어 있습니다.")

    return {
        "valid": len(errors) == 0,
        "name": name,
        "age": int(age) if age.isdigit() else None,
        "region": region,
        "nickname_part": nickname_part,
        "parts": parts,
        "errors": errors,
    }


def parse_nickname_for_room(room, nickname):
    if room == ROOM_REAL:
        return parse_real_name_nickname(nickname)
    return parse_all_nickname(nickname)


# Backwards-compatible alias used elsewhere (attendance.py, irispy.py)
parse_koseioreum_nickname = parse_all_nickname


def build_nickname_index(members, room=ROOM_ALL):
    index = defaultdict(list)
    for member in members:
        parsed = parse_nickname_for_room(room, member["nickname"])
        nickname_part = parsed["nickname_part"]
        if nickname_part:
            index[nickname_part].append(member["nickname"])
    return index


def duplicate_nicknames_for(member, nickname_index, room=ROOM_ALL):
    parsed = parse_nickname_for_room(room, member["nickname"])
    nickname_part = parsed["nickname_part"]
    if not nickname_part:
        return []
    nicknames = nickname_index.get(nickname_part, [])
    if len(nicknames) <= 1:
        return []
    return nicknames


def build_welcome_message(nickname, parsed, duplicates, room=ROOM_ALL):
    issues = []

    if not parsed["valid"]:
        issues.extend(parsed["errors"])

    other_duplicates = [n for n in duplicates if n != nickname]
    if other_duplicates:
        dup_list = ", ".join(other_duplicates)
        issues.append(f"닉네임 '{parsed['nickname_part']}'이(가) 이미 사용 중입니다: {dup_list}")

    display_name = parsed["nickname_part"] or nickname

    if not issues:
        return f"[오름봇] 🎉 {display_name}님, 환영합니다!"

    fmt, example = ROOM_FORMAT_HINTS.get(room, ROOM_FORMAT_HINTS[ROOM_ALL])
    issue_lines = "\n".join(f"• {i}" for i in issues)
    return (
        f"[오름봇] {display_name}님, 환영합니다!\n"
        "닉네임에 문제가 있어요. 확인 후 수정해주세요.\n\n"
        f"{issue_lines}\n\n"
        f"형식: {fmt}\n"
        f"예시: {example}"
    )


def build_change_message(old_nickname, new_nickname, history_items, duplicates, room=ROOM_ALL):
    parsed = parse_nickname_for_room(room, new_nickname)
    validation = "정상" if parsed["valid"] else "오류: " + ", ".join(parsed["errors"])

    duplicate_text = "없음"
    if duplicates:
        duplicate_text = f"닉네임 부분 '{parsed['nickname_part']}' 중복: {len(duplicates)}명"

    history_lines = []
    for item in history_items:
        prefix = f"[{item['changed_at']}] " if item["changed_at"] else ""
        history_lines.append(f"ㄴ{prefix}{item['nickname']}")

    label = ROOM_LABELS.get(room, ROOM_LABELS[ROOM_ALL])
    valid_mark = "✅" if parsed["valid"] else "⚠️"
    dup_mark = "✅" if not duplicates else "⚠️"
    return (
        f"[🔔 {label} 닉네임 변경]\n"
        f"✏️ {old_nickname} → {new_nickname}\n"
        f"{valid_mark} 형식: {validation}\n"
        f"{dup_mark} 중복: {duplicate_text}\n"
        + "\u200b" * 600
        + "\n"
        + "\n".join(history_lines)
    ).strip()


def build_nickname_change_room_message(new_nickname, parsed, duplicates, room=ROOM_ALL):
    issues = []

    if not parsed["valid"]:
        issues.extend(parsed["errors"])

    other_duplicates = [n for n in duplicates if n != new_nickname]
    if other_duplicates:
        dup_list = ", ".join(other_duplicates)
        issues.append(f"닉네임 '{parsed['nickname_part']}'이(가) 이미 사용 중입니다: {dup_list}")

    display_name = parsed["nickname_part"] or new_nickname

    if not issues:
        return (
            f"[오름봇] ✏️ {display_name}님이 닉네임을 변경했어요.\n"
            "✅ 현재 닉네임은 규칙에 맞습니당 😊"
        )

    fmt, example = ROOM_FORMAT_HINTS.get(room, ROOM_FORMAT_HINTS[ROOM_ALL])
    issue_lines = "\n".join(f"• {i}" for i in issues)
    return (
        f"[오름봇] ✏️ {display_name}님이 닉네임을 변경했어요.\n"
        "⚠️ 닉네임에 문제가 있어요. 확인 후 수정해주세요.\n\n"
        f"{issue_lines}\n\n"
        f"📋 형식: {fmt}\n"
    )


def build_member_stats_message(members, real_name_by_user_id=None, real_members=None, unmatched_real=None, include_names=False):
    real_name_by_user_id = real_name_by_user_id or {}
    real_members = real_members or []
    unmatched_real = unmatched_real or []

    parsed_members = [(member, parse_koseioreum_nickname(member["nickname"])) for member in members]
    valid = [(member, parsed) for member, parsed in parsed_members if parsed["valid"]]
    invalid = [(member, parsed) for member, parsed in parsed_members if not parsed["valid"]]

    ages = Counter(parsed["age"] for _, parsed in valid)
    schools = Counter(parsed["school"] for _, parsed in valid)
    genders = Counter(parsed["gender"] for _, parsed in valid)
    regions = Counter(parsed["region"] for _, parsed in valid)

    valid_count = len(valid)
    age_lines = "\n".join(
        f"- {age:02d}: {count}명 ({count / valid_count * 100:.1f}%)" if valid_count else f"- {age:02d}: {count}명"
        for age, count in sorted(ages.items(), key=lambda x: x[0] if x[0] >= 51 else x[0] + 100)
    ) or "없음"

    parsed_real = [(m, parse_real_name_nickname(m["nickname"])) for m in real_members]
    real_invalid = [(m, p) for m, p in parsed_real if not p["valid"]]

    real_name_count = len(real_name_by_user_id)

    lines = [
        "[오름봇] 👥 고세오름 현재원 통계",
        f"현재원: {len(members)}명  |  실명방: {real_name_count}명",
        f"✅ 형식 정상: {len(valid)}명  ⚠️ 오류: {len(invalid)}명",
        f"실명방 ✅ {len(parsed_real) - len(real_invalid)}명  ⚠️ {len(real_invalid)}명",
        "",
        "📅 나이",
        age_lines,
        "",
        "🏫 학교",
        format_counter(schools),
        "",
        "🚻 성별",
        format_counter(genders),
        "",
        "📍 지역",
        format_counter(regions),
    ]

    if invalid:
        lines.extend(["", "⚠️ [전체방] 형식 오류 닉네임"])
        lines.extend(f"- {member['nickname']}" for member, _ in invalid[:30])
        if len(invalid) > 30:
            lines.append(f"... 외 {len(invalid) - 30}명")

    if include_names:
        lines.extend(["", "📋 현재원 닉네임"])
        for idx, member in enumerate(members, 1):
            real_name = real_name_by_user_id.get(str(member["user_id"]))
            tag = f" [{real_name}]" if real_name else ""
            lines.append(f"{idx}. {member['nickname']}{tag}")

        if real_invalid:
            lines.extend(["", "⚠️ [실명방] 형식 오류 닉네임"])
            lines.extend(f"- {m['nickname']}" for m, _ in real_invalid[:30])
            if len(real_invalid) > 30:
                lines.append(f"... 외 {len(real_invalid) - 30}명")

        if unmatched_real:
            lines.extend(["", "🔍 [실명방] 전체방 미매칭 멤버"])
            lines.extend(f"- {nick}" for nick in unmatched_real[:30])
            if len(unmatched_real) > 30:
                lines.append(f"... 외 {len(unmatched_real) - 30}명")

    return "\n".join(lines).strip()


def build_chat_stats_message(bot, members, chat_id=WATCH_CHAT_ID, days=30, title="고세오름 대화 통계"):
    active_user_ids = {str(member["user_id"]) for member in members}
    nickname_by_user_id = {str(member["user_id"]): member["nickname"] for member in members}
    tz = ZoneInfo("Asia/Seoul")
    since = int((datetime.datetime.now(tz) - datetime.timedelta(days=days)).timestamp())

    api = bot.api if hasattr(bot, "api") else bot
    rows = api.query(
        query=(
            "SELECT id, type, user_id, created_at "
            "FROM chat_logs "
            "WHERE chat_id = ? AND created_at >= ? AND user_id IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 50000"
        ),
        bind=[str(chat_id), str(since)],
    )

    filtered = [
        row
        for row in rows
        if str(row.get("user_id")) in active_user_ids and row.get("created_at") is not None
    ]

    per_user = Counter(str(row["user_id"]) for row in filtered)
    per_weekday = Counter()
    per_hour = Counter()
    per_weekday_hour = defaultdict(Counter)

    for row in filtered:
        dt = datetime.datetime.fromtimestamp(int(row["created_at"]), tz)
        weekday = dt.weekday()
        hour = dt.hour
        per_weekday[weekday] += 1
        per_hour[hour] += 1
        per_weekday_hour[weekday][hour] += 1

    lines = [
        f"[오름봇] 💬 {title}",
        f"📅 기간: 최근 {days}일  |  💌 {len(filtered)}개",
        "",
        "🏆 대화 순위",
    ]

    if per_user:
        for rank, (user_id, count) in enumerate(per_user.most_common(30), 1):
            full = nickname_by_user_id.get(user_id, "(닉네임 없음)")
            display = full.split("/")[0].strip() or full
            lines.append(f"{rank}. {display}: {count}개")
    else:
        lines.append("집계된 메시지가 없습니다.")

    lines.extend(["", "📊 요일별", ascii_bar_chart(per_weekday, weekday_labels())])
    lines.extend(["", "🕐 시간대별", ascii_bar_chart(per_hour, [f"{hour:02d}" for hour in range(24)])])
    lines.extend(["", "🗓 요일×시간 히트맵", weekday_hour_heatmap(per_weekday_hour)])

    return "\n".join(lines).strip()


def format_counter(counter, total=None):
    if not counter:
        return "없음"
    total = total or sum(counter.values())
    if total == 0:
        return "없음"
    return "\n".join(
        f"- {key}: {value}명 ({value / total * 100:.1f}%)"
        for key, value in counter.most_common()
    )


def ascii_bar_chart(counter, labels):
    max_value = max(counter.values(), default=0)
    if max_value == 0:
        return "없음"

    lines = []
    for idx, label in enumerate(labels):
        value = counter.get(idx, 0)
        bar = "█" * max(1, round(value / max_value * 18)) if value else ""
        lines.append(f"{label:>2} | {bar} {value}")
    return "\n".join(lines)


def weekday_labels():
    return ["월", "화", "수", "목", "금", "토", "일"]


def weekday_hour_heatmap(per_weekday_hour):
    chars = " .:-=+*#%@"
    max_value = 0
    for weekday in range(7):
        for hour in range(0, 24, 3):
            value = sum(per_weekday_hour[weekday].get(hour + offset, 0) for offset in range(3))
            max_value = max(max_value, value)
    if max_value == 0:
        return "없음"

    lines = ["    00 03 06 09 12 15 18 21"]
    for weekday, label in enumerate(weekday_labels()):
        cells = []
        for hour in range(0, 24, 3):
            value = sum(per_weekday_hour[weekday].get(hour + offset, 0) for offset in range(3))
            index = round(value / max_value * (len(chars) - 1)) if value else 0
            cells.append(chars[index])
        lines.append(f"{label} |  {'  '.join(cells)}")
    return "\n".join(lines)


def now_kst():
    return datetime.datetime.now(ZoneInfo("Asia/Seoul")).strftime("%y%m%d %H:%M")


def migrate_pykv_history(kv_history, store=None):
    if not isinstance(kv_history, dict):
        return

    store = store or KoseioreumStore()
    conn = store.conn()
    with _LOCK:
        with conn:
            for key, value in kv_history.items():
                if ":" in key:
                    chat_id, user_id = key.split(":", 1)
                else:
                    chat_id, user_id = WATCH_CHAT_ID, key
                for item in value.get("history", []):
                    nickname = item.get("nickname") or ""
                    changed_at = item.get("date") or ""
                    conn.execute(
                        """
                        INSERT INTO nickname_history (chat_id, user_id, nickname, changed_at)
                        SELECT ?, ?, ?, ?
                        WHERE NOT EXISTS (
                            SELECT 1 FROM nickname_history
                            WHERE chat_id = ? AND user_id = ? AND nickname = ? AND changed_at = ?
                        )
                        """,
                        (
                            str(chat_id),
                            str(user_id),
                            nickname,
                            changed_at,
                            str(chat_id),
                            str(user_id),
                            nickname,
                            changed_at,
                        ),
                    )
