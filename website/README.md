# Product website

Published on GitHub Pages from main:/docs at https://arpanjot-coding.github.io/CheatCraft/.

Regenerate localized HTML and sitemap after editing COPY in build.py:

    python website/build.py

The stylesheet is maintained directly in docs/style.css. The core website needs no Node, cookies, analytics or runtime translation service. English lives at the root; the other twelve languages have dedicated subdirectories. Each edition has a localized title, description, main content and language navigation; reciprocal hreflang links, self-canonical URLs and a sitemap identify alternate editions. The real application screenshot shows its current English UI with controlled fixture data.

Filipino, Thai and Simplified Chinese resolve the requested Philippines, Thailand and Chinese editions. Portuguese and Spanish are language-wide editions. Italian appears once. Translations should receive native-speaker review before use in paid campaigns or contractual/security materials.

The project-site robots.txt is informational: GitHub Pages controls robots.txt at the host root. Submit the sitemap in a verified search-engine webmaster account if desired. No indexing or ranking guarantee is made.


## Design, localization and SEO review — 2 November 2026

The product illustration was replaced with an authentic native CheatCraft screenshot. Provenance and controlled-fixture context are recorded in docs/screenshots/README.md and visible in each localized caption. The site positions the app for developers and technical testers; it makes no claim of adoption by professional gamers and includes no invented testimonials, ratings or usage counts.

The navigation now exposes a keyboard-accessible language menu at the top. A localized skip link, visible focus styles, enlarged touch targets, localized footer/FAQ content, and source-preview requirements improve navigation and explanation. The current site describes the English desktop app; localized site pages do not imply a translated desktop build.

Titles describe Windows memory diagnostics instead of repeating marketing slogans. All thirteen pages have unique localized titles/descriptions, self-canonical URLs, reciprocal language alternatives including x-default, OG locales and a real 1200×630 social PNG. Filipino content retains the /fil/ URL and valid HTML language fil, with ISO 639-1 tl used in Google-facing hreflang. The sitemap uses the identical language/URL map. Language links are ordinary HTML and no locale is selected automatically from IP or browser settings.

SoftwareApplication/WebPage structured data describe the source preview truthfully. Free/MIT terms are visible. No ratings are invented and rich-result eligibility is not claimed. The custom 404 is noindex and excluded from the sitemap. The project-level robots.txt does not control the GitHub Pages host-root robots policy. Search Console verification, sitemap submission, real-user Core Web Vitals and native-speaker translation review remain external follow-up work.

Core content, screenshots and language routing need no JavaScript. One small first-party enhancement reads the public GitHub repository API with credentials omitted to display the actual star count. It uses textContent, a timeout and a neutral fallback, not a fabricated number. This is an external GitHub metadata request; there are no analytics or third-party scripts. Ordinary asset caching is controlled by GitHub Pages.

Verification: all thirteen editions were checked in a real browser at 320 CSS px for horizontal overflow and undersized targets after the navigation/SEO changes. The English baseline was inspected at 390, 768 and 1280 px. Native application capture was stopped with Escape after one screenshot; no further browser/native interaction was performed in that turn. The subsequent authentic-image and technology-section changes received static/regression checks; final visual reinspection is still required. No Lighthouse score, exhaustive WCAG conformance or ranking guarantee is claimed.

Run the website regression checks with:

    python -m unittest discover -s website -p test_site.py -v
