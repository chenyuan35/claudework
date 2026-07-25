"""
头条号自动发布 - 选题评分 (v8.0)
输入候选选题列表和方向数据，输出评分排序后的最优选题。
"""
import json, sys

SCORE_DIMS = {
    "audience_match": 25,
    "historical_data": 25,
    "practical_value": 20,
    "series_follow_value": 15,
    "timeliness_search": 10,
    "source_reliability": 5,
}

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
