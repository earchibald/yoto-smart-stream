# yoto-mcp

A local MCP server that lets Claude read and edit your Yoto MYO playlists. It runs on your
machine over stdio. Your Yoto tokens and the app's client secret stay in the macOS keychain, and
no tool result ever contains them.

Cards are named by title, the way the Yoto app shows them. Card ids never appear.

## Set up (once)

```bash
cd yoto-mcp
uvx --from . yoto-mcp setup            # asks for the Yoto app's client id and secret
uvx --from . yoto-mcp login Eugene     # browser login; links the account as "Eugene"
uvx --from . yoto-mcp login Family     # optional: a second family account
claude mcp add yoto -- uvx --from "$PWD" yoto-mcp serve
```

Login listens on the app's registered callback, `http://localhost/oauth/callback` by default.
Use `setup --redirect-uri …` or `YOTO_REDIRECT_URI` to change it. The first account you link
becomes the default; change it with `yoto-mcp default <name>`.

## What Claude can do

| Tool | Does |
| --- | --- |
| `yoto_whoami`, `yoto_account_link` | List linked accounts; link another one through the browser |
| `yoto_cards_list`, `yoto_card_get` | Your playlists and the family library, by title; one card as summary, outline or full |
| `yoto_card_playable` | Short-lived signed URLs for listening |
| `yoto_card_plan` → `yoto_card_apply` | Plan an edit (diff, warnings, lint), then apply it with a backup, a guard and a read-back check |
| `yoto_card_backups`, `yoto_card_restore` | Backups taken before every apply (last 20 per card), restored as a plan |
| `yoto_media_upload_file`, `_begin`, `_wait` | Upload audio; Yoto dedupes by sha256 |
| `yoto_media_import` | Copy a card's audio and icons to another account (media refs belong to one account) |
| `yoto_icon_render`, `yoto_icon_glyph`, `yoto_icon_from_image` | Draw 16×16 icons from a character grid and look at an 8× preview |
| `yoto_icon_upload`, `yoto_icons_search`, `yoto_cover_upload` | Upload icons and cover art; search your icons and Yoto's |

Every write is plan-then-apply. `yoto_card_apply` refuses a plan if the card changed since the
plan was made, if its title changed, or if the account doesn't own it. It saves a backup to
`~/.yoto/backups/`, writes, re-reads, compares, and checks that the first, last and changed tracks
play. Each apply is logged to `~/.yoto/changes.log`.

## Live checks

These answer two open questions in the design. Each writes to the default account and cleans up.

```bash
uvx --from . yoto-mcp check icons    # does an autoConvert=false icon come back pixel-identical?
uvx --from . yoto-mcp check resume   # does Yoto accept resumeTimeout: 0? (scratch card, deleted after)
```

## Develop

```bash
uv run --extra dev pytest
```

Tests run against `tests/fake_yoto.py`. It mimics what the real API did during the Hilo work:
`/content` is owner-only, `/card` returns signed URLs, foreign refs fail with 400, known uploads
get a null upload URL, transcoding is async, and refresh tokens rotate.
