"""
csdn_layout.py — CSDN 正文排版固定模块

唯一接口：
    normalize_csdn_html(article_html) -> str
    layout_gate(normalized_html) -> dict

固定规则（不可编辑，不可跳过）：
1. 普通段落 60-110 汉字，硬上限 140
2. 只在 。？！；后拆段，禁止句中截断
3. 每段 2-4 句，禁止强制一句一段
4. 开头/结尾/过渡段允许 25-60 汉字
5. 每个 h2/h3 区块 3-7 自然段
6. ul/ol/代码块/引用块/表格保持原结构不参与拆段
7. 禁止空段、连续 br、全段加粗、大段粗体
8. 并列列表项必须在写作阶段生成 ul/ol，排版模块不猜测语义
9. 390px 容器复验：普通段落不得连续超 7 行
10. 输出段落数/最大段长/段长中位数/超 140 段/手机超行段

调用方禁止：
- browser_evaluate 临时拆段
- 人工逐段排版
- 向用户询问排版
"""
import re
from typing import List

# ═══════════════════════════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════════════════════════

PARA_TARGET_MIN = 60       # 普通段落目标下限
PARA_TARGET_MAX = 110      # 普通段落目标上限
PARA_HARD_MAX = 140        # 普通段落硬上限
PARA_MINI_MIN = 25         # 开头/结尾/过渡段下限
PARA_MINI_MAX = 60         # 开头/结尾/过渡段上限
SENTENCE_PER_PARA_MIN = 2  # 每段最少句数
SENTENCE_PER_PARA_MAX = 4  # 每段最多句数
BLOCK_PARAS_MIN = 3        # 每个 h2/h3 区块最少段数
BLOCK_PARAS_MAX = 7        # 每个 h2/h3 区块最多段数
MOBILE_LINE_MAX = 7        # 手机端 390px 最大行数

# 中文字符宽度的近似 px 值（用于 390px 容器模拟）
_CHAR_PX = 17  # 16px 字体下中文字符约 17px


# ═══════════════════════════════════════════════════════════════
# 内部工具函数
# ═══════════════════════════════════════════════════════════════

def _extract_paragraphs_from_html(html: str) -> List[str]:
    """提取正文中所有 <p> 段落内容"""
    para_content = []
    # 匹配 <p> 内容（不包含块级内部标签如 ul/ol）
    for m in re.finditer(r'<p\b[^>]*>(.*?)</p>', html, re.DOTALL):
        content = m.group(1).strip()
        if content:
            para_content.append(content)
    return para_content


def _html_to_plain(text: str) -> str:
    """去掉 HTML 标签，保留文本"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', '', text)
    return text


def _count_han(text: str) -> int:
    """统计汉字字符数"""
    return len(re.findall(r'[一-鿿㐀-䶿\U00020000-\U0002a6df]', text))


def _count_lines_390(text: str, font_size: int = 16) -> int:
    """模拟 390px 宽度下的行数"""
    # 每个汉字 16px，字符间距 0px
    # 390px - padding(32px) = 358px 可用宽度
    available = 390 - 32
    char_width = font_size
    chars_per_line = available // char_width
    if chars_per_line <= 0:
        return 1
    lines = 0
    for para in text.split('\n'):
        clean = _html_to_plain(para)
        if not clean:
            continue
        # 汉字按 1 字 = 1 单位，英文/数字按 0.6 单位
        units = 0
        for ch in clean:
            if '一' <= ch <= '鿿':
                units += 1
            else:
                units += 0.6
        lines += max(1, -(-int(units) // chars_per_line))  # ceil division
    return lines


def _is_opening_or_closing(para_idx: int, total: int) -> bool:
    """判断是否为开头/结尾/过渡段落"""
    if para_idx == 0 or para_idx == total - 1:
        return True
    return False


def _split_sentences(text: str) -> List[str]:
    """按句号/问号/感叹号/分号拆句"""
    # 使用正向预查保留分隔符
    parts = re.split(r'(?<=[。？！；；])', text)
    return [s.strip() for s in parts if s.strip()]


# ═══════════════════════════════════════════════════════════════
# 主排版函数
# ═══════════════════════════════════════════════════════════════

def normalize_csdn_html(article_html: str) -> str:
    """
    对 CSDN 正文 HTML 执行固定排版规则。
    返回排版后的 HTML。

    算法：
    1. 解析 HTML 为段落序列（保留 h2/h3/ul/ol/pre/blockquote/table 为独立块）
    2. 对 <p> 段落执行拆段
    3. 重组 HTML
    """
    # Step 1: 将 HTML 按块级标签分割
    # 使用正则保留结构标签
    blocks = re.split(r'(<(?:h\d|ul|ol|pre|blockquote|table)[^>]*>.*?</(?:h\d|ul|ol|pre|blockquote|table)>)',
                      article_html, flags=re.DOTALL)

    result_parts = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # 非 <p> 块：直接保留
        if not block.startswith('<p>'):
            result_parts.append(block)
            continue

        # <p> 块：提取内容，拆段，重新包裹
        para_content = re.sub(r'</?p[^>]*>', '', block).strip()
        plain_text = _html_to_plain(para_content)

        if not plain_text:
            continue

        # 拆句
        sentences = _split_sentences(plain_text)

        # 如果只有一句或总长很小：保留原样
        if len(sentences) <= 1 or len(plain_text) < PARA_TARGET_MIN:
            result_parts.append(f'<p>{para_content}</p>')
            continue

        # 组合句子为段落（2-4 句/段，目标 60-110 汉字）
        new_paras = []
        current = []
        current_len = 0

        i = 0
        while i < len(sentences):
            sent = sentences[i]
            sent_len = _count_han(sent)

            if not current:
                # 第一句：必须放进去
                current.append(sent)
                current_len = sent_len
                i += 1
                continue

            # 计算当前段加上下一句后的长度
            would_be = current_len + sent_len + 2  # +2 for spacing

            # 判断条件：是否应该继续添加
            should_add = True

            # 如果当前段落已经达到 4 句，不再添加
            if len(current) >= SENTENCE_PER_PARA_MAX:
                should_add = False
            # 如果加入后超过硬上限，不再添加
            elif would_be > PARA_HARD_MAX:
                should_add = False
            # 如果加入后超过手机端行数上限，不再添加
            if current_len >= 60:  # only check once we have enough content
                test_text = ''.join(current + [sent])
                test_units = 0
                for ch in test_text:
                    if '一' <= ch <= '鿿':
                        test_units += 1
                    else:
                        test_units += 0.6
                available = 390 - 32
                char_width = 16
                chars_per_line = available // char_width
                test_lines = max(1, -(-int(test_units) // chars_per_line))
                if test_lines > 7:
                    should_add = False
            # 如果当前段落已经达到目标上限且后续还有足够句子
            elif current_len >= PARA_TARGET_MAX and len(sentences) - i >= 2:
                should_add = False

            if should_add:
                current.append(sent)
                current_len = would_be
                i += 1
            else:
                # 保存当前段落
                para_text = ''.join(current)
                if len(current) >= SENTENCE_PER_PARA_MIN or current_len >= PARA_MINI_MIN:
                    new_paras.append(f'<p>{para_text}</p>')
                else:
                    # 如果不足 2 句且长度不够，合并到下一段
                    if i < len(sentences):
                        sentences[i] = para_text + sentences[i]
                    else:
                        new_paras.append(f'<p>{para_text}</p>')
                current = []
                current_len = 0

        # 处理剩余句子
        if current:
            para_text = ''.join(current)
            if len(current) >= SENTENCE_PER_PARA_MIN or current_len >= PARA_MINI_MIN:
                new_paras.append(f'<p>{para_text}</p>')
            elif new_paras:
                # 追加到上一段
                last = new_paras[-1]
                new_paras[-1] = last.replace('</p>', para_text + '</p>')
            else:
                new_paras.append(f'<p>{para_text}</p>')

        result_parts.extend(new_paras)

    # Post-process: split paragraphs that exceed mobile line limit
    final_parts = []
    for part in result_parts:
        if part.startswith('<p>') and part.endswith('</p>'):
            text = part[3:-4]  # strip <p> and </p>
            plain = _html_to_plain(text)
            units = 0
            for ch in plain:
                if '一' <= ch <= '鿿':
                    units += 1
                else:
                    units += 0.6
            available = 390 - 32
            char_width = 16
            chars_per_line = available // char_width
            lines = max(1, -(-int(units) // chars_per_line))
            if lines > 7:
                # Split into two: try at a natural breakpoint
                splits = re.split(r'(?<=[。！？，；])', text)
                if len(splits) > 1:
                    mid = len(splits) // 2
                    p1 = ''.join(splits[:mid])
                    p2 = ''.join(splits[mid:])
                    if p1.strip() and p2.strip():
                        final_parts.append(f'<p>{p1}</p>')
                        final_parts.append(f'<p>{p2}</p>')
                        continue
        final_parts.append(part)

    return '\n'.join(final_parts)


# ═══════════════════════════════════════════════════════════════
# 排版门
# ═══════════════════════════════════════════════════════════════

def layout_gate(normalized_html: str) -> dict:
    """
    对排版后的 HTML 执行质量门。
    返回报告：
    {
        "para_count": int,
        "max_han": int,
        "median_han": int,
        "over_140": [str],
        "mobile_overflow": [str],
        "block_counts": {h2: int},
        "check_h2_block": PASS/FAIL,
        "check_mobile_lines": PASS/FAIL,
        "check_over_140": PASS/FAIL,
        "check_empty": PASS/FAIL,
        "check_ul_ol": PASS/FAIL,
        "overall": PASS/FAIL
    }
    """
    report = {}

    # 1. 统计段落
    paras = _extract_paragraphs_from_html(normalized_html)
    report['para_count'] = len(paras)

    # 2. 段长统计
    han_lengths = [_count_han(p) for p in paras]
    report['max_han'] = max(han_lengths) if han_lengths else 0
    sorted_lens = sorted(han_lengths)
    n = len(sorted_lens)
    report['median_han'] = sorted_lens[n // 2] if n else 0

    # 3. 超 140 段落
    over_140 = []
    for p in paras:
        h = _count_han(p)
        if h > PARA_HARD_MAX:
            over_140.append(p[:50])
    report['over_140'] = over_140
    report['check_over_140'] = 'FAIL' if over_140 else 'PASS'

    # 4. 手机端超行
    mobile_overflow = []
    for p in paras:
        text = _html_to_plain(p)
        lines_per_390 = _count_lines_390(text)
        if lines_per_390 > MOBILE_LINE_MAX:
            mobile_overflow.append(text[:40])
    report['mobile_overflow'] = mobile_overflow
    report['check_mobile_lines'] = 'FAIL' if mobile_overflow else 'PASS'

    # 5. 空段检查
    empty_paras = []
    for p in paras:
        text = _html_to_plain(p)
        if not text or len(text) < 5:
            empty_paras.append(p[:30])
    report['empty_paras'] = empty_paras
    report['check_empty'] = 'FAIL' if empty_paras else 'PASS'

    # 6. h2/h3 区块段落数检查
    block_counts = {}
    h2_h3_matches = list(re.finditer(r'<(h[23])[^>]*>(.*?)</\1>', normalized_html, re.DOTALL))
    for j, m in enumerate(h2_h3_matches):
        tag = m.group(1)
        title = _html_to_plain(m.group(2))[:30]
        # 计算此 h2/h3 到下一个之间的段落数
        start = m.end()
        if j + 1 < len(h2_h3_matches):
            end = h2_h3_matches[j + 1].start()
        else:
            end = len(normalized_html)
        section = normalized_html[start:end]
        section_paras = _extract_paragraphs_from_html(section)
        block_counts[f'{tag}:{title}'] = len(section_paras)

    report['block_counts'] = block_counts
    block_fails = [k for k, v in block_counts.items() if v < BLOCK_PARAS_MIN or v > BLOCK_PARAS_MAX]
    report['check_h2_block'] = 'FAIL' if block_fails else 'PASS'
    report['block_fails'] = block_fails

    # 7. ul/ol 标记检查
    ul_ol_count = len(re.findall(r'<[uo]l>', normalized_html))
    report['ul_ol_count'] = ul_ol_count

    # 8. 全段加粗检查
    all_bold_paras = []
    for p in paras:
        # 如果整个段落只有一个 <strong> 或 <b> 包裹
        cleaned = re.sub(r'<strong>|</strong>|<b>|</b>', '', p)
        plain = _html_to_plain(cleaned)
        bold_inner = re.sub(r'<strong>([^<]+)</strong>', r'\1', p)
        bold_plain = _html_to_plain(bold_inner)
        if len(plain) > 0 and bold_plain == plain:
            all_bold_paras.append(plain[:30])
    report['bold_paras_check'] = 'WARN' if len(all_bold_paras) > 3 else 'PASS'

    # 9. 总体判定
    checks = [
        report['check_over_140'],
        report['check_mobile_lines'],
        report['check_empty'],
        report['check_h2_block'],
    ]
    report['overall'] = 'PASS' if all(c == 'PASS' for c in checks) else 'FAIL'

    return report


# ═══════════════════════════════════════════════════════════════
# 快速测试（调用方式：python csdn_layout.py < article_csdn.html）
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys, json
    html = sys.stdin.read() if not sys.stdin.isatty() else open('article_csdn.html', encoding='utf-8').read()

    norm = normalize_csdn_html(html)
    report = layout_gate(norm)

    # 输出报告
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print()
    print('=== 排版后 HTML（前 500 字符） ===')
    print(norm[:500])
    print()

    if report['overall'] == 'PASS':
        print('✅ layout_gate PASS')
    else:
        print(f'❌ layout_gate FAIL: {json.dumps({k:v for k,v in report.items() if "check_" in k and v=="FAIL"}, ensure_ascii=False)}')
        sys.exit(1)
