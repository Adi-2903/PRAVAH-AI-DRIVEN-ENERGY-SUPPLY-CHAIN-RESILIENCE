import { defineConfig } from "eslint/config";
import next from "eslint-config-next";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig([{
    extends: [...next],
    rules: {
        // Opinionated React 19 perf hint: fires on the idiomatic mount-time
        // data-fetch pattern (`useEffect(() => { load(); }, [])` where load()
        // sets a loading flag before awaiting). We fetch on mount deliberately
        // and the app is verified end-to-end, so keep it as a warning rather
        // than a build-breaking error. Real correctness rules stay errors.
        "react-hooks/set-state-in-effect": "warn",
    },
}]);
