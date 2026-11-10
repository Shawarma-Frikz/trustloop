import { cp, mkdir, rm } from "node:fs/promises";
import { build } from "esbuild";

await rm("dist", { recursive: true, force: true });
await mkdir("dist", { recursive: true });

await build({
  entryPoints: ["src/background.ts", "src/content.ts", "src/popup.ts"],
  outdir: "dist",
  bundle: true,
  format: "iife",
  target: "chrome116",
  sourcemap: true,
  logLevel: "info",
});

await cp("public", "dist", { recursive: true });
