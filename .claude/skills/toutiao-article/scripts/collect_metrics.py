"""
头条号自动发布 - 数据采集和指标计算 (v8.0)
接收 Playwright 采集的文章数据（stdin JSON或文件），计算指标并写入 metrics.json。
"""
import json, sys, os
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.lib.config_loader import get_thresholds
from scripts.state import load_metrics, save_metrics, load_history

def calculate_ctr(reads, views):
    if not views or views == 0:
        return None
    return round(reads / views, 4)

def calculate_interaction_rate(likes, comments, reads):
    if not reads or reads == 0:
        return None
    return round((likes + comments) / reads, 4)

def calculate_follow_conversion(new_followers, reads):
    if not reads or reads == 0:
        return None
    return round(new_followers / reads, 4)

def rank_directions(scored_directions):
    cfg = get_thresholds()["metrics"]["direction_ranking"]
    ranked = sorted(scored_directions, key=lambda d: (
        (d.get("follow_conversion", 0) or 0) * cfg["follow_conversion"],
        (d.get("completion_score", 0) or 0) * cfg["completion_score"],
        (d.get("ctr", 0) or 0) * cfg["ctr"],
        (d.get("interaction_rate", 0) or 0) * cfg["interaction_rate"],
        (d.get("views", 0) or 0) * cfg["views"],
    ), reverse=True)
    return ranked

def build_batch_analysis(articles: list):
    """从文章列表构建分析，写入 metrics.json"""
    cfg = get_thresholds()["metrics"]

    total_views = sum(a.get("views", 0) for a in articles)
    total_reads = sum(a.get("reads", 0) for a in articles)
    total_likes = sum(a.get("likes", 0) for a in articles)
    total_comments = sum(a.get("comments", 0) for a in articles)

    directions = {}
    for a in articles:
        d = a.get("direction", "unknown")
        if d not in directions:
            directions[d] = []
        directions[d].append(a)

    scored = []
    for d_name, d_articles in directions.items():
        d_views = sum(a.get("views", 0) for a in d_articles)
        d_reads = sum(a.get("reads", 0) for a in d_articles)
        d_likes = sum(a.get("likes", 0) for a in d_articles)
        d_comments = sum(a.get("comments", 0) for a in d_articles)
        scored.append({
            "direction": d_name,
            "article_count": len(d_articles),
            "views": d_views,
            "reads": d_reads,
            "likes": d_likes,
            "comments": d_comments,
            "ctr": calculate_ctr(d_reads, d_views),
            "interaction_rate": calculate_interaction_rate(d_likes, d_comments, d_reads),
            "follow_conversion": None,
            "completion_score": None,
        })

    ranked = rank_directions(scored)

    high_perf = []
    low_perf = []
    hp_cfg = cfg["high_performance"]
    lp_cfg = cfg["low_performance"]
    for d in ranked:
        v = d["views"]
        r = d["ctr"] or 0
        if (v >= hp_cfg["views_min"] and r >= hp_cfg["ctr_min_pct"] / 100) or v >= hp_cfg["views_min_alternative"]:
            high_perf.append(d["direction"])
    # low performance: consecutive low views or very low CTR
    for d in ranked:
        if d["views"] < lp_cfg["multi_article_threshold"]:
            low_perf.append(d["direction"])

    batch_metrics = {
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": {
            "articles": len(articles),
            "views": total_views,
            "reads": total_reads,
            "likes": total_likes,
            "comments": total_comments,
            "ctr": calculate_ctr(total_reads, total_views),
        },
        "directions": ranked,
        "high_performance": high_perf[:2],
        "low_performance": low_perf,
    }

    # 写入 metrics.json
    m = load_metrics()
    m["last_batch"] = batch_metrics
    m["articles_total"] = m.get("articles_total", 0) + len(articles)
    recent = m.get("recent_batches", [])
    recent.append({"date": batch_metrics["run_date"], "articles": len(articles)})
    m["recent_batches"] = recent[-20:]  # keep last 20
    save_metrics(m)

    return batch_metrics


def main():
    """
    CLI 用法：
      collect_metrics.py < articles.json     # stdin JSON
      collect_metrics.py articles.json        # 文件路径
      collect_metrics.py --status             # 只打印当前状态
    """
    if "--status" in sys.argv:
        m = load_metrics()
        print(json.dumps(m, ensure_ascii=False, indent=2))
        sys.exit(0)

    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            data = json.load(f)
    elif not sys.stdin.isatty():
        data = json.loads(sys.stdin.read())
    else:
        print(json.dumps({"error": "No input data. Pipe JSON or pass file path."}, ensure_ascii=False))
        sys.exit(1)

    articles = data if isinstance(data, list) else data.get("articles", [])
    if not articles:
        print(json.dumps({"error": "Empty article list"}, ensure_ascii=False))
        sys.exit(1)

    result = build_batch_analysis(articles)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n✅ Written to metrics.json: {len(articles)} articles, {len(result['directions'])} directions")


if __name__ == "__main__":
    main()
