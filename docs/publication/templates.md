# Reviewed template catalog

The seventh documentation page links 93 literal public governance files: 84 in the historical first-generation family and 9 in MDAAI 2.0. Author: Eris Margeta Kurdali.

The reviewed feed is `Eris-Margeta/mdaai-templates` at commit `4ad670f9402e8699ed969ae719188196ef089aae`, schema 1, catalog 0.1.0. The exact `templates.json` SHA-256 is `f1e5b1426d00a9cc0192b644cde66a830b775bec3d0612f179cb3e693a3b17b4`. The lightweight manifest is vendored as `website/templates.catalog.json`; `website/templates.lock.json` owns the immutable pin. The upstream export manifest records source revisions, byte hashes, adaptations and exclusions. Catalog status `complete: false` concerns adoption review and uninitialized project scaffolds, not an incomplete export.

The homepage panel explains stable protocol → literal template → project → manual or agent-assisted review → versioned template → explicit adoption. A protocol may itself be revised through its authorized process. Neither publication nor import activates instructions in a downstream project.

## Build modes

```sh
just build
just templates-sync
just build-with-templates
```

`just build` runs `python3 -B website/build.py`, fully offline. It uses the reviewed lightweight catalog and links to pinned GitHub files; there are no local payload downloads. Docker and CI use this default.

`just templates-sync` is the explicit network operation. It requests the pinned raw manifest and GitHub archive, permitting only the exact pinned GitHub-to-codeload redirect. It uses native curl TLS verification, 10-second connect and 40-second request timeouts, at most two retries within 90 seconds, a 140-second process deadline and at most four redirect steps. Limits: 4 MiB compressed, 16 MiB expanded, 512 KiB per file, 512 archive members and 128 catalog payloads. The reviewed pin currently requires exactly 93 payloads.

Every archive member is checked, including ignored repository administrative files. Absolute paths, traversal, dot components, backslashes, Unicode/encoded path ambiguity, duplicate paths (including case collisions), symlinks, hardlinks, sparse files, devices and other special members are rejected. No archive path is extracted. Only exact catalog-listed UTF-8 payloads with matching sizes and hashes enter a staged cache. An atomic pointer replacement activates a fully checked immutable cache generation; failure preserves the previous generation. Old generations remain local and may be removed manually when no longer needed. Downloaded instructions and scripts are never executed or adopted.

`just build-with-templates` runs `python3 -B website/build.py --include-templates`. It performs no network access and requires a previously synced cache matching the reviewed pin. Every cached file is revalidated. It emits 93 escaped, noindex HTML text previews and 93 `.txt` downloads under the separate `/template-files/` namespace, with generated numeric filenames. It never serves payloads using executable source extensions or catalog-provided output paths. The optional cache is excluded from Git and Docker. Run `just build` to restore the default publication artifact.

## Reviewing a pin update

A changed upstream branch does nothing automatically. Review the new immutable commit, catalog schema, all file roles and provenance/adaptations, license notices, source-version disclosures and known link gaps. Replace the vendored manifest with actual reviewed bytes and set its actual SHA-256, full commit and count in the lock. Refresh only the relevant publication content/source digest after semantic review. Review and commit the resulting diff; run both test suites, explicitly sync and validate optional output, then restore and validate the offline default. A hash is integrity evidence, not semantic approval.

```sh
python3 -B website/check.py
python3 -B website/check_templates.py
node website/check_clipboard.cjs
node --check website/assets/app.js
```

The 2026-10-04 authorized content review added the gallery and below-video explanation, selectively clarified the two initial template families and refreshed only the content digest, public catalog source reference and additive `publication.css` asset digest. Existing source hashes, video, heading, captions and base design assets are retained.
