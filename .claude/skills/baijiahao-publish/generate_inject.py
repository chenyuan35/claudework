import re

with open(r'C:\Users\59314\claudework\.claude\skills\baijiahao-publish\article.html', encoding='utf-8') as f:
    html = f.read()

# Escape backticks, backslashes, and ${} for JS template literal
escaped = html.replace('\\', '\\\\')
escaped = escaped.replace('`', '\\`')
escaped = escaped.replace('${', '\\${')

js_func = "() => { UE_V2.instants['ueditorInstant0'].setContent(`" + escaped + "`); }"

with open(r'C:\Users\59314\claudework\.claude\skills\baijiahao-publish\inject.js', 'w', encoding='utf-8') as f:
    f.write(js_func)

print('inject.js written, length:', len(js_func))
