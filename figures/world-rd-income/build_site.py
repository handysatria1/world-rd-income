"""Package an already regenerated, validated chart for GitHub Pages.

python build_site.py --destination ../../_site
The destination must be empty. No download or calculation occurs here.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from source_guide import build_source_guide
from industry_site import build_industry_site, DOWNLOADS as INDUSTRY_DOWNLOADS
from broad_sector_site import build_broad_sector_site, DOWNLOADS as BROAD_DOWNLOADS, FIGURES as BROAD_FIGURES
from sector_economy_site import build_sector_economy_site, DOWNLOADS as SECTOR_DOWNLOADS, FIGURES as SECTOR_FIGURES
from rd_industry_site import build_rd_industry_site, DOWNLOADS as RD_INDUSTRY_DOWNLOADS
from dashboard_site import build_dashboard

ROOT = Path(__file__).resolve().parent


def build_site(destination: Path) -> None:
    report = json.loads((ROOT / "data" / "validation_report.json").read_text("utf-8"))
    assert report["validation"] and all(value == "passed" for value in report["validation"].values())
    history_report = json.loads((ROOT / "data" / "explorer_validation.json").read_text("utf-8"))
    assert history_report["built_utc"] == report["built_utc"]
    assert all(value == "passed" for value in history_report["validation"].values())
    assert "nominal_rd" in history_report
    assert "sector_field_gerd" in history_report
    sector_report = json.loads((ROOT / "data" / "sector_field_validation.json").read_text("utf-8"))
    assert sector_report["built_utc"] == report["built_utc"]
    assert all(value == "passed" for value in sector_report["validation"].values())
    basque_report = json.loads((ROOT / "data" / "basque_validation.json").read_text("utf-8"))
    assert basque_report["built_utc"] == report["built_utc"]
    assert all(value == "passed" for value in basque_report["validation"].values())
    breakdown_report = json.loads((ROOT / "data" / "breakdown_validation.json").read_text("utf-8"))
    assert breakdown_report["built_utc"] == report["built_utc"]
    assert all(value == "passed" for value in breakdown_report["validation"].values())
    document = (ROOT / "output" / "world_rd_income_explorer.html").read_text("utf-8")
    assert report["built_utc"] in document, "Rebuild the chart and report together before publishing"
    marker = "<!-- published-downloads -->"
    assert document.count(marker) == 1
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError(f"Use an empty site destination: {destination}")
    build_source_guide(destination, report["built_utc"])
    build_industry_site(destination, report["built_utc"])
    build_broad_sector_site(destination)
    build_sector_economy_site(destination)
    build_rd_industry_site(destination)

    # Explicit package directories avoid publishing unrelated workspace material.
    files = [ROOT / name for name in (
        "download_data.py", "reproduce_figures.py", "build_site.py",
        "release_downloads.py", "test_release_downloads.py", "DOWNLOAD_HOSTING.md",
        "requirements.txt", "README.md", "AUTOMATION.md", "OFFICIAL_DATA.md", "historical_explorer.py",
        "CITATION.cff", "CITATION.bib",
        "source_guide.py", "data_sources.html",
        "industry_sources.py", "industry_data.py", "verify_industry.py", "industry_site.py", "industry.html", "INDUSTRY_DATA.md", "china_gva.py", "CHINA_GVA.md",
        "broad_sector_sources.py", "broad_sectors.py", "verify_broad_sectors.py", "broad_sector_figures.py",
        "broad_sector_site.py", "verify_broad_site.py", "broad-sectors.html", "broad_sector_core.js", "broad_sector_chart.js", "test_broad_sector.js", "BROAD_SECTORS.md",
        "sector_economy_sources.py", "sector_economy.py", "verify_sector_economy.py", "sector_economy_figures.py",
        "sector_economy_site.py", "sector-economy.html", "sector_economy_core.js", "sector_economy_chart.js", "test_sector_economy.js", "SECTOR_ECONOMY.md",
        "rd_industry_sources.py", "rd_industry_mapping.py", "rd_industry_native.py", "rd_industry.py", "verify_rd_industry.py", "test_rd_industry.py",
        "rd_industry_site.py", "rd-industry.html", "rd_industry_core.js", "rd_industry_chart.js", "test_rd_industry.js", "RD_INDUSTRY.md",
        "rd_industry_details.py", "rd_coverage.js", "income_sources.py", "income_data.py", "absorptive_capacity.py", "test_absorptive_capacity.py",
        "income_core.js", "income_chart.js", "innovation_chart.js", "absorptive_capacity_chart.js",
        "test_absorptive_capacity_chart.js", "INCOME_GROUPS.md",
        "basque_innovation_sources.py", "basque_innovation.py", "verify_basque_innovation.py",
        "dashboard_site.py", "snapshot_indicators.py", "test_snapshot_indicators.py", "dashboard.html", "dashboard.css", "dashboard.js", "dashboard_bridge.js",
        "research_groups.py", "research-groups.html", "research_group_chart.js", "research_group_core.js", "research_compare_chart.js", "test_research_groups.js", "RESEARCH_GROUPS.md", "verify_dashboard.py", "test_income.js",
        "government_industry_sources.py", "government_industry.py", "verify_government_industry.py", "official_industry_chart.js", "GOVERNMENT_INDUSTRIES.md",
        "explorer.html", "explorer.css", "explorer_core.js", "explorer.js", "test_explorer.js",
        "nominal_rd.py", "test_nominal_rd.py",
        "sector_field_rd.py", "test_sector_field_rd.py", "verify_sector_field.py",
        "basque_sources.py", "basque_rd.py", "verify_basque.py",
        "breakdown_sources.py", "breakdown_rd.py", "breakdown_figures.py", "breakdown_core.js",
        "test_breakdown.js", "verify_breakdown.py", "official_sources.py", "official_rd.py",
    )]
    files += [p for p in (ROOT / "data").rglob("*") if p.is_file() and p.suffix in {".json", ".csv", ".xml", ".xlsx", ".md", ".html", ".zip", ".px", ".pdf", ".hwpx"}]
    files += [p for p in (ROOT / "output").iterdir() if p.is_file() and p.suffix in {".html", ".png", ".svg", ".pdf"}]
    with ZipFile(destination / "world-rd-income.zip", "w", ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, "world-rd-income/figures/world-rd-income/" + path.relative_to(ROOT).as_posix())
        for name in ("CITATION.cff", "CITATION.bib"):
            archive.write(ROOT / name, "world-rd-income/" + name)
        for name in ("sources.html", "source_inventory.csv", "source_manifest.json",
                     "industry_source_inventory.csv", "industry_source_manifest.json",
                     "broad_sector_source_inventory.csv", "broad_sector_source_manifest.json",
                     "sector_economy_source_inventory.csv", "sector_economy_source_manifest.json",
                     "rd_industry_source_inventory.csv", "rd_industry_source_manifest.json"):
            if name.endswith('.html'):
                offline = (destination / name).read_text('utf-8')
                for path in ROOT.glob('*.md'):
                    offline = offline.replace(f'href="{path.name}"', f'href="figures/world-rd-income/{path.name}"')
                archive.writestr('world-rd-income/' + name, offline)
            else:
                archive.write(destination / name, "world-rd-income/" + name)
        # Keep the supplement's downloaded-data links usable after extracting the research ZIP.
        offline = (destination / "industry.html").read_text("utf-8")
        for name in INDUSTRY_DOWNLOADS:
            offline = offline.replace(f'href="{name}"', f'href="figures/world-rd-income/data/{name}"')
        offline = offline.replace('href="INDUSTRY_DATA.md"', 'href="figures/world-rd-income/INDUSTRY_DATA.md"')
        offline = offline.replace('href="CHINA_GVA.md"', 'href="figures/world-rd-income/CHINA_GVA.md"')
        offline = offline.replace('href="index.html"', 'href="figures/world-rd-income/output/world_rd_income_explorer.html"')
        offline = offline.replace('<a href="world-rd-income.zip">Full reproducible research ZIP</a>', 'Full research package: this extracted directory')
        archive.writestr("world-rd-income/industry.html", offline)
        offline = (destination / "broad-sectors.html").read_text("utf-8")
        for name in BROAD_DOWNLOADS:
            offline = offline.replace(f'href="{name}"', f'href="figures/world-rd-income/data/{name}"')
        for name in BROAD_FIGURES:
            offline = offline.replace(f'href="{name}"', f'href="figures/world-rd-income/output/{name}"')
        offline = offline.replace('href="BROAD_SECTORS.md"', 'href="figures/world-rd-income/BROAD_SECTORS.md"')
        offline = offline.replace('<a href="world-rd-income.zip">Full reproducible research ZIP</a>', 'Full research package: this extracted directory')
        archive.writestr("world-rd-income/broad-sectors.html", offline)
        offline = (destination / "sector-economy.html").read_text("utf-8")
        for name in SECTOR_DOWNLOADS:
            offline = offline.replace(f'href="{name}"', f'href="figures/world-rd-income/data/{name}"')
        for name in SECTOR_FIGURES:
            offline = offline.replace(f'href="{name}"', f'href="figures/world-rd-income/output/{name}"')
        offline = offline.replace('href="SECTOR_ECONOMY.md"', 'href="figures/world-rd-income/SECTOR_ECONOMY.md"')
        offline = offline.replace('<a href="world-rd-income.zip">Full reproducible research ZIP</a>', 'Full research package: this extracted directory')
        archive.writestr("world-rd-income/sector-economy.html", offline)
        offline = (destination / "rd-industry.html").read_text("utf-8")
        for name in RD_INDUSTRY_DOWNLOADS:
            offline = offline.replace(f'href="{name}"', f'href="figures/world-rd-income/data/{name}"')
        offline = offline.replace('href="RD_INDUSTRY.md"', 'href="figures/world-rd-income/RD_INDUSTRY.md"')
        offline = offline.replace('<a href="world-rd-income.zip">Full reproducible research ZIP</a>', 'Full research package: this extracted directory')
        archive.writestr("world-rd-income/rd-industry.html", offline)
        for name in ("update-world-rd-income.yml", "publish-world-rd-snapshot.yml"):
            workflow = ROOT.parents[1] / ".github" / "workflows" / name
            if workflow.exists():
                archive.write(workflow, "world-rd-income/.github/workflows/" + name)
    for name in ("CITATION.cff", "CITATION.bib"):
        (destination / name).write_bytes((ROOT / name).read_bytes())
    (destination / "current_results.md").write_bytes((ROOT / "data" / "current_results.md").read_bytes())
    for name in ["rd_nominal_annual.csv", "rd_nominal_coverage.csv", "world_rd_income_data.xlsx", "basque_annual.csv",
                 "rd_sector_field_annual.csv", "rd_sector_field_coverage.csv", "rd_sector_field_reconciliation.csv", "rd_sector_field_definitions.csv",
                 "rd_breakdown_annual.csv", "rd_breakdown_coverage.csv", "rd_breakdown_reconciliation.csv", "rd_breakdown_definitions.csv",
                 "rd_breakdown_conversion.csv", "rd_breakdown_examples.csv", "rd_official_conversion.csv",
                 "rd_research_oecd_alternatives.csv", "rd_ons_funding_reported.csv", "rd_ons_intensity.csv", "rd_ons_funding_comparison.csv"]:
        (destination / name).write_bytes((ROOT / "data" / name).read_bytes())
    chart_links = []
    for name, title in [("rd_funding_intensity_2020_2024", "Funding + intensity"),
                        ("rd_performer_intensity_2020_2024", "Performing sectors + intensity"),
                        ("rd_performer_composition_2020_2024", "Performing-sector percentages"),
                        ("rd_funding_performer_composition_2020_2024", "Funding and performer composition"),
                        ("rd_research_type_composition_2020_2024", "Government/business research types")]:
        links = []
        for extension in ["png", "svg", "pdf"]:
            filename = name + "." + extension
            (destination / filename).write_bytes((ROOT / "output" / filename).read_bytes())
            links.append(f'<a href="{filename}">{extension.upper()}</a>')
        chart_links.append(title + ": " + " / ".join(links))
    document = document.replace(marker, (
        '<p><strong><a href="rd-industry.html">Industry R&amp;D combined with GVA, employment, productivity and exports</a></strong> · '
        'Six-sector classification with coverage audit · <a href="rd_industry_economy.xlsx">Combined Excel workbook</a></p>'
        '<p><strong><a href="sector-economy.html">Employment, productivity and goods-export chart maker</a></strong> · '
        'Five layouts with selectable economies and years · <a href="sector_economy.xlsx">Full Excel workbook</a></p>'
        '<p><strong><a href="broad-sectors.html">Create a six-sector GVA stacked chart</a></strong> · '
        'Choose economies and years; download PNG, SVG and CSV · '
        '<a href="broad_sector_gva.xlsx">Broad-sector Excel workbook</a></p>'
        '<p><strong>New: <a href="industry.html">Medium/high-tech exports and ISIC two-digit value added</a></strong> · '
        '<a href="industry_exports_gva.xlsx">Companion Excel workbook</a> · '
        '<a href="industry_country_coverage.csv">Country coverage</a></p>'
        '<p><a href="sources.html">Detailed data sources, exact requests and provenance</a> · '
        '<a href="source_inventory.csv">Source inventory (CSV)</a> · '
        '<a href="source_manifest.json">Original provenance manifest (JSON)</a></p>'
        '<p><a href="world-rd-income.zip">Download this build: figures, Excel/CSV data, '
        'exact source responses, methodology and Python/JavaScript code (ZIP)</a> · '
        '<a href="current_results.md">Current results and updated captions</a><br>'
        '<a href="rd_nominal_annual.csv">Nominal R&amp;D database (CSV)</a> · '
        '<a href="rd_nominal_coverage.csv">Nominal R&amp;D coverage (CSV)</a> · '
        '<a href="world_rd_income_data.xlsx">Excel workbook</a><br>'
        '<a href="rd_sector_field_annual.csv">GERD sector × field database (CSV)</a> · '
        '<a href="rd_sector_field_coverage.csv">Coverage</a> · '
        '<a href="rd_sector_field_reconciliation.csv">Reconciliation audit</a> · '
        '<a href="rd_sector_field_definitions.csv">Definitions and flags</a><br>'
        '<a href="basque_annual.csv">Basque Country: annual data and EUR/USD/PPP conversion inputs (CSV)</a><br>'
        '<a href="rd_breakdown_annual.csv">Funding and research-type database (CSV)</a> · '
        '<a href="rd_breakdown_coverage.csv">Coverage</a> · '
        '<a href="rd_breakdown_reconciliation.csv">Reconciliation</a> · '
        '<a href="rd_breakdown_definitions.csv">Definitions</a> · '
        '<a href="rd_breakdown_conversion.csv">Basque constant-price proxy inputs</a> · '
        '<a href="rd_breakdown_examples.csv">Example chart values</a></p>'
        '<p>Direct official-source checks: <a href="rd_ons_funding_reported.csv">ONS funding/performance</a> · '
        '<a href="rd_ons_funding_comparison.csv">ONS–OECD comparison audit</a> · '
        '<a href="rd_ons_intensity.csv">ONS intensity</a> · <a href="rd_official_conversion.csv">UK PPP conversion inputs</a> · '
        '<a href="rd_research_oecd_alternatives.csv">Preserved OECD UK research estimates</a></p>'
        '<details><summary>Example stacked charts · 2020–2024</summary><p>' + '<br>'.join(chart_links) + '</p></details>'
    ))
    dashboard_files = build_dashboard(destination)
    offline = (destination / 'index.html').read_text('utf-8').replace('<a href="world-rd-income.zip" download>Download data and code (ZIP)</a>', 'Data and code · extracted archive')
    for folder in ("data", "output"):
        for path in (ROOT / folder).iterdir():
            if path.is_file():
                offline = offline.replace(f'href="{path.name}"', f'href="figures/world-rd-income/{folder}/{path.name}"')
    with ZipFile(destination / "world-rd-income.zip", "a", ZIP_DEFLATED) as archive:
        archive.writestr("world-rd-income/index.html", offline)
        for name in dashboard_files:
            if name == 'index.html':
                continue
            if name.endswith('.html'):
                text = (destination / name).read_text('utf-8')
                for folder in ('data', 'output'):
                    for path in (ROOT / folder).iterdir():
                        if path.is_file():
                            text = text.replace(f'href="{path.name}"', f'href="figures/world-rd-income/{folder}/{path.name}"')
                for path in ROOT.glob('*.md'):
                    text = text.replace(f'href="{path.name}"', f'href="figures/world-rd-income/{path.name}"')
                text = text.replace('<a href="world-rd-income.zip">Full reproducible research ZIP</a>', 'This extracted research archive')
                archive.writestr('world-rd-income/' + name, text)
            else:
                archive.write(destination / name, 'world-rd-income/' + name)
    # Keep the Pages artifact below the 300 MB deployment target. The research
    # ZIP retains ordinary CSVs; these two large standalone downloads are losslessly gzipped.
    compressed_downloads=['rd_breakdown_annual.csv','rd_sector_field_annual.csv']
    for name in compressed_downloads:
        path=destination/name
        (destination/(name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
        path.unlink()
    for path in destination.glob('*.html'):
        text=path.read_text('utf-8')
        for name in compressed_downloads:text=text.replace('href="'+name+'"','href="'+name+'.gz"')
        path.write_text(text,encoding='utf-8')
    (destination / ".nojekyll").touch()
    print(f"Website ready: {destination / 'index.html'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    build_site(args.destination.resolve())


if __name__ == "__main__":
    main()
