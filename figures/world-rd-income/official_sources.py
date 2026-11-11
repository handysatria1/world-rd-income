"""Direct national/regional sources and documentation for the coverage audit."""

ONS = "https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/researchanddevelopmentexpenditure/"
FILES = {
    "ons_gerd_2024.xlsx": "ukgrossdomesticexpenditureonresearchanddevelopment2021designatedasnationalstatistics/2024/gerd2024.xlsx",
    "ons_goverd_2024.xlsx": "scienceengineeringandtechnologystatisticsreferencetables/current/goverd2024.xlsx",
    "ons_berd_2024.xlsx": "businessenterpriseresearchanddevelopmentukdesignatedasofficialstatistics/2024/berd2024official.xlsx",
    "ons_berd_2023.xlsx": "businessenterpriseresearchanddevelopmentukdesignatedasofficialstatistics/2023/berd2023official.xlsx",
    "ons_berd_2022.xlsx": "businessenterpriseresearchanddevelopmentukdesignatedasofficialstatistics/2022/rftberd2022datasetofficialstatistics1.xlsx",
    "ons_gerd_2023_official.xlsx": "ukgrossdomesticexpenditureonresearchanddevelopment2021designatedasofficialstatistics/2023/gerdofficial2023.xlsx",
}
SOURCES = {name: "https://www.ons.gov.uk/file?uri=" + ONS.split(".uk", 1)[1] + "datasets/" + path
           for name, path in FILES.items()}
SOURCES.update({
    "ons_gerd_2024_bulletin.html": ONS + "bulletins/ukgrossdomesticexpenditureonresearchanddevelopment/2024",
    "ons_goverd_2024_bulletin.html": ONS + "bulletins/ukgovernmentexpenditureonscienceengineeringandtechnology/2024",
    "ons_berd_2024_bulletin.html": ONS + "bulletins/businessenterpriseresearchanddevelopment/2024",
    "eustat_rd_catalog.html": "https://en.eustat.eus/banku/id_043201/indexlistaopera.html",
    "eustat_rd_tables.html": "https://en.eustat.eus/estadisticas/tema_312/opt_1/tipo_1/temas.html",
    "ine_rd_regions_2024.html": "https://www.ine.es/dynt3/inebase/index.htm?padre=12876&capsel=12883",
})
