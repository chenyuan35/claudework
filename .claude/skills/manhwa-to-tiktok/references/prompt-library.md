# 韩漫 Prompt 库 v1.0

> 每次执行后补充已验证的 prompt。新增一条时带日期和质量评分。

---

## 模板结构

每条记录包含：
- **题材-镜头类型** + 版本号
- **场景描述**
- **使用的完整 prompt**
- **Agens输出质量**（⭐⭐⭐⭐⭐）
- **问题/改进**
- **修改后 prompt**
- **结果**

---

## 各题材 Base Prompt 框架

### 重生/回归（Regression）
```
base_prompt = (
    f"{scene_description}, {camera_angle}, "
    f"character: {character_desc}, "
    f"{mood_vibe}, "
    f"Korean webtoon style, manhwa art, full color digital painting, "
    f"soft cinematic lighting, elegant slender proportions, "
    f"detailed expressive eyes, clean lineart, glossy rendering, "
    f"sophisticated color palette, smooth skin texture, "
    f"fashion-forward clothing style, "
    f"{palette}, "
    f"no text, no watermark, no chibi, no anime style"
)
```

### 霸凌/复仇（Bullied → Revenge）
```
base_prompt = (
    f"{scene_description}, {camera_angle}, "
    f"character: {character_desc}, "
    f"{mood_vibe}, "
    f"Korean webtoon style, manhwa dark tone, high contrast, "
    f"muted navy and slate grey palette, dramatic shadows, "
    f"cinematic lighting, slender proportions, detailed eyes, "
    f"clean sharp lineart, glossy highlights on tears/sweat, "
    f"no text, no watermark, no anime style"
)
```

### 浪漫/心动（Romance）
```
base_prompt = (
    f"{scene_description}, {camera_angle}, "
    f"character: {character_desc}, "
    f"{mood_vibe}, "
    f"Korean webtoon style, manhwa romance art, "
    f"soft warm lighting, dreamy atmosphere, bokeh background, "
    f"dusty rose and lavender palette, soft pink gradient, "
    f"slender elegant proportions, detailed glossy eyes, "
    f"clean lineart, smooth skin, glowing skin texture, "
    f"no text, no watermark, no anime style"
)
```

### 系统/面板（System UI）
```
base_prompt = (
    f"{scene_description}, {camera_angle}, "
    f"character: {character_desc}, "
    f"floating holographic game interface overlay, status window, "
    f"{mood_vibe}, "
    f"Korean webtoon style, manhwa fantasy, "
    f"vibrant neon blue and dark contrast, sci-fi UI elements, "
    f"cinematic lighting, slender proportions, detailed eyes, "
    f"clean sharp lineart, glossy rendering, "
    f"no text, no watermark, no anime style"
)
```

---

## 已验证的 Prompt 记录

> ⚠️ 空——等第一次执行后填充
