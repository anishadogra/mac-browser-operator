# Browser Operator profile

Claude reads this before every browser task. Keep it short and current; edit it whenever an account or a rule changes.

## Browsers
- Chrome (Claude in Chrome extension) deviceId: <paste from list_connected_browsers, or "only one connected">
- Accounts signed in to that Chrome: <emails; Gmail slot numbers if known, which move when accounts change>
- Safari: <which logins live there, for example personal WhatsApp Web>

## Accounts per job
| Job | Browser | Account | How to verify |
|---|---|---|---|
| Work email | Chrome | you@company.com | Gmail tab title contains the address |
| Personal WhatsApp | Safari | your phone number | `wa.py status` shows CONNECTED |

## Standing permissions (what Claude may do without asking first)
Write each one as exact as possible. Sends, posts and submits still need a go in the chat unless a line here says otherwise.
- Example: open Chrome Gmail to send emails I approved in chat (each batch still needs my "send").
- Example: when a build is finished, send the file to my own "Message yourself" chat on WhatsApp.

## People Claude may message when I say so
| Name | Where | How to find | Check |
|---|---|---|---|
| Me (notes to self) | Safari WhatsApp | `wa.py send-file --to self` | self chat id from `wa.py self` |

## Never
- Type my passwords, sign in or out for me, accept terms or tick consent boxes without my yes.
- Message anyone new, or anyone twice, without my go.
