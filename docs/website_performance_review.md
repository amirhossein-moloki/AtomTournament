# Website Performance Review

## Overview
This document summarizes the current performance posture of the Atom Tournament web experience based on a source-level review of the static frontend served from the `frontend` directory. The assessment focuses on rendering performance, asset delivery, and runtime behavior that affect page load speed and responsiveness.

## Key Strengths
- **Lean initial markup:** The dashboard page structures its UI with semantic Tailwind utility classes without embedding large inline images or videos, which keeps the HTML payload compact for first render.【F:frontend/index.html†L1-L118】
- **Bottom-loaded application script:** The dashboard JavaScript bundle is referenced at the end of the HTML file, allowing the browser to parse most of the DOM before executing application logic.【F:frontend/index.html†L119-L121】

## Issues Affecting Performance
1. **Blocking third-party CSS/JS from CDNs**
   - Tailwind CSS is pulled through the JavaScript-based CDN build (`https://cdn.tailwindcss.com`) directly inside the `<head>`, which blocks rendering until the script is fetched and executed. This adds a large synchronous dependency to the critical path.【F:frontend/index.html†L7-L23】
   - Font Awesome’s full stylesheet is also fetched synchronously from a CDN. While convenient, it inflates unused CSS and increases render-blocking time.【F:frontend/index.html†L8-L9】

2. **Heavy visual effects on the login page**
   - The login screen depends on Three.js and Vanta’s WebGL background effect, which introduce sizable downloads (hundreds of KB) and consume GPU/CPU cycles even though the page contains a simple form.【F:frontend/login.html†L33-L45】

3. **Lack of asset bundling and caching strategy**
   - The project relies on CDN-served CSS/JS and unbundled JavaScript modules (`dashboard.js`, `login.js`). There is no build step to tree-shake, minify, or version assets, making it difficult to leverage long-term caching and potentially increasing transfer size.【F:frontend/index.html†L7-L23】【F:frontend/js/dashboard.js†L1-L103】

4. **Inefficient DOM updates in dashboard rendering**
   - `dashboard.js` builds team and tournament rows using `innerHTML +=`, which forces repeated DOM parsing and layout work inside loops. This approach scales poorly as data grows and could lead to jank in larger dashboards.【F:frontend/js/dashboard.js†L60-L101】

5. **No lazy loading or skeleton states for dynamic data**
   - The dashboard fetches user data after the DOM content loads but does not provide placeholders or cache the response. Users must wait for the API call to finish before seeing meaningful content, which can increase perceived latency.【F:frontend/js/dashboard.js†L1-L58】

## Opportunities for Improvement
- Replace the runtime Tailwind CDN script with a compiled CSS bundle generated during the build process. This removes the blocking script and dramatically reduces CSS payload size.
- Self-host a trimmed icon set or use SVG sprites instead of the full Font Awesome CDN to eliminate unused CSS and additional network round trips.
- Introduce a bundling pipeline (e.g., Vite, Webpack, or esbuild) to minify JavaScript, enable code splitting, and emit cache-friendly hashed filenames.
- Optimize dashboard rendering by constructing DOM nodes with `document.createElement` or `insertAdjacentHTML` after building the full markup string, minimizing reflows during loops.
- Provide lightweight skeleton components or cached last-known data to improve perceived load time while the dashboard fetch is in flight.
- On the login page, consider removing or gating the Vanta/Three.js background for low-power devices, or lazy-load the effect after the core form is interactive.

## Performance Score
**Estimated Score: 5 / 10** – The current implementation delivers a visually rich experience but relies on blocking third-party assets and heavy visual effects that hinder load speed, particularly on constrained networks or devices. Addressing the above issues should unlock significantly faster first paint and interactivity times.
