#!/usr/bin/env python3
"""ai_score.py — 反 AI 检测门（5 维评分）

用法:
  python ai_score.py wechat_article_xxx.txt
  python ai_score.py wechat_article_xxx.txt --threshold 45

阈值说明:
  0-30  → 人类感强 ✅
  31-45 → 可接受 ⚠️
  46-60 → AI 感偏高，建议改写 ❌
  61+   → 明显 AI 生成，必须改写 ❌❌

退出码:
  0 = 通过（评分 ≤ 阈值）
  1 = 未通过（评分 > 阈值）

参考: jiji262/wechat-publisher ai_score.py 5 维模型
"""

import argparse, math, re, sys
from collections import Counter
from pathlib import Path


# ─── 套话词库 ────────────────────────────────────────────────

CLICHE_PATTERNS = [
    '值得注意的是', '毋庸置疑', '不可否认', '众所周知',
    '在这个信息爆炸的时代', '随着AI的发展', '随着科技的进步',
    '随着社会的发展', '随着时代的变迁',
    '值得一提的是', '首先', '其次', '总的来说',
    '综上所述', '由此可见', '换言之', '换句话说',
    '时代抛弃你不会打招呼',
    '简单说', '简单来说', '不难发现',
    '我们需要', '我们应该', '我们必须',
    '不仅...而且', '既...又',
    '从某种角度来说', '从某种程度上说',
    '毫无疑问', '毫无疑问的是',
    '不出所料', '正如我们所知',
    '众所周知', '众所周知的是',
    '深刻洞察', '深度思考', '深度解析',
    '引发思考', '引人深思', '发人深省',
    '某种程度上', '某种意义上',
    '不可忽视的是', '不容忽视',
    '我们需要认识到', '我们应该认识到',
]

# AI 常用高频词（用于词汇多样性检测）
AI_FAVORITE_WORDS = {
    '但', '是', '的', '在', '和', '这', '就', '也', '不', '很',
    '更', '会', '都', '要', '可以', '因为', '所以', '如果',
    '能够', '需要', '让', '把', '被', '从', '对', '为',
    '通过', '使用', '利用', '基于', '实现',
    '方式', '方法', '手段', '途径',
    '问题', '答案', '解决方案',
    '方面', '角度', '维度', '层面',
    '场景', '领域', '行业', '市场',
    '关键', '重要', '核心', '根本',
    '提升', '提高', '增强', '优化',
    '有效', '高效', '显著', '明显',
    '理解', '了解', '认识', '认知',
    '趋势', '方向', '未来', '前景',
    '要素', '元素', '成分', '部分',
    '过程', '流程', '步骤', '环节',
    '价值', '意义', '内涵', '本质',
    '体验', '感受', '感觉', '体会',
    '帮助', '支撑', '支持', '保障',
    '机会', '机遇', '挑战', '困难',
    '真正' ,'真实', '确实', '的确',
    '最终', '最后', '终于', '总算',
    '开始', '首先', '最初', '原本',
    '因为', '因此', '所以', '于是',
    '然而', '但是', '可是', '不过',
    '不是', '没有', '无法', '难以',
    '许多', '大量', '众多', '很多',
    '这些', '那些', '某些', '各种',
    '不断', '持续', '不断', '继续',
    '可能' ,'或许', '也许', '大概',
    '已经', '已经', '早已', '早就',
    '来', '去', '做', '说', '看',
    '想', '知道', '觉得', '认为', '以为',
    '发现', '找到', '看到', '听到', '感到',
    '决定', '选择', '判断', '决定',
    '愿意', '希望', '期待', '渴望',
    '努力', '奋斗', '拼搏', '坚持',
    '成功', '失败', '胜利', '挫折',
    '各种', '不同', '一样', '相同',
    '内容', '信息', '知识', '智慧',
    '世界', '社会', '生活', '人生',
    '一个', '这个', '那个', '哪个',
    '什么', '怎么', '如何', '为什么',
    '起来', '下来', '出来', '过来',
    '下去', '上去', '进去', '出去',
    '学习', '工作', '生活', '成长',
    '关系', '感情', '情感', '情绪',
    '状态', '情况', '状况', '形势',
    '结果', '后果', '效果', '成果',
}

# 并列结构模式
PARALLEL_PATTERNS = [
    re.compile(r'既不.*也不'),
    re.compile(r'既.*又'),
    re.compile(r'不仅.*而且'),
    re.compile(r'不是.*而是'),
    re.compile(r'没有.*只有'),
    re.compile(r'无论.*都'),
    re.compile(r'虽然.*但是'),
    re.compile(r'因为.*所以'),
    re.compile(r'如果.*就'),
    re.compile(r'只要.*就'),
    re.compile(r'只有.*才'),
    re.compile(r'一.*就'),
    re.compile(r'越.*越'),
]


def extract_sentences(text):
    """提取句子列表。"""
    # 按句号/问号/感叹号/分句/换行切开
    raw = re.split(r'[。！？\n]', text)
    sentences = [s.strip() for s in raw if len(s.strip()) >= 4]
    return sentences if sentences else [text]


def score_burstiness(text):
    """1. 句长方差 — AI 句子长度太均匀，人类差异大。"""
    sentences = extract_sentences(text)
    if len(sentences) < 5:
        return 0, 0

    lengths = [len(re.findall(r'[一-鿿]', s)) for s in sentences]
    mean = sum(lengths) / len(lengths)
    if mean < 2:
        return 0, 0

    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)

    # 标准差小 = AI 均匀；标准差大 = 人类有起伏
    # 正常人标准差约 4-8，AI 约 1-3
    if std_dev < 2:
        score = 25  # 极均匀 → AI 感强
    elif std_dev < 3:
        score = 18
    elif std_dev < 4:
        score = 12
    elif std_dev < 6:
        score = 5  # 正常范围
    else:
        score = 0  # 方差大 → 人类感

    return score, round(std_dev, 1)


def score_cliche_density(text):
    """2. 套话密度 — AI 爱用固定套路句式。"""
    total_hanzi = len(re.findall(r'[一-鿿]', text))
    if total_hanzi < 100:
        return 0, []

    hits = []
    for pattern in CLICHE_PATTERNS:
        count = len(re.findall(re.escape(pattern), text))
        if count > 0:
            hits.append((pattern, count))

    total_hits = sum(c for _, c in hits)
    density = total_hits / total_hanzi * 1000  # 每千字命中数

    if total_hits == 0:
        return 0, []
    elif density < 1:
        score = 5
    elif density < 2:
        score = 12
    elif density < 4:
        score = 20
    else:
        score = 30

    return score, hits


def score_vocabulary_diversity(text):
    """3. 词汇多样性 — AI 高频词占比高，词汇量偏窄。"""
    words = re.findall(r'[一-鿿]{2,4}', text)
    if len(words) < 50:
        return 0, 0

    total = len(words)
    ai_words_count = sum(1 for w in words if w in AI_FAVORITE_WORDS)
    ratio = ai_words_count / total

    if ratio > 0.35:
        score = 25
    elif ratio > 0.28:
        score = 18
    elif ratio > 0.22:
        score = 10
    elif ratio > 0.16:
        score = 5
    else:
        score = 0

    return score, round(ratio * 100, 1)


def score_structure_regularity(text):
    """4. 结构规整度 — AI 每段字数太均匀，并列结构多。"""
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paras) < 4:
        return 0, 0, 0

    # 去除标题/插图/标记等
    body_paras = [p for p in paras
                  if not p.startswith('【金句】')
                  and not p.startswith('[插图：')
                  and not re.match(r'^[一二三四五六七八九十]+、', p)]

    if len(body_paras) < 3:
        return 0, 0, 0

    lengths = [len(re.findall(r'[一-鿿]', p)) for p in body_paras]
    mean = sum(lengths) / len(lengths)
    if mean < 5:
        return 0, 0, 0

    # 段落长度标准差（越小越均匀=越AI）
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean  # 变异系数

    # 并列结构检测
    para_text = '\n'.join(body_paras)
    parallel_count = sum(1 for p in PARALLEL_PATTERNS if p.search(para_text))

    # 打分
    if cv < 0.3:
        score = 20
    elif cv < 0.45:
        score = 12
    elif cv < 0.6:
        score = 6
    else:
        score = 0

    score += min(parallel_count * 3, 10)  # 并列结构加分

    return min(score, 25), round(cv, 2), parallel_count


def score_punctuation_diversity(text):
    """5. 标点多样性 — AI 逗号比例高，情绪标点少。"""
    chars = text.replace('\n', '').replace(' ', '').replace('\r', '')
    if len(chars) < 100:
        return 0, {}

    total_punct = 0
    punct_counts = Counter()
    for c in chars:
        if c in '，。！？；：、""''（）…—·':
            total_punct += 1
            punct_counts[c] += 1

    if total_punct == 0:
        return 0, {}

    # 逗号占比
    comma_ratio = punct_counts.get('，', 0) / total_punct

    # AI 爱用逗号 > 35%，人类爱用句号和情绪标点
    # 情绪标点（！？…——）
    emotional = punct_counts.get('！', 0) + punct_counts.get('？', 0) + \
                punct_counts.get('…', 0) * 0.5
    emotional_ratio = emotional / total_punct if total_punct > 0 else 0

    if comma_ratio > 0.4:
        score = 20
    elif comma_ratio > 0.35:
        score = 15
    elif comma_ratio > 0.3:
        score = 8
    elif comma_ratio > 0.25:
        score = 3
    else:
        score = 0

    # 情绪标点加分（人类感强）
    if emotional_ratio < 0.02:
        score += 5  # 几乎没有情绪标点 → AI 感
    elif emotional_ratio > 0.1:
        score -= 3  # 情绪多 → 人类感

    return min(score, 20), {
        'comma_ratio': round(comma_ratio, 2),
        'emotional_ratio': round(emotional_ratio, 2),
    }


def main():
    parser = argparse.ArgumentParser(description='AI 味检测门（5 维模型）')
    parser.add_argument('file', nargs='?', help='文章文件路径')
    parser.add_argument('--threshold', type=int, default=45,
                        help='阈值（默认 45，≤45 通过）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细输出')
    args = parser.parse_args()

    path = Path(args.file) if args.file else Path('wechat_article.txt')
    if not path.exists():
        # 尝试找最新的 wechat_article_*.txt
        candidates = sorted(Path.cwd().glob('wechat_article_*.txt'))
        if candidates:
            path = candidates[-1]
        else:
            print('❌ 未找到文章文件')
            sys.exit(1)

    text = path.read_text(encoding='utf-8')

    # 5 维评分
    burstiness_score, std_dev = score_burstiness(text)
    cliche_score, cliche_hits = score_cliche_density(text)
    vocab_score, vocab_ratio = score_vocabulary_diversity(text)
    struct_score, cv, parallel_count = score_structure_regularity(text)
    punct_score, punct_stats = score_punctuation_diversity(text)

    total = burstiness_score + cliche_score + vocab_score + struct_score + punct_score
    hanzi = len(re.findall(r'[一-鿿]', text))

    # 输出（ASCII-safe，兼容 GBK 终端）
    sep = '=' * 47
    print(sep)
    print(f'  AI Wei Jian Ce: {path.name}')
    print(f'  Zong Ping Fen: {total}/100 （Yu Zhi <= {args.threshold}）')
    print(f'  Han Zi: {hanzi}')
    print(sep)

    labels = [
        ('1.JuZhangQiFu', burstiness_score, f'std={std_dev}', 25),
        ('2.TaoHua', cliche_score, f'{len(cliche_hits)} hit(s)', 30),
        ('3.CiHui', vocab_score, f'AI ratio={vocab_ratio}%', 25),
        ('4.JieGou', struct_score, f'cv={cv},parallel={parallel_count}', 25),
        ('5.BiaoDian', punct_score, f'comma={punct_stats.get("comma_ratio","?")}', 20),
    ]
    for name, score, detail, max_s in labels:
        bar = '#' * score + '.' * (max_s - score) if max_s > 0 else ''
        print(f'  {name}: {score:2d}/{max_s} {bar}  {detail}')

    verdict = 'PASS' if total <= args.threshold else 'BLOCK'
    print(sep)
    print(f'  VERDICT: {verdict} (threshold={args.threshold})')
    print(sep)

    if cliche_hits and args.verbose:
        print(f'\n  套话命中:')
        for pattern, count in cliche_hits:
            print(f'    「{pattern}」×{count}')

    if total > args.threshold:
        sys.exit(1)


if __name__ == '__main__':
    main()
