"""Archive worldwide R&D/income inputs, including 2000–2025 history.

python download_data.py             # reuse checksum-verified snapshots
python download_data.py --refresh   # replace with the current source vintage
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from basque_sources import SOURCES as BASQUE_SOURCES, REQUESTS as BASQUE_REQUESTS
from breakdown_sources import SOURCES as BREAKDOWN_SOURCES, REQUESTS as BREAKDOWN_REQUESTS
from official_sources import SOURCES as OFFICIAL_SOURCES

REQUESTS = {**BASQUE_REQUESTS, **BREAKDOWN_REQUESTS}

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
WB = "https://api.worldbank.org/v2"
OECD = "https://sdmx.oecd.org/public/rest/v1"
INDICATORS = {
    "rd": ("GB.XPD.RSDV.GD.ZS", "2020:2024"),
    "nominal": ("NY.GDP.PCAP.CD", "2025"),
    "ppp": ("NY.GDP.PCAP.PP.CD", "2025"),
}
SOURCES = {
    "wb_countries.json": f"{WB}/country?format=json&per_page=400",
    "msti_gerd_percent_gdp_2020_2024.csv": (
        f"{OECD}/data/OECD.STI.STP,DSD_MSTI@DF_MSTI,1.3/"
        ".A.G.PT_B1GQ._Z._Z?startPeriod=2020&endPeriod=2024&format=csvfilewithlabels"
    ),
    "msti_structure.xml": (
        f"{OECD}/dataflow/OECD.STI.STP/DSD_MSTI@DF_MSTI/1.3?references=all"
    ),
}
for key, (indicator, period) in INDICATORS.items():
    SOURCES[f"wb_{key}.json"] = (
        f"{WB}/country/all/indicator/{indicator}?source=2&date={period}"
        "&format=json&per_page=20000&footnote=y"
    )
    SOURCES[f"wb_{key}_metadata.json"] = f"{WB}/indicator/{indicator}?source=2&format=json"

HISTORY_START, HISTORY_END = 2000, 2025
HISTORY_SOURCES = {
    "msti_gerd_percent_gdp_history.csv": (
        f"{OECD}/data/OECD.STI.STP,DSD_MSTI@DF_MSTI,1.3/"
        f".A.G.PT_B1GQ._Z._Z?startPeriod={HISTORY_START}&endPeriod={HISTORY_END}&format=csvfilewithlabels"
    ),
    **{
        f"wb_{key}_history.json": (
            f"{WB}/country/all/indicator/{indicator}?source=2&date={HISTORY_START}:{HISTORY_END}"
            "&format=json&per_page=20000&footnote=y"
        ) for key, (indicator, _) in INDICATORS.items()
    },
}
SOURCES.update(HISTORY_SOURCES)

UIS_BULK_URL = "https://databrowser.uis.unesco.org/resources/bulk"
UIS_ARCHIVE = "uis_science_sdg.zip"
NOMINAL_SOURCES = {
    "msti_gerd_nominal_local_history.csv": (
        f"{OECD}/data/OECD.STI.STP,DSD_MSTI@DF_MSTI,1.3/"
        f".A.G.XDC.V._Z?startPeriod={HISTORY_START}&endPeriod={HISTORY_END}&format=csvfilewithlabels"
    ),
    "wb_gdp_total_usd_history.json": (
        f"{WB}/country/all/indicator/NY.GDP.MKTP.CD?source=2&date={HISTORY_START}:{HISTORY_END}"
        "&format=json&per_page=20000&footnote=y"
    ),
    "wb_gdp_total_usd_metadata.json": f"{WB}/indicator/NY.GDP.MKTP.CD?source=2&format=json",
    "wb_indicator_catalog.json": f"{WB}/indicator?source=2&format=json&per_page=20000",
    "uis_science_bulk.html": UIS_BULK_URL,
}
SOURCES.update(NOMINAL_SOURCES)

SECTOR_FIELD_SOURCES = {
    "gerd_sector_field_history.csv": (
        f"{OECD}/data/OECD.STI.STP,DSD_RDS_GERD@DF_GERD_FORD,1.0/"
        f".A.G.._Z._Z._Z.._Z..?startPeriod={HISTORY_START}&endPeriod={HISTORY_END}&format=csvfilewithlabels"
    ),
    "gerd_ford_structure.xml": (
        f"{OECD}/dataflow/OECD.STI.STP/DSD_RDS_GERD@DF_GERD_FORD/1.0?references=all"
    ),
}
SOURCES.update(SECTOR_FIELD_SOURCES)
SOURCES.update(BASQUE_SOURCES)
SOURCES.update(BREAKDOWN_SOURCES)
SOURCES.update(OFFICIAL_SOURCES)


def uis_archive_url(body: bytes) -> str:
    """Use the current Science download advertised on the official bulk page."""
    urls = set(re.findall(r'https://download\.uis\.unesco\.org/bdds/\d{6}/SCN-SDG\.zip', body.decode("utf-8")))
    assert len(urls) == 1, "UIS Science archive link changed or is ambiguous; inspect the official bulk page"
    return urls.pop()


def download(url: str, query: dict | None = None, timeout: int = 180, retries: int = 3) -> tuple[bytes, dict]:
    """Retry temporary upstream failures, retaining the actual response bytes."""
    for attempt in range(retries):
        try:
            request_body = None if query is None else json.dumps(query, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
            request = Request(url, data=request_body, headers={"User-Agent": "world-rd-income-research/1.0", "Content-Type": "application/json"})
            with urlopen(request, timeout=timeout) as response:
                body = response.read()
                info = {
                    "url": url, "resolved_url": response.url,
                    "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                    "content_type": response.headers.get("Content-Type", ""),
                    "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                }
                if request_body is not None:
                    info.update(method="POST", request_body=request_body.decode("utf-8"),
                                request_sha256=hashlib.sha256(request_body).hexdigest())
            return body, info
        except (URLError, TimeoutError, ConnectionError) as error:
            if isinstance(error, HTTPError) and error.code != 429 and not 500 <= error.code < 600:
                raise
            if attempt == retries - 1:
                raise
            print(f"Temporary download failure; retrying {url}: {error}")
            time.sleep(5 * (attempt + 1))


def refresh_inputs(refresh: bool = False) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "manifest.json"
    manifest = json.loads(path.read_text("utf-8")) if path.exists() else {}
    previous = ROOT.parent / "oecd-rd-income" / "data" / "raw"
    previous_manifest = previous / "manifest.json"
    pending = {}
    for name, url in SOURCES.items():
        target = RAW / name
        if target.exists() and not refresh:
            assert name in manifest, f"Missing provenance for {name}"
            assert hashlib.sha256(target.read_bytes()).hexdigest() == manifest[name]["sha256"]
            assert manifest[name]["url"] == url
            if name in REQUESTS:
                assert json.loads(manifest[name]["request_body"]) == REQUESTS[name]
            print(f"Reusing {name}")
            continue
        # Carry forward the exact OECD vintage used for the previous figures.
        if not refresh and name in {"msti_gerd_percent_gdp_2020_2024.csv", "msti_structure.xml"} and previous_manifest.exists():
            old = json.loads(previous_manifest.read_text("utf-8"))[name]
            body = (previous / name).read_bytes()
            assert old["url"] == url
            assert hashlib.sha256(body).hexdigest() == old["sha256"]
            info = {**old, "archive_note": "Exact snapshot reused from the OECD-only reconstruction"}
        else:
            body, info = download(url, REQUESTS.get(name))
        if name in REQUESTS:
            payload = json.loads(body)["dataset"]
            assert "dimension" in payload and "value" in payload
            info["api_updated"] = payload.get("updated", "")
        elif name.startswith("eustat_") and name.endswith("_metadata.json"):
            assert json.loads(body)["variables"]
        elif name.startswith("eustat_") and name.endswith(".html"):
            assert b"Eustat" in body and b"<html" in body.lower()
        elif name.startswith("eustat_") and name.endswith(".px"):
            assert b"DECIMALS=" in body and b"DATA=" in body
        elif name.endswith(".json"):
            payload = json.loads(body)
            assert isinstance(payload, list) and len(payload) == 2, f"Unexpected API response: {name}"
            assert int(payload[0]["pages"]) == 1 and int(payload[0]["page"]) == 1, (
                f"Unretrieved API pages: {name}; increase per_page or add pagination before publishing"
            )
            assert isinstance(payload[1], list) and len(payload[1]) == int(payload[0]["total"])
            info["api_lastupdated"] = payload[0].get("lastupdated", "")
        elif name.endswith(".csv"):
            assert body.lstrip(b"\xef\xbb\xbf").startswith(b"STRUCTURE,")
        elif name == "uis_science_bulk.html":
            uis_archive_url(body)
        elif name.endswith(".xlsx"):
            with ZipFile(io.BytesIO(body)) as archive:
                assert archive.testzip() is None and "xl/workbook.xml" in archive.namelist()
        elif name.startswith("ons_") and name.endswith(".html"):
            assert b"Office for National Statistics" in body and b"<html" in body.lower()
        elif name.startswith("ine_") and name.endswith(".html"):
            assert b"INEbase" in body and b"<html" in body.lower()
        else:
            assert b"<message:Structure" in body
        pending[name] = body
        manifest[name] = info
    # Resolve the current UIS release from the archived official discovery page.
    bulk = pending.get("uis_science_bulk.html")
    if bulk is None:
        bulk = (RAW / "uis_science_bulk.html").read_bytes()
    url = uis_archive_url(bulk)
    target = RAW / UIS_ARCHIVE
    if target.exists() and not refresh:
        assert manifest[UIS_ARCHIVE]["url"] == url
        assert hashlib.sha256(target.read_bytes()).hexdigest() == manifest[UIS_ARCHIVE]["sha256"]
        print(f"Reusing {UIS_ARCHIVE}")
    else:
        body, info = download(url)
        with ZipFile(io.BytesIO(body)) as archive:
            assert archive.testzip() is None
            assert {"SCN-SDG_DATA_NATIONAL.csv", "SCN-SDG_LABEL.csv", "SCN-SDG_METADATA.csv"} <= set(archive.namelist())
        pending[UIS_ARCHIVE] = body
        manifest[UIS_ARCHIVE] = {**info, "discovery_url": UIS_BULK_URL, "release": url.split("/")[-2]}
    # A failed download or response validation must not leave a mixed vintage.
    # Promote only after all responses pass; write the manifest last.
    for name, body in pending.items():
        target = RAW / name
        temporary = target.with_name(name + ".download")
        temporary.write_bytes(body)
        temporary.replace(target)
        print(f"Archived {name}: {len(body):,} bytes")
    if pending:
        temporary = path.with_suffix(".download")
        temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    refresh_inputs(args.refresh)


if __name__ == "__main__":
    main()
