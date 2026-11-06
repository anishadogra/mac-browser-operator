# Input recipes

Identify the control first, then use its recipe. Read every value back from the page, and compare hashes for long text (`await __bo.sha(text)`; JS `.length` counts an emoji as 2, so lengths mislead). All helpers come from `scripts/js/bo_core.js`.

| Control | Seen on | Recipe | Read back |
|---|---|---|---|
| Plain input or textarea in a React app | Instagram comments, Workday fields, Flow names, LinkedIn dates | `__bo.setValue(el, v)` (native setter, then input and change events) | re-query the element, then `.value` (React redraws it) |
| Lexical editor `[data-lexical-editor]` | WhatsApp composer, Instagram DMs | `__bo.paste(el, text)` | `__bo.readEditor(el)` |
| ProseMirror or Tiptap | LinkedIn post, Flow prompt box | LinkedIn: `__bo.paste(el, text, {html: __bo.linesToHtml(text)})`. Flow: `__bo.insertText(el, text)` at the caret end | join `:scope > p` textContent |
| Gmail body | Gmail compose and reply | `__bo.insertText(body, text, {replace: true})` | `innerText` with `\n{3,}` collapsed to `\n\n` |
| Recipient fields that turn into chips | Gmail To | insertText the address, then focus the next field so it blurs into a chip; Return picks a suggested contact | visible `[email][data-hovercard-id]` outside `[role=listbox],[role=option]` |
| react-select | Greenhouse | click, type, Enter | `[class*=singleValue]` |
| Workday single select | Workday | click the button, find the visible `[role=option]` with the exact text, `__bo.fire(option)` | the button's aria-label |
| Workday multi-select search | Workday Skills | `__bo.setValue`, a real Enter, wait 3 s, a real Enter | `[data-automation-id=selectedItem]` |
| Country and phone pickers | Greenhouse, Lever | type the country, ArrowDown, check the focused option's text, Enter; then the phone digits as real key presses | the visible value and `aria-invalid` |
| Menu-style time pickers | LinkedIn schedule | open the input, click the `menuitemradio` option | the "Posting at…" line |
| Buttons that ignore synthetic clicks | Flow generate, LinkedIn "Start a post", WhatsApp's document preview Send | a real click: `computer left_click`, or `safari.py click` | the next state appears |
| Buttons that accept dispatched events | Gmail Send, menus, toggles | `__bo.fire(el)` (mousedown, mouseup, click) | toast or state change |

## Files
- Your own input: `__bo.fileInput('bo-file')`, then `find "bo-file upload"`, then `file_upload` absolute paths.
- The app's own input: run `__bo.parkPickers()` before clicking the app's upload button. The input it creates is parked in the page (aria-label "bo parked file input") and no macOS picker opens. Then `file_upload` into it, or `__bo.feed(__bo.parked, files)`.
- Lexical composers take files by paste: `__bo.pasteFiles(editor, input.files)` (WhatsApp opens its media editor).
- Downloads without dialogs: `__bo.hookDownloads()` records the blob behind the app's own download click in `__bo.downloads`; read it out with `safari.py pull` or FileReader slices.

## Gates that caught real mistakes
- Account in the title or slot; recipient chip equal to the expected address; composer empty before a paste; text hash after it; exactly one compose window; no dialog open; no earlier message of ours in the chat; attachment name and size; no visible `[role=progressbar]`.
- After every `focus()`, check `document.activeElement`. A minimised compose takes the keys silently and every step still says "ok".
- A Submit that does nothing usually means a hidden required field: `document.querySelectorAll(':invalid')` names it.
- Small helper text under a field ("Please mention it in USD") changes the answer. Read it.

## Recon on a site with no playbook (about 10 minutes)
1. Find the editors: `[contenteditable]`, `[data-lexical-editor]`, `.ProseMirror`, react-select, shadow roots.
2. Find stable handles: aria-label, role, name, data-testid, componentkey. Obfuscated class names change week to week.
3. Try a dispatched click on a harmless control to learn whether the app accepts synthetic events.
4. Look for app state: `window.require` (Meta apps), React fiber props (`__bo.fiber(el, 'propName')`), JSON inside `<script>` tags, the app's own read-only endpoints called with `fetch` from the page.
5. Write the first ledger lines (`learn.py add --site <new-site>`), and a playbook after the second run.
