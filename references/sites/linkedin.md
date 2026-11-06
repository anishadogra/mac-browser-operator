# LinkedIn

## Reading the feed
- Posts are `[role="listitem"][componentkey^="update-card-focus"]`, and the scroll container is `<main>`. `innerText` already holds the full post, even behind "… more".
- Loading more needs real wheel events: jump with JS close to the bottom (`main.scrollTop = main.scrollHeight - main.clientHeight - 600`), then one `computer scroll` of 10 ticks. About half the cycles load the next 5 posts; repeat.
- Counts: innerText of `[aria-label^="Reaction button"]`, `[aria-label="Comment"]` and `[aria-label="Repost"]`. Images are `img[alt="View image"]`; documents show "· N pages"; albums show "1/N".
- Keep items in `window.__feed` keyed by componentkey, and read about 45 posts per `get_page_text` pass.

## Posting live (after the person's go)
1. Duplicate check: `/in/me/recent-activity/all/` must not already show the caption's first line.
2. "Start a post" opens only with a real click.
3. Caption: `__bo.paste(editor, text, {html: __bo.linesToHtml(text)})` into the Tiptap `[contenteditable]`, then compare the joined `:scope > p` text with the source. Dialogs recreate the editor, so re-query it every time.
4. Files: run `__bo.parkPickers()` first. Images and video: Media › "Upload from computer", `file_upload` into the parked input, Next. PDF: "+" › Document (ref click) › Choose file; the document title is required and holds 58 characters at most. Polls: question up to 140 characters, options up to 30.
5. Video loads only in a visible tab. Front it by a unique title (`references/chrome-extension.md`).
6. Before Post, re-read the caption length. Click Post once. If unsure whether it went, read recent activity before anything else.
- On any failure before Post: close the composer and choose Discard (skip "Save as draft").

## Scheduling inside LinkedIn (only when the person asks for it)
- The clock icon opens "Schedule post". Date: the `mm/dd/yyyy` input through the value setter plus input and change events. Time: open the input and click the `menuitemradio` option such as "9:30 AM". Check the "Posting at…" line, Confirm, then Schedule.
- Leftover-draft trap: closing "View scheduled posts" returns to a composer that still holds the last post with a live Schedule button. Discard it, reload, and confirm the scheduled count is unchanged.

## Job search
- Ambiguous place names geocode to the US with plausible results ("Delhi" returned Cincinnati jobs). Always write "City, Country" and spot-check the returned locations.
