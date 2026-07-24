# Publishing Workflow

Use this before browser-assisted Douyin publishing.

## Browser Choice

Use the `chrome:control-chrome` skill when it is available. This local setup has been checked with the Codex Chrome plugin and should be treated as the preferred publishing surface for Douyin account work.

Prefer the user's Chrome browser for real account operations:

- Better persistence for login cookies and account sessions.
- Easier QR-code login with the user's existing environment.
- Better compatibility with password managers, downloads, and file pickers.
- More suitable for repeated publishing and data review.

Use the in-app browser only for:

- Quick page checks.
- One-off tests.
- Viewing public pages.
- Low-risk workflows where login persistence does not matter.

Do not rely on the in-app browser to preserve passwords or long-term account history.

## Login Rules

- Prefer QR-code login from the user's Douyin mobile app.
- Do not ask the user to paste passwords, SMS codes, cookies, or tokens into chat.
- If a password or verification code is required, let the user enter it directly in the browser.
- Do not save passwords or payment methods unless the user explicitly asks at that moment.

## Official Entry

Use Douyin's official creator/publishing site when available, such as the Douyin Creator Service Platform. If the web UI cannot publish image posts for the current account, stop and report the limitation instead of trying risky workarounds.

## Publish Gate

Before the final publish or scheduled-publish submission action, summarize:

- Account shown in the browser.
- Title/caption.
- Image count.
- Visibility and schedule setting.
- Hashtags.
- Any platform warnings.

Ask for explicit confirmation before clicking the final publish, schedule, or submit button.

## After Publish

Record:

- Published URL or visible post identifier when available.
- Publish time.
- Title/caption.
- Assets used.
- Any warnings or errors.

Do not delete, edit, pin, change account settings, or reply to comments without separate confirmation.
