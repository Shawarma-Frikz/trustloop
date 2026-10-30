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

`src/content.ts` only checks the host is supported and pings the service worker. The live Amazon spike failed in an unsigned session; Phase 0.5's synthetic fallback fixtures are under `mock/fixtures/amazon/`. They validate fixture shape only and do not establish live Amazon selectors or extraction precision. Extraction starts in Phase 1.

## Test

```bat
cd extension
npm test
```
