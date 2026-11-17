// 把与 react-pdf 匹配的 pdf.js worker 拷到 public/，避免依赖外部 CDN。
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const reactPdfDir = dirname(require.resolve("react-pdf/package.json"));
const pdfjsDir = dirname(createRequire(join(reactPdfDir, "x.js")).resolve("pdfjs-dist/package.json"));
mkdirSync("public", { recursive: true });
copyFileSync(join(pdfjsDir, "build", "pdf.worker.min.mjs"), join("public", "pdf.worker.min.mjs"));
console.log("pdf worker copied from", pdfjsDir);
