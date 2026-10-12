import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", auto_download=["html"])

with app.setup:
    import pathlib

    import folium
    import geopandas as gpd
    import marimo as mo
    import matplotlib as mpl
    import pandas as pd
    from caf.viz import mapping, web
    from matplotlib import pyplot as plt
    from matplotlib.backends import backend_pdf

    plt.style.use("caf.viz.tfn")
    mpl.rcParams["image.cmap"] = "viridis_r"

    OUTPUT_FOLDER = pathlib.Path("outputs")
    OUTPUT_FOLDER.mkdir(exist_ok=True)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Healthcare Metric

    1. Load the LSOAs
    2. Load the population (elderly) then disaggregate to health status
    3. Load the hospitals data
    4. Load in the PT travel times
    5. Calculate the accessible zones
    6. Map the accessibility
    7. Summary tables
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Load LSOAs

    Load the LSOA geometries which will be used for the mapping throughout the notebook.
    """)
    return


@app.function
def load_lsoas(path: pathlib.Path, subset_path: pathlib.Path):
    """Load LSOAs and filter to subset."""
    lsoas = gpd.read_file(path, columns=["LSOA21CD", "LSOA21NM", "geometry"]).set_index(
        "LSOA21CD"
    )
    subset = pd.read_csv(subset_path).iloc[:, 0].tolist()
    print(f"Read {len(lsoas):,} rows from LSOAs, found {len(subset):,} LSOAs in subset")
    lsoas.geometry = lsoas.simplify(10)
    return lsoas.loc[subset, :]


@app.cell
def _():
    lsoas = load_lsoas(
        "data/Workshop Data/LSOA boundaries 2021.gpkg",
        "data/Workshop Data/LSOA2021_in_Tyne_and_Wear.csv",
    )
    lsoas
    return (lsoas,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Population Data
    Read the population by age data and disaggregate using the [Bad Health Proportion](#bad-health-proportion).
    """)
    return


@app.cell
def _():
    population_path = pathlib.Path("data/Workshop Data/population-age.csv")
    population = pd.read_csv(
        population_path, index_col="lsoa2021", usecols=["lsoa2021", "65+"]
    )
    population
    return (population,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Bad Health Proportion

    The bad health proportion data is provided at OA level so before loading it we read the [Output Area (2021) to LSOA to MSOA to LEP to LAD (April 2023) Best Fit Lookup in EN (ONS)](https://geoportal.statistics.gov.uk/datasets/ons::output-area-2021-to-lsoa-to-msoa-to-lep-to-lad-april-2023-best-fit-lookup-in-en/about), which will be used to aggregate the OA population by health status to LSOA.
    """)
    return


@app.cell
def _():
    oa_lsoa_path = pathlib.Path(
        r"data/OAs_to_LSOAs_to_MSOAs_to_LEP_to_LAD_(April_2023)_Lookup_in_England.csv"
    )
    oa_lsoa = pd.read_csv(
        oa_lsoa_path, usecols=["OA21CD", "LSOA21CD"], index_col="OA21CD"
    )["LSOA21CD"]
    oa_lsoa
    return (oa_lsoa,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Define a function which reads the health status data at OA level, aggregates it to LSOA and then calculates a "bad health proportion".
    Call the function to load the health proportion data.
    """)
    return


@app.function
def read_health_status(path: pathlib.Path, lookup: pd.Series) -> pd.DataFrame:
    """Read health status Excel spreadsheet, aggregate to LSOA and calculate proportion."""
    index_col = "Area"
    total_col = "Total: All usual residents"
    bad_cols = ["Bad health", "Very bad health"]

    data = pd.read_excel(
        path,
        usecols=[index_col, total_col, *bad_cols],
        index_col=index_col,
    )
    data = data.rename(index=lookup.to_dict())
    data = data.groupby(index_col).sum()
    data["bad_health_proportion"] = data[bad_cols].sum(axis=1) / data[total_col]
    data.index.name = "LSOA"
    return data["bad_health_proportion"]


@app.cell
def _(oa_lsoa):
    health_proportion = read_health_status(
        pathlib.Path(r"data/Workshop Data/TS037 - General health 2021 OA NE.xlsx"),
        oa_lsoa,
    )
    health_proportion
    return (health_proportion,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Use the bad health proportion to disaggregate the population.
    """)
    return


@app.cell
def _(health_proportion, population):
    health_population = population.join(health_proportion, how="left", validate="1:1")
    health_population["Bad Health"] = (
        health_population["65+"] * health_population[health_proportion.name]
    )
    health_population = health_population.drop(columns=[health_proportion.name])
    health_population
    return (health_population,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Define a function which uses [caf.viz](https://cafviz.readthedocs.io/en/stable/) to plot each column in a DataFrame on a interactive map, then use the function to plot the elderly population and bad health population.
    """)
    return


@app.function
def interactive_map(geodata: gpd.GeoDataFrame, columns: list[str]) -> folium.Map:
    """Interactive map with separate layers for each column."""
    layers = {}
    show = True
    for column in columns:
        layers[column] = web.MapData(
            geodata,
            column,
            options=web.ExploreOptions(tooltip=True, show=show, legend_title=column),
        )
        show = False
    return web.map_datasets(layers)


@app.cell(expand_output=True)
def _(health_population, lsoas):
    interactive_map(
        lsoas.join(health_population, how="left", validate="1:1").reset_index(),
        health_population.columns,
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Define a function to output a PDF containing heatmaps of each column in the geospatial data.
    """)
    return


@app.function
def pdf_map(
    geodata: gpd.GeoDataFrame,
    columns: list[str],
    out_path: pathlib.Path,
    title: str = "",
) -> None:
    with backend_pdf.PdfPages(out_path) as pdf:
        for column in columns:
            fig = mapping.heatmap_figure(
                geodata,
                column,
                f"{title} - {column}" if title != "" else column,
                n_bins=min(5, geodata[column].nunique()),
            )
            pdf.savefig(fig)
            plt.close(fig)
    print(f"Written maps to {out_path}")


@app.cell
def _(health_population, lsoas):
    pdf_map(
        lsoas.join(health_population, how="left", validate="1:1").reset_index(),
        health_population.columns,
        OUTPUT_FOLDER / "population-maps.pdf",
        title="LSOA Populations",
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Hospitals
    Load the hospitals dataset and group to LSOAs.
    """)
    return


@app.cell
def _():
    hospital_lsoas = (
        gpd.read_file("data/Workshop Data/Hospitals_OAs.gpkg")
        .groupby("LSOA21CD")["Name"]
        .count()
        .to_frame()
        .rename(columns={"Name": "hospital count"})
    )
    hospital_lsoas
    return (hospital_lsoas,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## PT Travel Times
    Load the PT travel times dataset.
    """)
    return


@app.cell
def _():
    pt_times = pd.read_csv(
        r"data/Workshop Data/r5_PT_travel_times.csv", index_col=["from_id", "to_id"]
    )
    pt_times
    return (pt_times,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Define a function to calculate the accessibility to/from things.
    """)
    return


@app.function
def accessibility(
    cost: pd.Series, cutoff: float, stuff: pd.DataFrame, forward: bool = True
) -> pd.DataFrame:
    """Calculate the total amount of `stuff` which is accessible within the cutoff."""
    cut_costs = cost[cost <= cutoff]
    print(
        f"Costs filtered ({cost.name} <= {cutoff}) from {len(cost):,} to {len(cut_costs):,}"
    )
    if forward:
        join, group = "from_id", "to_id"
    else:
        join, group = "to_id", "from_id"

    access = cut_costs.to_frame().merge(
        stuff, how="left", left_on=join, right_index=True, validate="m:1"
    )
    return access.groupby(group)[stuff.columns].sum()


@app.cell(hide_code=True)
def _(selected_cutoff_time):
    mo.md(rf"""
    Join the population to the travel times with the cutoff (<= **{selected_cutoff_time.value}** mins) to show what zones are
    accessible by people, then join the hospitals to the travel time to show how many hospitals each zone can access.
    """)
    return


@app.cell
def _():
    selected_cutoff_time = mo.ui.dropdown(
        [15, 30, 60, 90, 120], value=90, label="Travel Time Cutoff (mins)"
    )
    selected_cutoff_time
    return (selected_cutoff_time,)


@app.cell
def _(health_population, hospital_lsoas, pt_times, selected_cutoff_time):
    lsoa_access = {
        "People's Access to Zones": accessibility(
            pt_times["travel_time_p50"], selected_cutoff_time.value, health_population
        ),
        "Zone Access to Hospitals": accessibility(
            pt_times["travel_time_p50"],
            selected_cutoff_time.value,
            hospital_lsoas,
            forward=False,
        ),
    }

    mo.vstack([mo.vstack([mo.md(f"### {i}"), j]) for i, j in lsoa_access.items()])
    return (lsoa_access,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Plot Access

    Plot the number of zones that people can access and the number of hospitals accessible by each zone.
    """)
    return


@app.cell
def _(lsoa_access):
    zone_access = pd.concat(
        [
            data.rename(columns={i: f"{name} - {i}" for i in data.columns})
            for name, data in lsoa_access.items()
        ],
        axis=1,
    )
    zone_access.index.name = "LSOA21CD"
    zone_access
    return (zone_access,)


@app.cell(expand_output=True)
def _(lsoas, zone_access):
    interactive_map(
        lsoas.join(zone_access, how="left", validate="1:1").reset_index(),
        zone_access.columns,
    )
    return


@app.cell
def _(lsoas, zone_access):
    pdf_map(
        lsoas.join(zone_access, how="left", validate="1:1").reset_index(),
        zone_access.columns,
        OUTPUT_FOLDER / "lsoa_access-maps.pdf",
    )
    return


@app.cell(hide_code=True)
def _(selected_hospitals):
    mo.md(rf"""
    ## People's Access to Hospitals
    Filter the zone access to hospitals to get the zones which can access **{selected_hospitals.value}**, or more, and join the population by health status to see people's access to hospitals.
    """)
    return


@app.cell
def _(lsoa_access):
    selected_hospitals = mo.ui.slider(
        0,
        int(lsoa_access["Zone Access to Hospitals"]["hospital count"].max()),
        value=3,
        label="Minimum Accessible Hospitals",
    )
    selected_hospitals
    return (selected_hospitals,)


@app.cell
def _(health_population, lsoa_access, selected_hospitals):
    hospital_access = lsoa_access["Zone Access to Hospitals"].copy()
    mask = hospital_access["hospital count"] >= selected_hospitals.value
    hospital_access = hospital_access[mask].join(
        health_population, how="left", validate="1:1"
    )
    return hospital_access, mask


@app.cell(hide_code=True)
def _(hospital_access, mask, selected_cutoff_time, selected_hospitals):
    mo.md(rf"""
    ### Results

    **{len(hospital_access):,}** ({mask.sum() / len(mask):.1%}) LSOAs have access to, at least, **{selected_hospitals.value}**
    hospitals within **{selected_cutoff_time.value}** minutes, this equates to **{hospital_access["65+"].sum():,.0f}**
    people over 65, **{hospital_access["Bad Health"].sum():,.0f}** of which have bad (or very bad) health.
    """)
    return


@app.cell
def _(health_population, hospital_access):
    summary = pd.concat(
        [
            hospital_access.drop(columns="hospital count")
            .sum()
            .rename("Hospital Access"),
            health_population.sum().rename("Total"),
        ],
        axis=1,
    )
    summary["Percentage with Access"] = summary["Hospital Access"] / summary["Total"]
    summary.index.name = "Population Group"
    mo.ui.table(
        summary,
        format_mapping={
            "Percentage with Access": "{:,.0%}",
            **dict.fromkeys(("Hospital Access", "Total"), "{:,.0f}"),
        },
        selection=None,
        show_search=False,
    )
    return


@app.cell(expand_output=True)
def _(hospital_access, lsoas):
    interactive_map(
        lsoas.join(hospital_access, how="left", validate="1:1").reset_index(),
        hospital_access.columns,
    )
    return


@app.cell
def _(hospital_access, lsoas):
    pdf_map(
        lsoas.join(hospital_access, how="left", validate="1:1").reset_index(),
        hospital_access.columns,
        OUTPUT_FOLDER / "hospital_access-maps.pdf",
    )
    return


if __name__ == "__main__":
    app.run()
