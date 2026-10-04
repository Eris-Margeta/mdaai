# Reviewed publication provenance

The six curated documentation pages are drawn from the original MDAAI template, MDAAI 2.0 source package and approved documentation content. Before export, all **52 source-reference SHA-256 digests** were checked against the actual reviewed source bytes. Original source packages remain private/read-only and are not distributed here.

`website/provenance.json` uses logical source names, not personal absolute paths or sibling-repository dependencies. Its source hashes identify the reviewed bytes but do not allow a public build to re-read those private sources. That distinction is deliberate, not a claim of independent source access.

A standalone build verifies:
- the digest of curated `content.json`;
- exact coverage of its logical source references;
- the digest of every explicitly allowlisted static asset;
- safe paths, six approved routes and no unexpected generated files.

Changes fail closed. After an authorized edit, review the corresponding sources and content, record the rationale, then refresh the reviewed content digest or affected asset digest. Never replace digests merely to make a failing build green.

The site documents generic internal file names because those are the protocol. It does not serve the files, private archives, internal reports, original source matrices, old/rejected pages or operational records. Example tasks do not assert a product was implemented. No automatic installer or enforcement guarantee is claimed.

## Media

The final MP4, SRT, PNG poster and matching WebVTT are explicitly selected from the approved local technical explainer. The final narration script is included; rejected drafts, raw audio, logs and third-party workflow copies are excluded. The delivered video is 91.3 seconds, H.264/AAC, 1080 × 1080 at 30 fps. It uses English locally synthesized narration and burned captions plus external captions. No human listening review or legal clearance of third-party voice/font output is implied.

## Design and attribution

The original reviewed `style.css`, `app.js`, SVG favicon and TEJL logo are preserved byte-for-byte. A separate tiny stylesheet sizes the new video. Canonical URLs, visible authorship, structured data and social metadata add no new marketing claims or invented organization credentials. No analytics or remote fonts are added.

## Approved cover and social-art optimization

The approved lossless 1000 × 1300 guardian cover remains unchanged. The homepage now selects a high-quality progressive JPEG derivative from 280, 360, 560, 720 and 1000 pixel widths using initial-HTML `srcset` and CSS-matched `sizes`. Each derivative uses quality 95, 4:4:4 sampling and multiple progressive scans; eager loading and high fetch priority do not depend on JavaScript. Explicit dimensions retain the existing rendered geometry. `website/cover.py` reproduces the derivatives with pinned Pillow 12.1.0 and records the original and derivative digests, encoded dimensions and codec version in its source inventory. The reviewed provenance allowlist publishes only selected derivatives, not that inventory.

All seven routes' four social-art variants were separately adapted from the approved guardian plate, with warm ivory paper, a burgundy title band, route-specific titles and E.M.K. credit. The native master is neither replaced nor recolored. `website/identity.py` reproduces the exact existing dimensions: 1200 × 630 static PNG and GIF alternate, 1200 × 600 large-card PNG, and 600 × 600 square PNG. The new `v2` URLs avoid stale social-art URLs; the GIF's small footer tick leaves its complete title and artwork stable from the first frame. The static PNG remains the primary Open Graph image. Full author attribution is preserved. Social-platform recrawl timing and GIF playback are not guaranteed.

These authorized appearance-preserving cover derivatives and owner-requested social-art revisions justify updating only their corresponding reviewed asset digests. Browser regression coverage checks cold-cache responsive selection, one high-priority cover request, encoded progressive scans and unchanged pre/post-decode image geometry with zero image-associated layout shift. This is not a claim that every connection paints progressive scans at the same speed.

## Rights

The canonical template's tracked MIT license is preserved unchanged at `licenses/template-MIT.txt`, including its original attribution. No blanket MIT or public-domain status is invented for website content or media. See the root [rights notice](../../LICENSE).
