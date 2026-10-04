# MDAAI public documentation repository

Read this file before editing. This repository publishes six curated documentation pages and an explanatory video; it is not the private product implementation or an automatic governance installer.

## Working contract
- Preserve approved content and the existing design. Keep source packages read-only.
- `website/content.json` owns published prose; `website/provenance.json` pins reviewed content, logical source references and assets. Builds fail closed on drift.
- After an authorized, source-reviewed edit, refresh only the relevant content/asset digests and document why. Never fabricate source hashes or treat digests as proof of semantic correctness.
- Run `python3 -B website/build.py`, `python3 -B website/check.py`, `node website/check_clipboard.cjs`, and `node --check website/assets/app.js`.
- Use zsh. Do not publish machine paths, credentials, source archives, rejected drafts, internal reports or operational checkpoints. Keep private operational records local.
- Every public claim must reflect real evidence. Do not represent example tasks as implemented products, instructions as automatic enforcement, or local builds as completed publication.
- No host canonicalization redirects in site code. Canonical host routing is owned by the DNS/CDN edge.
- Preserve prior attribution/license notices. No blanket reuse license for publication content may be invented.

## Structure
`website/` contains source and reproducible build/tests. `docs/publication/` explains provenance and media. `licenses/` preserves inherited notices. `Dockerfile` and `nginx.conf` define the production static service.

This project was instantiated from the canonical first-generation repository template without copying its Git history. Its private working scaffold is deliberately excluded from the public repository.
