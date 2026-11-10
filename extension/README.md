# Extension

Manifest V3 client. It reads the page, never computes a score or verdict.

## Build

```bat
cd extension
npm install
npm run build
```

`npm install` generates `package-lock.json`; commit it so CI can use `npm ci`.

## Load

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Load unpacked and select `extension/dist`.

After a rebuild, press Reload on the extension card.

The popup provides a manual one-review path for exercising the public API.
On a supported Amazon review route, the content script uses the selectors in
`src/adapters/amazon-reviews.v1.json`, extracts visible eligible cards, hashes
session keys, batches fresh reviews up to ten, and renders only result
metadata. A memory-only page session prevents resubmission after DOM churn.
The observer debounces mutations and enforces the frozen minimum rescan
interval. A user-triggered **Retry** is available for transient unknown results;
there are no automatic retries. Review text and fingerprints are not written
to extension storage.

Result cards expose the status in text, not colour alone. Scored results show
score, verdict, evidence quality, engine, and named signals; low evidence keeps
the score and verdict and adds the normative qualifier. Signals-only results
show no score or verdict. Unknown results show their reason and no numeric
placeholder. The page panel and popup support keyboard focus with a visible
focus indicator and announce result changes to assistive technology.

Local history is available from the popup's **History** button. It is off by
default. When enabled, Chrome local storage keeps only timestamp, hostname,
adapter ID, result metadata, and reason code for at most 100 entries or 30 days.
It never stores review text, review keys, reviewer names, URL paths, or text
fingerprints. Disabling history stops new entries but leaves existing entries
until the user clears them. History is not synchronized.

The Amazon selectors have fixture coverage, but the live Phase 0.5 spike failed
because the review section required sign-in. Treat real-page extraction as
unverified until the live spike is repeated successfully; the saved synthetic
fixtures establish behavior only for their documented markup.

For local popup requests, configure Spring Boot to allow the exact installed
extension origin. Copy the extension ID from `chrome://extensions`, then set
the origin before starting the backend:

```powershell
$env:TRUSTLOOP_ALLOWED_ORIGINS = "chrome-extension://YOUR_EXTENSION_ID"
```

Replace `YOUR_EXTENSION_ID` with the ID shown by Chrome. The backend remains
loopback-only. Reload the extension after rebuilding it.

Saved fixtures cover standard, compact, collapsed, and unsupported pages under
`mock/fixtures/amazon/`. They do not establish live Amazon extraction precision.

## Test

```bat
cd extension
npm run typecheck
npm run build
npm test
```
