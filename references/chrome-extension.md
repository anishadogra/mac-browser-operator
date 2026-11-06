# Chrome through the Claude in Chrome extension

## Setup (once per person)
- Install the Claude in Chrome extension, sign in with the same Claude account, and keep its side panel connected.
- Several Chromes can be connected at once (other profiles, other Macs). Put the right `deviceId` in `profile.md` and pick it with `select_browser`. Display names such as "Browser 1" change; the device id stays until the extension is reinstalled.
- Before real work, confirm the account on a page that needs login. Google: `[...document.querySelectorAll('[aria-label]')].map(e => e.getAttribute('aria-label')).find(x => /Google Account/.test(x))`.
- If `list_connected_browsers` returns nothing, the person reopens Chrome or the Claude side panel. Retries change nothing.

## javascript_tool
- Write top-level code and use top-level `await`. An `(async () => {...})()` hands back `{}` before its checks finish, so a gate written that way blocks nothing.
- `throw` at top level to stop a `browser_batch` before its next step.
- One call times out at about 45 s while the page keeps running the promise. Start long work with `__bo.run` and poll `__bo.status`.
- Output limits: strings near 1,000 characters come back truncated, arrays past about 100 items too. Text that looks like `key=value`, a URL with a query, or a JWT returns `[BLOCKED: ...]`. Return arrays of short strings, print `key :: value`, strip `https://`; `__bo.safe(s)` does these swaps.
- Reading a long text: build it in the page, replace `document.body` with a `<main><article>` holding one `<p>` per paragraph (DOM calls; Trusted Types sites refuse `innerHTML`), then `get_page_text` (50,000 character cap). Reload the page afterwards.

## browser_batch
- One batch per item. A thrown gate halts it before the irreversible action (proven on Gmail and WhatsApp).
- Keep a batch to about 12 waits of 10 s plus reads. A longer batch returns "did not respond in time" while the page carries on.
- A lost connection leaves the page running. End batches with read-only checks, never with a step that changes state, and after any loss read the page state twice, about 10 s apart, before touching anything.

## Typing and clicking
- `computer type` loses focus or drops keys in rich editors (Instagram, LinkedIn). Use `input-recipes.md`.
- `computer key` sends real key events; `type` inserts text without them. Phone fields and some pickers need real keys.
- Some buttons answer only real clicks (LinkedIn "Start a post", Flow generate): `computer left_click` by ref or coordinate. Check what sits under a coordinate first with `document.elementFromPoint(x, y).closest('[aria-label]')`.
- Coordinates belong to the latest screenshot's frame and differ per screen, so prefer refs from `find`.

## Files
- An app's own attach or paperclip button opens the macOS picker, which no tool can drive. Add your own hidden input (`__bo.fileInput`) or park the app's input (`__bo.parkPickers`), then `find` it and `file_upload` absolute paths.
- `file_upload` takes up to 10 MB per call. For bigger files: `split -b 4000000 "<file>" part_` on the Mac, run `__bo.chunkInput()`, upload each part with its own `file_upload` call and run `__bo.takePart()` after each, then `await __bo.assemble(name, mimeType, sha256hex)` and feed `__bo.file` to the app (`__bo.feed(input, [__bo.file])`). Deliverables keep their exact bytes; never shrink or re-encode them to fit.
- Screenshots land in the session's `tool-results/` folder as `mcp-claude-in-chrome-blob-*.jpg`; copy them out as proof. `save_to_disk` writes nothing on some Macs.

## Tabs and windows
- Tab ids change when Chrome discards and recreates a tab (Memory Saver). Call `tabs_context_mcp` again.
- A minimised window times out screenshots and swallows clicks, while JS and key events still work. Ask the person to restore it.
- Hidden tabs throttle timers and defer media: video uploads sit on "Loading" and Gmail chips arrive a minute late. Bring the tab forward: set a unique `document.title`, then find and front it with the `Control_Chrome` tools (`list_tabs`, `switch_to_tab`) or AppleScript. Their own tab with the same URL is a different tab, so match on the unique title.
- `navigate` turns `file://` into a dead `https://file///` address and can close the tab group. Open local files with `open -a "Google Chrome" "<path>"`.

## AppleScript route (works without the extension)
- Always available: `tell application "Google Chrome" to make new tab at end of tabs of window 1 with properties {URL:"…"}`; read `URL` and `title` of every tab; `set active tab index of window 1 to N`; `activate`.
- Page JavaScript (`execute javascript`) needs Chrome › View › Developer › Allow JavaScript from Apple Events. It is the person's security setting: ask, and respect their choice.
- With two Chrome processes running (another profile), AppleScript fails with error -609.

## Google account slots
- `/mail/u/N/` and `/forms/u/N/` count the signed-in accounts in sign-in order, and adding or removing an account shifts them. Read the slots by visiting `u/0`, `u/1`, … and reading `document.title`; gate every step on the title.
- A slot showing "Verify that it's you" waits for the person to sign in.
