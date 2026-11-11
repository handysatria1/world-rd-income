"""Publish a readable source guide and lossless, build-specific provenance exports."""

from __future__ import annotations

import csv
import hashlib
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def source_role(name: str) -> tuple[str, str]:
    if name.startswith("wb_"):
        provider = "World Bank WDI (UNESCO UIS for the R&D intensity indicator)"
        if name == "wb_countries.json":
            return provider, "Economy catalog and aggregate exclusion"
        if "metadata" in name or "catalog" in name:
            return provider, "Indicator definitions, units and source metadata"
        return provider, "Reported indicators or same-year conversion inputs; see indicator ID in URL"
    if name.startswith(("msti_", "gerd_")):
        return "OECD", "Structure, units, classifications and flags" if name.endswith(".xml") else "Reported GERD observations"
    if name.startswith("uis_"):
        return "UNESCO Institute for Statistics", "Bulk-release discovery page" if name.endswith(".html") else "Science SDG archive: observations, labels, metadata and release documentation"
    if name.startswith("eustat_"):
        if name.endswith(".html"):
            role = "Methodology, classification, advance-release or coverage documentation"
        elif name.endswith(".px"):
            role = "PC-Axis source used to establish precision and support source checks"
        elif "metadata" in name:
            role = "PxWeb table dimensions, labels and units"
        else:
            role = "Reported regional observations selected by the archived POST request"
        return "Eustat — Basque Statistics Office", role
    if name.startswith("ons_"):
        review = "goverd" in name or name.endswith(".html")
        return "UK Office for National Statistics", "Methodology and coverage review; GovERD net-spending types are not used as performed-research types" if review else "Reviewed publication-vintage workbook observations; see table/cell mappings in the guide"
    if name.startswith("ine_"):
        return "Instituto Nacional de Estadística (Spain)", "Regional coverage review only; no numerical observations extracted for the dashboard"
    return "See source URL", "Archived input; consult its source documentation"


def build_source_guide(destination: Path, built_utc: str) -> None:
    raw = ROOT / "data/raw"
    manifest_bytes = (raw / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    fields = sorted({key for info in manifest.values() for key in info})
    entries = []
    with (destination / "source_inventory.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_file", "provider", "role", "http_method", *fields])
        writer.writeheader()
        for name, info in sorted(manifest.items()):
            path = raw / name
            assert path.stat().st_size == info["bytes"], name
            with path.open("rb") as source:
                assert hashlib.file_digest(source, "sha256").hexdigest() == info["sha256"], name
            provider, role = source_role(name)
            method = info.get("method", "GET")
            writer.writerow({"source_file": name, "provider": provider, "role": role, "http_method": method, **info})
            details = [f"<dt>Provider</dt><dd>{escape(provider)}</dd>",
                       f"<dt>Use in this project</dt><dd>{escape(role)}</dd>",
                       f"<dt>HTTP method</dt><dd>{escape(method)}</dd>",
                       f"<dt>Archived file inside the research ZIP</dt><dd><code>data/raw/{escape(name)}</code></dd>"]
            for key, value in info.items():
                text = escape(str(value))
                if key in {"url", "resolved_url", "discovery_url"}:
                    assert str(value).startswith(("https://", "http://"))
                    rendered = f'<a href="{text}">{text}</a>'
                elif key in {"request_body", "sha256", "request_sha256"}:
                    rendered = f"<pre>{text}</pre>"
                else:
                    rendered = text or "Not supplied"
                details.append(f"<dt>{escape(key)}</dt><dd>{rendered}</dd>")
            entries.append(f'<details class="source-entry" data-source-file="{escape(name, quote=True)}">'
                           f'<summary><code>{escape(name)}</code> — {escape(provider)}</summary>'
                           f'<dl>{"".join(details)}</dl></details>')
    (destination / "source_manifest.json").write_bytes(manifest_bytes)
    template = (ROOT / "data_sources.html").read_text("utf-8")
    replacements = {
        "__BUILD_UTC__": escape(built_utc),
        "__SOURCE_COUNT__": str(len(manifest)),
        "__RETRIEVAL_DATES__": escape(", ".join(sorted({info["retrieved_utc"][:10] for info in manifest.values()}))),
        "__SOURCE_ENTRIES__": "\n".join(entries),
    }
    for marker, value in replacements.items():
        assert template.count(marker) == 1, marker
        template = template.replace(marker, value)
    (destination / "sources.html").write_text(template, encoding="utf-8")
