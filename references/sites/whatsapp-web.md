# WhatsApp Web

Two proven routes. Personal WhatsApp in Safari runs through WhatsApp Web's own modules: fast, no UI clicks, no read receipts. WhatsApp Business in Chrome runs through the UI with paste and hash gates.

## A · Safari, personal account (`scripts/wa.py`)
Setup: Safari JavaScript from Apple Events on (`references/safari.md`), and web.whatsapp.com linked from the phone (WhatsApp › Settings › Linked devices). The tab can sit anywhere in Safari.

| Command | Does |
|---|---|
| `wa.py open` | adds web.whatsapp.com as a tab when none exists (ask the person first) |
| `wa.py status` | socket stream and state, chat count, visibility, the self chat |
| `wa.py wake` | fronts the tab, reloads when DISCONNECTED, waits for CONNECTED (about 15 to 25 s) |
| `wa.py find "<name regex>"` | matching chats with id, name, pushname, unread count (read-only) |
| `wa.py self` | the "Message yourself" chat |
| `wa.py recent --chat ID [--n 15]` | last messages without opening the chat |
| `wa.py send-text --to ID\|self\|+DIGITS --text-file T [--preview] [--expect-name X] --yes` | gated text send, ack check, logged |
| `wa.py send-file --to ID\|self --file F [--caption C] [--expect-name X] --yes` | sends a document with its exact bytes (no recompression), SHA-checked in the page |
| `wa.py download --chat ID --match "<filename regex>" --out DIR` | saves a received document, read-only |

Without `--yes` every send is a dry run that prints the recipient and what would go. Pass `--yes` only after the person's go in this session. `--expect-name` refuses the send unless the chat's name or pushname contains that text.

Proven facts (Oct to Nov 2026):
- Modules: `WAWebCollections` (Chat, Msg, Contact), `WAWebSocketModel`, `WAWebWidFactory`, `WAWebQueryExistsJob` (null means not on WhatsApp), `WAWebFindChatAction`, `WAWebSendTextMsgChatAction`, `WALinkify` with `WAWebLinkPreviewChatAction` (link card), `WAWebMediaOpaqueData` with `WAWebPrepRawMedia` (documents), `WAWebMediaInMemoryBlobCache`, `WAWebChatLoadMessages`, `WAWebCmd`. When one is reported missing, WhatsApp renamed it: probe `window.require` before guessing.
- `prep.sendToChat({chat, options: {caption}})` takes one object.
- ack 0 is uploading or pending, 1 sent, 2 delivered, 3 read. A 40 MB video document reaches ack 1 in about 35 s, and only while Safari is in front.
- Many contacts share a name (one search matched 15 people). Gate on the chat id plus name and pushname, and on "not a group".
- `nullthrows: me` on a send means the session signed out; a reload shows the QR code. The person relinks from their phone; never scan or link for them.
- A hidden or minimised Safari keeps the socket DISCONNECTED and loads few chats: `wa.py wake`.
- Readable chats and self ids do not prove a live session. When the stream stays DISCONNECTED with the tab in front, the session has usually dropped, and the reload in `wake` then shows the QR (seen 3 and 4 Nov 2026).
- After any interruption, inspect the existing message (`ack`, `mediaData.mediaStage`, `isSendFailure`) before resending. WhatsApp resumes a stuck upload by itself once the tab is visible, so a blind resend doubles it. wa.py counts live copies and refuses a second one.
- Message bodies in IndexedDB are encrypted. Read through the models only. For image messages `body` holds a thumbnail, so read `caption`.
- Opening a chat (`Cmd.openChatBottom`) sends blue ticks for its unread messages. Sends work without opening it; `--show` opens it on purpose.
- Older history without opening the chat: `WAWebChatLoadMessages.loadEarlierMsgs({chat})` (an object, not the chat).

## B · WhatsApp Business in Chrome (UI route through the extension)
One batch per message:
1. Navigate `https://web.whatsapp.com/send?phone=<digits>` and wait about 20 s.
2. Inject `scripts/js/wa_business.js` after setting `window.__WA_ACCOUNT_DIGITS` (the sending number) and optionally `window.__WA_OURS` (a regex matching your own earlier outreach).
3. `__waGate(digits, exactName)` throws on a dialog, a wrong account, a wrong chat, an earlier message of ours, or a non-empty composer.
4. `await __waPaste(TEXT)` returns the sha12 of the composer; compare it with the approved draft's hash.
5. Wait about 6 s for the link card, then `await __waDropBareCard()` (a card without an image repeats the URL).
6. `__waSendRect()` returns the Send button's label and centre: require the label "Send", then a real click.
7. Confirm your text in `#main` and an empty composer, then log the send.

Notes:
- Business accounts show a NAME in the header. Open Contact info, check the digits-only number there, and gate on the exact name. Gate numbers on digits only.
- A Google Maps number can belong to someone else. Prefer the number on the business's own website (`wa.me/…` links).
- Photos: `__waPhotoInput()`, `find "bo photos upload"`, `file_upload` the paths, `await __waPastePhotos(n)` until the label reads "Send n selected", real click, then confirm n blob images in the chat.
- "AI from Meta" businesses: the first Send may open a terms dialog. The message is held until OK, and OK accepts Meta's AI terms, so it needs the person's yes. After the dialog closes, re-read `#main` for your text and never paste again.
- Auto-greetings arrive within seconds. They show delivery; log them as AUTO, separate from replies.
- Read the chat list from `#pane-side` rows (`span[title]` holds the last message). Opening an unread chat marks it read for everyone using that number.
- Tip popups are `role=dialog` and block the gate: close their X first. Some days WhatsApp builds no rich card for any link; drop the bare card.
- Pace: about 2 minutes per message including logging. Keep first messages to people you have not talked to before to a small daily number.
