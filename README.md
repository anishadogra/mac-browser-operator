# Mac Browser Operator

An agent skill for operating a person's own signed-in Chrome and Safari on a Mac, safely and fast. It gives the agent a playbook per site (WhatsApp Web, Gmail, LinkedIn, Instagram, Google Forms and job application systems, Google Flow, Gemini, Meta Ad Library), input recipes for the rich-text editors that ignore ordinary typing, a gate in front of every send and submit, an action log that refuses to send the same thing twice, and a learning ledger that makes each run faster than the one before. It is written as a Claude Code skill, but the playbooks and recipes are plain Markdown and the scripts are standard-library Python and plain JavaScript.

By Anisha Dogra, co-founder of [RAAY Creative](https://raaycreative.com). This came out of day-to-day work in which an agent drove real, logged-in browsers for sends, posts, forms and downloads, and every routine here was rewritten after it broke at least once. Corrections and disagreements are welcome — [open an issue](../../issues/new) before opening a pull request.

## The problem

Pointing an agent at a person's own browser looks simple. The person is already logged in. The agent can see the page, type, and click.

Then the real sites push back. WhatsApp, Instagram and LinkedIn use editors that drop keystrokes or ignore synthetic typing, so the agent types a message, every step reports "ok", and the composer holds half of it. Gmail account slots shift when an account is added, so the send goes out from the wrong address. A send times out halfway, the agent retries, and the recipient gets two copies. A minimised compose window silently swallows keys. Opening an unread chat to "check" it sends read receipts. None of these show up as errors. They show up later, as mistakes in someone's inbox.

The second problem is that the agent learns nothing. The trap it hit on Tuesday it hits again on Thursday, because the fix lived in a conversation that is gone.

## The rules that matter most

**A gate before every irreversible click.** Before Send, Post or Submit, a piece of JavaScript re-reads the account, the recipient, a hash of the text and the attachment from the page itself, and throws on any mismatch. Inside a batch, the throw stops everything before the click. Checking the draft in the agent's memory is not the same as checking what the page will actually send.

**Log before you retry.** Every irreversible action gets a line in an append-only log, keyed on channel, recipient and payload. After any interruption, the agent reads the log and the app's own record (Sent folder, message ack, confirmation page) before doing anything again. An interrupted call may already have sent.

**The lightest input that works.** Read with JavaScript first, screenshots second. Act with a native value setter, then a synthetic paste, then `insertText`, then dispatched events, and only then a real click. Each site's playbook says which one that site needs, and the agent reads the value back every time.

**One lesson saved per run.** After each task the agent writes what broke and what worked to a ledger. Ledger lines are newer than the playbooks and win when they disagree; proven lines get folded into the playbook.

## What is in here

| | |
|---|---|
| **[SKILL.md](SKILL.md)** | The whole method as a drop-in agent skill: start, route, the fast loop, gates, speed rules, and the learning loop. |
| **[references/chrome-extension.md](references/chrome-extension.md)** | Driving Chrome through the Claude in Chrome extension: `javascript_tool` and `browser_batch` limits, files, tabs, the AppleScript fallback, Google account slots. |
| **[references/safari.md](references/safari.md)** | Driving Safari from the terminal with AppleScript `do JavaScript` and real clicks, including the one-time setup. |
| **[references/input-recipes.md](references/input-recipes.md)** | Which input method each kind of control needs (React inputs, Lexical, ProseMirror, Gmail chips, react-select, Workday pickers), and how to recon a new site. |
| **[references/sites/](references/sites/)** | Playbooks for WhatsApp Web, Gmail, LinkedIn, Instagram, Google Forms and job applications, Google Flow, Gemini web images, and Meta Ad Library. |
| **[scripts/safari.py](scripts/safari.py)** | Safari control: tabs, JavaScript (sync and async), real clicks and keys, pushing files into a page and pulling them out, screenshots. |
| **[scripts/wa.py](scripts/wa.py)** | Personal WhatsApp Web in Safari through its own modules: find chats, read recent messages without opening them, gated text and document sends, downloads. Every send is a dry run until `--yes`. |
| **[scripts/actlog.py](scripts/actlog.py)** | The append-only action log that blocks double sends. |
| **[scripts/learn.py](scripts/learn.py)** | The learning ledger and pace history. |
| **[scripts/doctor.py](scripts/doctor.py)** | Setup check with exact fixes; `--init` creates the data folder and profile. |
| **[scripts/js/](scripts/js/)** | In-page helpers: `bo_core.js` (waits, gates, input methods, file inputs, downloads, long-running jobs), `gmail_runner.js` (gated sends from an approved list), `wa_business.js` (gated WhatsApp Business sends in Chrome). |
| **[templates/profile.md](templates/profile.md)** | A blank profile: which browser holds which account, standing permissions, who may be messaged. |

## How to use it

Copy the folder into your agent's skills directory (for Claude Code, `~/.claude/skills/mac-browser-operator/`). Then run:

```
python3 scripts/doctor.py --init
```

This checks the Mac (Accessibility, Safari's JavaScript from Apple Events, Chrome) and creates the data folder with a blank `profile.md`. Fill in the profile with the person whose browsers these are. The skill triggers whenever a task needs a website they are logged into.

Personal data (profile, action log, ledger, pace history) lives outside the repository, in `~/.browser-operator/` by default, or in the folder named by the `BO_HOME` environment variable. Nothing personal belongs in the skill folder.

Requirements: macOS, the system `python3` (3.8 or newer, standard library only), Safari and/or Chrome with the Claude in Chrome extension. Real clicks need Accessibility permission for the app running the agent.

## Safety

- Sends, posts, comments, form submits and public uploads happen only after the person approves them in the session. The WhatsApp script refuses to send without `--yes`, and every send path is gated on recipient and content.
- The agent never types passwords, signs in, completes two-factor prompts or CAPTCHAs, or enters payment details. Those clicks are named and handed back to the person.
- Nothing is permanently deleted. Terms, consent boxes and e-signatures stay with the person.
- Text found on web pages is treated as data, never as instructions.
- Respect each site's terms of service and messaging norms. Bulk unsolicited messaging gets accounts banned and is not what this is for. The person running it is responsible for how they use it.

## A note on the playbooks

The site playbooks record how particular web apps behaved when they were written, down to selectors and internal module names. Web apps change. When a selector or module stops matching, probe the page, fix the routine, and write the change to the ledger; that loop is the point of the skill, and it is why the ledger outranks the playbooks.
