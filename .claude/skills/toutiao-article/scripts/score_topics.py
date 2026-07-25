"""
头条号自动发布 - 选题评分 (v8.0)
输入候选选题列表和方向数据，输出评分排序后的最优选题。
"""
import json, sys, os
from datetime import datetime, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.lib.config_loader import get_thresholds, get_content_policy

SCORE_DIMS = {
    "audience_match": 25,
    "historical_data": 25,
    "practical_value": 20,
    "series_follow_value": 15,
    "timeliness_search": 10,
    "source_reliability": 5,
}


def _account_directions() -> set:
    policy = get_content_policy()
    account = policy.get("account", {})
    directions = {str(x) for x in account.get("direction_ids", [])}
    for pillar in account.get("content_pillars", []):
        directions.add(str(pillar.get("key", "")))
        directions.update(str(x) for x in pillar.get("subdirs", []))
    return {d for d in directions if d}


def _topic_matches_account(topic: dict) -> bool:
    allowed = _account_directions()
    values = {
        str(topic.get("content_pillar", "")),
        str(topic.get("direction", "")),
        str(topic.get("subdirection", "")),
    }
    return bool({v for v in values if v} & allowed)


def _hot_bonus(topic: dict) -> int:
    """热点只在符合账号方向且达到阈值、未过期时加有限分。"""
    cfg = get_thresholds()["topics"]
    hot_score = topic.get("hot_score")
    if not isinstance(hot_score, (int, float)) or hot_score < cfg["hot_topic_min_score"]:
        return 0
    if not _topic_matches_account(topic):
        return 0

    age_days = topic.get("hot_age_days")
    published_at = topic.get("hot_published_at")
    if age_days is None and not published_at:
        return 0
    if isinstance(age_days, (int, float)) and age_days > cfg["hot_topic_age_days_max"]:
        return 0
    if published_at and age_days is None:
        try:
            published = datetime.fromisoformat(str(published_at).replace("Z", "+00:00")).date()
            if (date.today() - published).days > cfg["hot_topic_age_days_max"]:
                return 0
        except (TypeError, ValueError):
            return 0

    return min(cfg["hot_topic_bonus_max"], max(1, int(hot_score // 20)))

def score_topic(topic: dict, high_performance_dirs: list, recent_titles: list) -> dict:
    """
    topic: { title, direction, hot_score, source, audience_score, etc. }
    Returns topic with score and breakdown.
    """
    breakdown = {}
    total = 0

    # Audience match (0-25)
    am = topic.get("audience_score", 10)
    am = max(0, min(25, am))
    breakdown["audience_match"] = am
    total += am

    # Historical data (0-25)
    is_core = topic.get("direction") in high_performance_dirs
    hd = 25 if is_core else (10 if not high_performance_dirs else 5)
    if topic.get("direction") and high_performance_dirs and topic["direction"] in high_performance_dirs:
        hd = 25
    elif topic.get("direction") and high_performance_dirs:
        # adjacent direction
        hd = 15
    else:
        hd = 5
    breakdown["historical_data"] = hd
    total += hd

    # Practical value (0-20)
    pv = topic.get("practical_value", 10)
    pv = max(0, min(20, pv))
    breakdown["practical_value"] = pv
    total += pv

    # Series continuity / follow value (0-15)
    sf = 15 if topic.get("series_id") else 5
    breakdown["series_follow_value"] = sf
    total += sf

    # Timeliness or search demand (0-10)
    ts = topic.get("timeliness_score", 5)
    ts = max(0, min(10, ts))
    breakdown["timeliness_search"] = ts
    total += ts

    # Source reliability (0-5)
    sr = topic.get("source_score", 3)
    sr = max(0, min(5, sr))
    breakdown["source_reliability"] = sr
    total += sr

    hot_bonus = _hot_bonus(topic)
    breakdown["account_aligned_hot_bonus"] = hot_bonus
    total += hot_bonus

    return {
        **topic,
        "score": total,
        "breakdown": breakdown,
    }


def rank_topics(candidates: list, high_performance_dirs: list, recent_titles: list) -> list:
    """Score and rank multiple candidate topics."""
    scored = []
    for t in candidates:
        s = score_topic(t, high_performance_dirs, recent_titles)
        scored.append(s)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def main():
    if len(sys.argv) > 1:
        input_data = json.loads(open(sys.argv[1], "r", encoding="utf-8").read())
    else:
        input_data = json.loads(sys.stdin.read())

    candidates = input_data.get("candidates", [])
    high_perf = input_data.get("high_performance_directions", [])
    recent = input_data.get("recent_titles", [])

    ranked = rank_topics(candidates, high_perf, recent)
    print(json.dumps(ranked, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
