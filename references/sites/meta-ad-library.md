# Meta Ad Library and Facebook pages

- Page id: open `facebook.com/<page>` and read `"associated_page_id":"(\d+)"` from `document.documentElement.innerHTML`. Use it in `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&media_type=all&search_type=page&view_all_page_id=<id>`. The profile id (starting 100…) falsely reports "not running ads" even for heavy advertisers.
- Test the method on a brand known to advertise before trusting a "no ads" result. Cross-check with a keyword search (`q=<brand>&search_type=keyword_unordered`) or the advertiser typeahead, which lands on the correct page id.
- Wait about 5 s before reading counts. The default sort is impressions high to low; "Latest" is the only other order. Each card shows its start date and "N ads use this creative and text", which marks a duplicated winner. In the UK and EU, `active_status=all` also lists stopped ads with their run dates.
- The interface language follows the account (Hindi and others). Read dates and counts by pattern.
- Video frames: `drawImage(video)` onto a canvas works (pixel reads are blocked). Play muted, seek to a few points, lay the canvases out in a fixed overlay and take one screenshot per ad.
