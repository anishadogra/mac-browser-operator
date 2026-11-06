# Gmail web

## Account
- Open `https://mail.google.com/mail/u/<N>/` for the account named in `profile.md`, and gate every step on `document.title` containing the address. The title can read just "<Organisation> Mail" for a moment between views, so poll before failing.
- Slots move when accounts are added or removed; `?authuser=` falls back to u/0 without warning.
- The Gmail connector rewrites links into google.com redirects and cannot attach local files. Mail that carries a link goes from Gmail web.

## One email
1. Go to `#inbox?compose=new` and wait for exactly one `input[name="subjectbox"]`. A compose shorter than 300 px is minimised: expand it first.
2. To: focus `input[aria-label="To recipients"]`, insertText the address, then focus the subject so it becomes a chip. Count only real chips: visible `[email][data-hovercard-id]` outside `[role=listbox],[role=option]`. With an "outside your organisation" warning the chip has no email attribute; read `div[aria-label="To"]` instead. Gmail rewrites a known gmail.com address to its dotted form; dots do not matter there.
3. Subject: focus, `select()`, insertText. Body: focus `div[aria-label="Message Body"]`, `execCommand('selectAll')`, insertText. Gate: subject equal, body equal after collapsing `\n{3,}` to `\n\n`, chips equal to [address].
4. Wait 3 s, then Send: dispatched mousedown, mouseup and click on the compose's `div[role=button][aria-label^="Send"]` (or cmd+Enter with the body focused).
5. Done means the compose closed AND the toast says "Message sent" (with "Sending…" gone).
6. Verify: `#search/in:sent to:<addr> after:<local midnight epoch>` shows exactly one row with the subject. Rows show "me", so match on the subject.

## Many emails: `scripts/js/gmail_runner.js`
Approved list as a JSON file `[{"to": …, "s": subject, "T": body}]`.
1. Set `window.__ACCOUNT = '<sending address>'`, inject the runner, run `__dataInput()`.
2. `find "bo send list upload"`, `file_upload` the JSON, then `await __load('<sha256 of the file>')`.
3. `__chunk(0, 25)`, then poll `__RUN` and `__col(0, 25)` every 2 minutes (a batch of 11 ten-second waits plus one read), log each verified row with `actlog.py`, start the next chunk.
- About 11 s per message, with a recipient check before each send.
- Any throw stops the chunk before the next compose. Fix that row, then `__chunk(next, end)`.
- Leave 8 to 12 s between sends. At about 1 s per email, some composes closed and never sent.
- Keep the Gmail tab in front for the whole run, and do WhatsApp sends before or after it.

## Traps and recoveries
- "Message could not be sent. Check your network": look in Sent first (it has always been 0), wait for the banner to clear (15 to 35 s), refill the reopened draft, re-gate, send once, then confirm `in:drafts` is empty.
- "Still sending…" can end in nothing: check Sent AND Drafts before any resend.
- "#2008 / the system encountered a problem" makes every search return nothing. Gate on that text and never resend on "not in Sent" while it shows. Do a real `location.reload()` (a `#hash` change keeps the same page), then re-inject helpers. It has lasted up to 1.5 hours.
- Gmail skips a search it is already showing: move `after:` by one second per retry.
- Fast searches can read rows before Gmail paints them: mark the old rows stale and wait for fresh rows with subjects.
- Dedupe search: `{to:a from:a to:b from:b}`. Bare addresses get split into words and match everything. Test with two known contacts first.
- Bounces arrive within 15 s to an hour, sometimes as their own "Delivery Status Notification" thread: sweep `after:<epoch> -in:sent`. Ticket systems auto-acknowledge (delivery only). Challenge-response filters hold mail until someone replies, and that reply needs the person's go.
- Links: put the full `https://` URL on its own line; Gmail links it. Check the Sent body for the `<a href>`.
- Schedule send only when the person names a time: More send options › Schedule send › Select date and time (`input[aria-label="Date"]` like "14 Oct 2026", `input[aria-label="Time"]` in 24 h).
- Attachments over 10 MB in a reply: split into 4 MB parts, chunk-upload and assemble with a SHA check, put the File into the reply's own `input[type=file][name="Filedata"]` with a DataTransfer plus a change event, and wait until no `[role=progressbar]` remains.
