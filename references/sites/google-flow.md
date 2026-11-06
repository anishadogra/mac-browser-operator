# Google Flow (images)

- Works in Chrome through the extension and in Safari through `safari.py`. In Safari most action buttons need real clicks.
- Real clicks needed: Start generation, @-picker options, the model dropdown, New project, Add media › Upload, and Create body and Done for characters. JS clicks work for sidebar navigation, Download media, the 1K and 2K menu items, Next media, thumbnails and settings toggles.
- Prompt boxes are ProseMirror `[contenteditable=true]`: focus, put the caret at the end, insertText. Once @ chips are in the box, avoid select-all and delete.
- Attaching an asset: type "@", set the picker's "Search assets" input with the value setter, wait about 2 s, real-click the single `[role=option]`. Gate on the `.mention-chip` names before every send; a silent attach failure once changed a character's look. The agent also resolves references by name ("Reference image from my uploads: '<file name>'").
- Upload without a dialog: `__bo.parkPickers()`, open Add media › Upload, then feed the parked input (`safari.py push` plus `__bo.feed`, or `file_upload` in Chrome). The rights dialog's "I agree" needs the person's yes once per build.
- Settings: default aspect ratio and output count live in `flow-toggles[aria-label=…] button[role=radio]` (JS clicks work). Keep "Confirm before generating" on Always.
- Busy: a visible "stop" button means the agent is still working, and Flow keeps rendering after the agent replies, so wait for the new tile count. Skip "go ahead" nudges; one was rendered as an image caption.
- One agent message with numbered scenes returns all of them (10 in about a minute). Up to 3 agent sessions run in parallel; a fourth reports "Other sessions are currently running".
- Originals: a grid `img` src ends `=s512-rw`; swap that tail for `=s0` and pull it (`safari.py pull`, or an in-page fetch). The 2K upscale download cost 0 credits; capture it with `__bo.hookDownloads()` to keep ~/Downloads clean.
- Map outputs to scenes by the exact quoted headline in the stored prompt; grid order follows generation, not your scene list.
- Image models carry a daily quota per account ("You've reached your usage limit"). Read the agent's reply before blaming a script.
- Prompt traps: asking for a "simple top band" draws literal bars; describing a font for text that should not appear prints the description. Keep logos clear of Flow's bottom-right sparkle mark.
- `performance.getEntriesByType('resource')` stops at 250 entries; call `performance.setResourceTimingBufferSize(3000)` first.
- New characters: gate every step on the page state. "Done" does not always navigate away, and a batch once renamed the previous character. Name a page only while its name field reads "Untitled character".
