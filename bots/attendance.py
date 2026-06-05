import csv
import os
import time
import urllib.request

SHEETS = {
    "2025-2": "1J4ErATN6Jnpj5_pc58a-IculN5kn5BAW3PmMvu0e1Ls",
    "2026-1": "1IiBwx_Hto-ZJ4UYhbF786bG7mDhNXfmciGCHam9VP6Q",
}
SHEET_NAME = "Summary"

_COL_P_NAME = 14
_COL_P_COUNT = 15
_COL_L_NAME = 34
_COL_L_COUNT = 35
_DATA_START_ROW = 4

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
CACHE_TTL = 3600  # 1시간

os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(sheet_id):
    return os.path.join(CACHE_DIR, f"attendance_{sheet_id}.csv")


def _is_cache_fresh(path):
    if not os.path.exists(path):
        return False
    return time.time() - os.path.getmtime(path) < CACHE_TTL


def _load_csv(path_or_url, is_url=False):
    if is_url:
        req = urllib.request.Request(
            path_or_url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            lines = [line.decode('utf-8') for line in response.readlines()]
            reader = csv.reader(lines)
            return list(reader)
    else:
        with open(path_or_url, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            return list(reader)


def _write_csv(path, rows):
    with open(path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def _search_sheet(sheet_id, nickname):
    path = _cache_path(sheet_id)
    if _is_cache_fresh(path):
        rows = _load_csv(path, is_url=False)
    else:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
        rows = _load_csv(url, is_url=True)
        _write_csv(path, rows)

    participants_count = 0
    leaders_count = 0

    # Find first participant match
    for row in rows[_DATA_START_ROW:]:
        if len(row) > _COL_P_COUNT:
            p_name = row[_COL_P_NAME].strip()
            p_count = row[_COL_P_COUNT].strip()
            if p_name == nickname:
                try:
                    participants_count = int(float(p_count)) if p_count else 0
                except ValueError:
                    pass
                break

    # Find first leader match
    for row in rows[_DATA_START_ROW:]:
        if len(row) > _COL_L_COUNT:
            l_name = row[_COL_L_NAME].strip()
            l_count = row[_COL_L_COUNT].strip()
            if l_name == nickname:
                try:
                    leaders_count = int(float(l_count)) if l_count else 0
                except ValueError:
                    pass
                break

    return {
        "참가": participants_count,
        "모임장": leaders_count,
    }


def get_attendance(nickname):
    results = {}
    for label, sheet_id in SHEETS.items():
        try:
            results[label] = _search_sheet(sheet_id, nickname)
        except Exception as e:
            results[label] = {"error": str(e)}
    return results


def build_attendance_message(nickname, results):
    total_p = 0
    total_l = 0
    lines = [f"[오름봇] 🏔️ {nickname}님의 참석 현황"]
    lines.append("")

    for label, data in results.items():
        if "error" in data:
            lines.append(f"❌ {label}: 조회 실패")
        else:
            p = data["참가"]
            l = data["모임장"]
            total_p += p
            total_l += l
            parts = []
            if p:
                parts.append(f"참가 {p}회")
            if l:
                parts.append(f"모임장 {l}회")
            lines.append(f"📋 {label}: {' / '.join(parts) if parts else '참가 없음'}")

    lines.append("")
    lines.append(f"🎯 합계: 참가 {total_p}회 / 모임장 {total_l}회")
    return "\n".join(lines)


def _get_all_ranked(sheet_id):
    path = _cache_path(sheet_id)
    if _is_cache_fresh(path):
        rows = _load_csv(path, is_url=False)
    else:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
        rows = _load_csv(url, is_url=True)
        _write_csv(path, rows)

    def _sorted_list(name_col, count_col):
        results = []
        for row in rows[_DATA_START_ROW:]:
            if len(row) > count_col:
                name = row[name_col].strip()
                count_str = row[count_col].strip()
                if name:
                    try:
                        count = int(float(count_str)) if count_str else 0
                        if count > 0:
                            results.append((name, count))
                    except ValueError:
                        pass
        # Stable sort by count descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    return {
        "participants": _sorted_list(_COL_P_NAME, _COL_P_COUNT),
        "leaders":      _sorted_list(_COL_L_NAME, _COL_L_COUNT),
    }


def _competition_rank(ranked_list, target_name):
    rank = 1
    prev_count = None
    for i, (name, count) in enumerate(ranked_list):
        if count != prev_count:
            rank = i + 1
            prev_count = count
        if name == target_name:
            return rank
    return None


def get_attendance_ranking(season="2026-1", requester=None):
    sheet_id = SHEETS.get(season)
    if not sheet_id:
        return {"error": f"시즌 '{season}'을 찾을 수 없습니다."}
    try:
        all_ranked = _get_all_ranked(sheet_id)
        my_p_rank = _competition_rank(all_ranked["participants"], requester) if requester else None
        my_l_rank = _competition_rank(all_ranked["leaders"], requester) if requester else None
        my_p_count = next((c for n, c in all_ranked["participants"] if n == requester), 0) if requester else 0
        my_l_count = next((c for n, c in all_ranked["leaders"] if n == requester), 0) if requester else 0
        return {
            "season": season,
            "participants": all_ranked["participants"][:5],
            "leaders": all_ranked["leaders"][:5],
            "my_p_rank": my_p_rank,
            "my_p_count": my_p_count,
            "my_l_rank": my_l_rank,
            "my_l_count": my_l_count,
            "requester": requester,
        }
    except Exception as e:
        return {"error": str(e)}


def build_attendance_ranking_message(data, requester=None):
    if "error" in data:
        return f"[오름봇] ❌ 순위 조회 실패: {data['error']}"

    season = data["season"]
    lines = [f"[오름봇] 🏆 {season} 참석 순위"]
    lines.append("")

    # 참가 순위
    participants = data["participants"]
    lines.append("⛰️ 참가 순위 (Top 5)")
    if participants:
        rank = 1
        prev_count = None
        for i, (name, count) in enumerate(participants):
            if count != prev_count:
                rank = i + 1
                prev_count = count
            lines.append(f"  {rank}. {name}: {count}회")
    else:
        lines.append("  (데이터 없음)")

    # 본인 참가 순위
    my_p_rank = data.get("my_p_rank")
    my_p_count = data.get("my_p_count", 0)
    req = data.get("requester") or requester
    if req and my_p_rank:
        top5_names = [n for n, _ in participants]
        if req not in top5_names:
            lines.append(f"  ···")
            lines.append(f"  {my_p_rank}. {req}: {my_p_count}회 (내 순위)")

    lines.append("")

    # 모임장 순위
    leaders = data["leaders"]
    lines.append("🎤 모임장 순위 (Top 5)")
    if leaders:
        rank = 1
        prev_count = None
        for i, (name, count) in enumerate(leaders):
            if count != prev_count:
                rank = i + 1
                prev_count = count
            lines.append(f"  {rank}. {name}: {count}회")
    else:
        lines.append("  (데이터 없음)")

    # 본인 모임장 순위
    my_l_rank = data.get("my_l_rank")
    my_l_count = data.get("my_l_count", 0)
    if req and my_l_rank:
        top5_l_names = [n for n, _ in leaders]
        if req not in top5_l_names:
            lines.append(f"  ···")
            lines.append(f"  {my_l_rank}. {req}: {my_l_count}회 (내 순위)")

    return "\n".join(lines)
