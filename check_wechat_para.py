# check_wechat_para.py — 段长硬闸（烘焙前必跑）
# 用法: python check_wechat_para.py wechat_article_xxx.txt
# v2.0 — 2026-07-20 新标准：35-100 汉字/段，上限 150，无连续短段
import re, sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else 'wechat_article.txt')
t = path.read_text(encoding='utf-8')
lines = t.splitlines()
title = lines[0] if lines else ''
body = '\n'.join(lines[1:]).lstrip('\n')
paras = [p.strip() for p in body.split('\n\n') if p.strip()]

total_hanzi = len(re.findall(r'[一-鿿]', t))
imgs = sum(1 for p in paras if p.startswith('[插图：'))
subs = sum(1 for p in paras if re.match(r'^[一二三四五六七八九十]+、', p))

# 计算有效段落（不是纯分隔符 / 图占位 / 空段）
valid_paras = []
for p in paras:
    if p.startswith('[插图：') or p == '===' or p == '---' or p == '***':
        continue
    cn = len(re.findall(r'[一-鿿]', p))
    if cn > 0:
        valid_paras.append((cn, p[:60]))

over150 = [(c, s) for c, s in valid_paras if c > 150]
under20 = [(c, s) for c, s in valid_paras if c < 20]

# 检查连续短段
consec_under20 = 0
for c, _ in valid_paras:
    if c < 20:
        consec_under20 += 1
    else:
        consec_under20 = 0
    if consec_under20 >= 2:
        break

print(f'title: {title[:50]}')
print(f'hanzi={total_hanzi} sections={len(valid_paras)} imgs={imgs} subs={subs}')

# 检查超长段
if over150:
    print(f'FAIL over150={len(over150)} (limit 150 hanzi/para)')
    for c, s in over150[:5]:
        print(f'  {c}字: {s}')
    sys.exit(2)

# 检查连续短段
if consec_under20 >= 2:
    print(f'FAIL consecutive short paras (<20 hanzi)')
    sys.exit(3)

# 检查汉字范围
if not (2400 <= total_hanzi <= 2800):
    print(f'FAIL hanzi={total_hanzi} expect 2400-2800')
    sys.exit(4)

# 检查图片数
if imgs < 2 or imgs > 4:
    print(f'FAIL imgs={imgs} expect 2-4')
    sys.exit(5)

# 小标题数（建议 4-7，非硬性）
if subs < 3 or subs > 8:
    print(f'WARN subs={subs} typical 4-7')

print('PASS para gate')
