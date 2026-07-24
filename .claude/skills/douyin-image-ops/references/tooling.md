# Tooling Notes

Use these notes when the user asks how to produce images at scale.

## Recommended Stack

### Fastest Start

- Direct AI image generation inside Codex for sample covers and visual directions.
- Fabritor or yft-design for Chinese text, cover layout, and export.

### Long-Term Local Workflow

- ComfyUI for repeatable AI image workflows and batch generation.
- yft-design for poster, cover, article long image, and template-based layout.
- Fabritor for lightweight Fabric.js-based image editing and template export.

## Open-Source Tool Roles

- ComfyUI: node-based AI image workflow, good for repeatable pipelines and API-style production.
- AUTOMATIC1111 stable-diffusion-webui: mature Stable Diffusion UI with a large extension ecosystem.
- Fooocus: simple prompt-to-image workflow, good for low-friction image generation, less ideal for deep automation.
- InvokeAI: creator-oriented image workspace with canvas/editing workflows.
- yft-design: Chinese online design editor suited to posters, ecommerce images, article long images, and covers.
- Fabritor: Fabric.js image editor suited to posters, Xiaohongshu/WeChat covers, banners, text styling, and export.

## Practical Advice

- Do not put Chinese text directly into AI-generated images when precision matters. Generate clean background/character images, then add text in a design editor.
- Keep a reusable visual system: 2-3 fonts, 3-5 colors, fixed cover hierarchy, fixed page count.
- Save prompts and template JSON when tools support it.
- For a new account, ship 20-30 test posts before over-optimizing tooling.

## When To Avoid Tooling

- If the user only needs a first test batch, generate images directly and deliver prompts.
- If the user has no GPU or weak hardware, avoid local Stable Diffusion setup at first.
- If the user has no validated niche, do not spend time building automation before content-market fit.
