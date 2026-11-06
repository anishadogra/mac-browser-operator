# Google Forms and job applications

## Before Submit, every time
1. The form or posting is the right one and fits the person (region, years asked, residency, time zone).
2. Every field is read back from the page (values, react-select singleValue, the uploaded file name), and every small helper text under a field is read.
3. Opinion and personal questions ("why us", "where in five years", forms that ask for no AI) are the applicant's own words: leave them and log the form as waiting.
4. Consent ticks, terms and typed-name e-signatures need the person's explicit yes for that batch. A typed signature stays theirs.
5. Screenshot of the filled form, then Submit, then the confirmation page, then the log line.

## Google Forms
- Open `docs.google.com/forms/u/<N>/d/e/<id>/viewform`; the header must show the intended account before any typing.
- Read back values, choices and checkboxes. Success shows "Your response has been recorded".
- Forms that commit money or pick between clashing options wait for the person.

## Workday
- Sessions die after about 20 to 30 idle minutes (endless spinners, `/values/` calls answering 400, "e.map is not a function"). Tabs left open for hours fail at Submit. Work live with the person: they press Sign In (the browser fills it), you fill every step at once, and the tick and Submit follow within minutes. A new tab on the same tenant asks for sign-in again.
- Single select: click the button, find the visible `[role=option]` with the exact text, `__bo.fire` it; verify each button's aria-label.
- Multi-select search (Skills, id `skills--skills`): `__bo.setValue`, a real Enter, wait 3 s, a real Enter; verify `[data-automation-id=selectedItem]`.
- Field of Study can ignore search: scroll the listbox with JS until the exact option exists, then click it.
- Date spin buttons: click the month segment and type MMYYYY.

## Greenhouse
- react-select: click, type, Enter; read `[class*=singleValue]`.
- Phone: set the country first (focus `#country`, type, ArrowDown, check the focused option is the right country code, Enter), then press the digits as real keys. If validation fired while the country was empty, "required" sticks: reload and redo in that order.
- Location: focus `#candidate-location`, type the city, read the options from the listbox named in its `aria-controls`, Enter on the exact option.
- Country pickers list lookalikes first (typing "India" offers "British Indian Ocean Territory"). Pick by the exact option text; only the read-back caught a coordinate click on the wrong one.
- Company sites that embed Greenhouse work better at `job-boards.greenhouse.io/embed/job_app?for=<board>&token=<job id>`.

## Lever
- Upload the CV first (its parser overwrites fields), then set name, email, phone and company, then the location from the autocomplete list only.
- Submit: focus `#btn-submit`, press Enter; success is the /thanks page with "Application submitted!".
- A Submit that does nothing points to a hidden required field, such as an "[Optional]" file marked required: `:invalid` finds it. Leave the attribute alone.

## Others
- Ashby can cap applications per candidate within a period (a third role at one company was refused).
- SmartRecruiters keeps file inputs inside shadow DOM: hand it to the person with the prepared files.
- Aggregators (We Work Remotely, Himalayas, Indeed Apply) apply only from the applicant's own account. Find the same role on the company's own board.
- Board region labels are often wrong. Count a role as open only when the company's own posting says so.
- Probe many company boards slowly, about one request a second; Workable rate-limits the whole IP, the person's browser included.
