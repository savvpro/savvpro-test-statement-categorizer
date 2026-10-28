// Copies ../samples into public/samples. Tolerates a missing source directory.
import { cpSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "..", "samples");
const dest = join(root, "public", "samples");

if (!existsSync(src)) {
  console.log("copy-samples: ../samples not found, skipping");
} else {
  mkdirSync(dest, { recursive: true });
  cpSync(src, dest, { recursive: true });
  console.log("copy-samples: copied samples to public/samples");
}
