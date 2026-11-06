# Safari from Claude Code

## Setup (once, done by the person)
1. Safari › Settings › Advanced › tick "Show features for web developers".
2. Safari › Settings › Developer › tick "Allow JavaScript from Apple Events" (older Safari: the Develop menu).
3. On the first run macOS asks whether the app running Claude may control Safari: Allow. The switch lives in System Settings › Privacy & Security › Automation.
4. Real clicks need Accessibility for the same app (System Settings › Privacy & Security › Accessibility). `python3 scripts/doctor.py` reports both.
5. Keep page zoom at 100 % and the status bar hidden (View › Hide Status Bar) so page pixels map to screen points.

## safari.py in practice
- Tabs are chosen by a URL fragment (`-t web.whatsapp.com`), because other sessions add tabs and windows.
- Every command except `open` refuses to run while Safari is closed, so nothing launches by surprise.
- `open URL` adds a tab at the end of window 1, or makes a window when none exists. A new window would become "window 1" and send another session's JavaScript to the wrong page. A background tab stays unloaded until it is shown: pass `--front`.
- `js` evaluates one expression and prints it (objects come back as JSON). `jsf` runs a whole file, for example `scripts/js/bo_core.js`; the file's last expression is the result.
- `run -t PART body.js` takes an async body (use `await`, end with `return`). It starts the work in the page, polls until it settles and reads large results back in 900,000-character slices. Plain `do JavaScript` returns before promises settle, which is why this wrapper exists.
- Wrap risky code in try/catch and return the message; `run` already reports page errors.

## Visibility decides whether work happens
- A hidden, covered or minimised tab throttles or stops: WhatsApp drops its socket, video documents stall in PREPARING, Flow renders nothing.
- `safari.py front -t PART` unminimises the window, selects the tab and brings Safari forward. Check `document.hidden` before long work.
- When the person is using another app, say before fronting Safari that it will come forward for a moment.

## Real clicks
Some apps ignore synthetic clicks (Flow: generate, the @ picker, the model menu, upload). `safari.py click -t PART 'CSS' [--text "Exact label"]`:
1. fronts the tab, raises its window (AXRaise), and requires `document.hasFocus()` with Safari frontmost;
2. clicks the element's centre with a CGEvent, so the pointer moves on the person's screen (tell them first);
3. hands focus back to the app they were in. It tries up to 4 times and stops when they switch apps mid-click.
- The first click on an unfocused window only focuses it; the focus gates prevent that silent miss.
- `clickxy` and `key` exist for the rare case without a selector.

## Files in and out
- `safari.py push -t PART FILE --var __boFile` sends base64 in 1,000,000-character chunks (about 0.4 s each), rebuilds a `File` in the page and compares its SHA-256 with the local file.
- `safari.py pull -t PART URL OUT` fetches inside the page with its cookies (also `blob:` URLs) and writes the bytes. Google image originals: swap the `=s512…` tail for `=s0`.
- For app download buttons, inject `bo_core.js`, run `__bo.hookDownloads()`, click the app's download, then read `__bo.downloads` and pull the captured blob URL. Nothing lands in ~/Downloads.

## Housekeeping
- Every osascript call is bounded by a timeout inside the scripts. In a shell without `timeout`, `perl -e 'alarm 60; exec @ARGV' osascript …` does the same.
- `safari.py shot` captures one window with `screencapture -l`; it fails while the window is off-screen. Window titles need Screen Recording permission for the app; without it the script falls back to the frontmost Safari window.
- Scratchpad copies of helpers disappear in temp cleanups. This skill's scripts are the durable copies.
