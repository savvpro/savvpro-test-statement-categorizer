import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import jsxA11y from "eslint-plugin-jsx-a11y";

// eslint-config-next already registers the jsx-a11y plugin; we enable the full recommended rule set.
const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: { ...jsxA11y.flatConfigs.recommended.rules, "react/no-danger": "error" },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", "src/lib/api/schema.d.ts", "public/**"]),
]);

export default eslintConfig;
