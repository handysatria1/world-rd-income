"""Official Basque regional inputs and reproducible PxWeb POST selections."""

API = "https://www.eustat.eus/bankupx/api/v1/en/DB/"
CODE = "ES-PV"  # ISO 3166-2 subdivision, deliberately not an invented ISO3.
TABLES = {
    "rd_total": "PX_043201_cid_res01.px",
    "rd_business_pnp": "PX_043201_cid_e12.px",
    "rd_government": "PX_043201_cid_ap01.px",
    "rd_higher_education": "PX_043201_cid_es01n.px",
    "gdp_per_capita": "PX_170112_cpib_pib_a_11.px",
    "gdp_total": "PX_170112_cpib_pib_a_06.px",
}
SELECTIONS = {
    **{key: {"naturaleza": ["10"]} for key in TABLES if key.startswith("rd_")},
    "gdp_per_capita": {"territorio histórico": ["_T"]},
    "gdp_total": {"territorio histórico": ["_T"], "rama actividad (A-10)": ["70"],
                  "tipo de dato": ["10"], "tipo de medida": ["10"]},
}
SOURCES, REQUESTS = {}, {}
for key, table in TABLES.items():
    SOURCES[f"eustat_{key}_metadata.json"] = API + table
    name = f"eustat_{key}.json"
    SOURCES[name] = API + table
    REQUESTS[name] = {"query": [{"code": code, "selection": {"filter": "item", "values": values}}
                              for code, values in SELECTIONS[key].items()],
                      "response": {"format": "json-stat"}}
FACTORS = {"exchange": "PA.NUS.FCRF", "ppp": "PA.NUS.PPP"}
for key, indicator in FACTORS.items():
    SOURCES[f"wb_spain_{key}.json"] = (
        f"https://api.worldbank.org/v2/country/ESP/indicator/{indicator}"
        "?source=2&date=2000:2025&format=json&per_page=100&footnote=y")
    SOURCES[f"wb_spain_{key}_metadata.json"] = f"https://api.worldbank.org/v2/indicator/{indicator}?source=2&format=json"
SOURCES.update({
    "eustat_rd_advance_2025.html": "https://en.eustat.eus/elementos/ele0027200/not0027219_i.html",
    "eustat_rd_methodology.html": "https://en.eustat.eus/document/datos/fm_043201_i.html",
    "eustat_gdp_per_capita_notes.html": "https://en.eustat.eus/elementos/ele0014300/tbl0014375_i.html",
    "eustat_rd_fields.html": "https://en.eustat.eus/documentos/opt_1/tema_312/elem_25874/definicion.html",
})
for key in ["rd_government", "rd_higher_education"]:
    SOURCES[f"eustat_{key}.px"] = "https://www.eustat.eus/bankupx/Resources/PX/Databases/DB/" + TABLES[key]
