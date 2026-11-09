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

The popup currently provides a manual one-review path for exercising the public
API and its retry state. It keeps the pasted text only in the open popup's
memory and exposes a **Retry** button only after a timeout or scoring
unavailable result. Each click makes exactly one new request; there is no
automatic retry. This is not Amazon page extraction: the Phase 0.5 live spike
failed, and the content script still does not collect live review cards.

For local popup requests, configure Spring Boot to allow the exact installed
extension origin. Copy the extension ID from `chrome://extensions`, then set
the origin before starting the backend:

```powershell
$env:TRUSTLOOP_ALLOWED_ORIGINS = "chrome-extension://YOUR_EXTENSION_ID"
```

Replace `YOUR_EXTENSION_ID` with the ID shown by Chrome. The backend remains
loopback-only. Reload the extension after rebuilding it.

`src/content.ts` only checks the host is supported and pings the service worker. The live Amazon spike failed in an unsigned session; Phase 0.5's synthetic fallback fixtures are under `mock/fixtures/amazon/`. They validate fixture shape only and do not establish live Amazon selectors or extraction precision. Extraction starts in Phase 1.

## Test

```bat
cd extension
npm test
```
