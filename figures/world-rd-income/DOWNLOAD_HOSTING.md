# Large downloads in Releases; interactive website on Pages

The deployment enforces a stricter 300,000,000-byte Pages artifact ceiling. Releases have a separate allowance: each asset must be smaller than 2 GiB, with no stated total release-size limit. See GitHub's [Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) and [release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas).

`release_downloads.py` runs **after** the full staged site, workbooks and offline research ZIP have been verified. It relocates root-level download-only ZIP, Excel, CSV/CSV.gz and PDF files of at least 5,000,000 bytes into a separate release-upload directory, preserving their bytes. HTML, JavaScript, JSON, JSON.gz partitions, small tables and images remain on Pages. No chart fetches are redirected to GitHub Releases; they remain same-origin. It rewrites only HTML download anchors, not scripts, data values or chart controls.

Every moved file receives an immutable, explicit release-tag URL in `downloads_manifest.json`, with byte count and SHA-256. Identical assets can be reused from a reviewed existing release with `--reuse-release`; a size or digest mismatch causes a fresh asset instead of silently reusing different data. Public Release asset sizes and SHA-256 digests must match before Pages can deploy. Downloads remain ordinary CSV/Excel/ZIP files, not modified datasets.

The weekly workflow publishes large files to a unique `data-RUN_ID-RUN_ATTEMPT` release. This release is not marked as GitHub's latest release. The website links to that exact build, never a floating latest URL. Release publishing uses a job-scoped `contents: write` permission. A failure leaves the previous Pages deployment unchanged. Old releases are not automatically deleted, because their URLs provide reproducibility.

Fresh builds assemble the full research ZIP **before** download-link rewriting, retaining a self-contained, local-link archive and including the distribution script and checks. The initial hosting-only migration reuses the existing, byte-identical research ZIP; its older source code is intentionally not rewritten. Current hosting code is in the GitHub repository. There is no need to download source CSVs from Releases to load the website charts. The final Pages-size check applies to the slim published site, not the temporary combined staging area.

```sh
python -m unittest test_release_downloads.py
python release_downloads.py --site /path/to/staged-site --assets /separate/path/to/downloads \
  --repository OWNER/REPO --release-tag data-BUILD
# Inspect the manifest and run browser checks before publishing manually.
```

Add `--publish --target COMMIT` to publish and verify the prepared files in the same run. `gh` authentication is required for publication, or set `GH_BIN` to the GitHub CLI executable. Do not run preparation twice against the same modified site: restore or rebuild the original staging area first. Original source files and earlier release assets are not deleted.

The snapshot deployment workflow supports both historical full-site archives and newer release-linked archives. For a newer snapshot, `downloads_manifest.json` replaces the requirement for an on-Pages `world-rd-income.zip`.
