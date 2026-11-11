"""Official GERD funding/type inputs; separate from the sector/field vintage."""

OECD = "https://sdmx.oecd.org/public/rest/v1"
FLOWS = {"funding": "DSD_RDS_GERD@DF_GERD_SOF", "research": "DSD_RDS_GERD@DF_GERD_TORD"}
# Funding leaves both performer and funder free (11 SDMX dimensions).
KEYS = {"funding": ".A.G..._Z._Z._Z._Z..", "research": ".A.G.._Z._Z.._Z._Z.."}
SOURCES, REQUESTS = {}, {}
for kind, flow in FLOWS.items():
    SOURCES[f"gerd_{kind}_history.csv"] = (
        f"{OECD}/data/OECD.STI.STP,{flow},1.0/{KEYS[kind]}"
        "?startPeriod=2000&endPeriod=2025&format=csvfilewithlabels")
    SOURCES[f"gerd_{kind}_structure.xml"] = f"{OECD}/dataflow/OECD.STI.STP/{flow}/1.0?references=all"
TABLE = "PX_043201_cid_res06.px"
API = "https://www.eustat.eus/bankupx/api/v1/en/DB/"
SOURCES["eustat_rd_funding_metadata.json"] = API + TABLE
SOURCES["eustat_rd_funding.json"] = API + TABLE
SOURCES["eustat_rd_funding.px"] = "https://www.eustat.eus/bankupx/Resources/PX/Databases/DB/" + TABLE
REQUESTS["eustat_rd_funding.json"] = {"query": [], "response": {"format": "json-stat"}}
TABLE_COST = "PX_043201_cid_res05.px"
SOURCES["eustat_rd_cost_metadata.json"] = API + TABLE_COST
SOURCES["eustat_rd_cost.json"] = API + TABLE_COST
SOURCES["eustat_rd_cost.px"] = "https://www.eustat.eus/bankupx/Resources/PX/Databases/DB/" + TABLE_COST
REQUESTS["eustat_rd_cost.json"] = {"query": [], "response": {"format": "json-stat"}}
