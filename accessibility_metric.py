import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")

with app.setup:
    import pathlib
    import warnings

    import geopandas as gpd
    import marimo as mo
    import numpy as np
    import pandas as pd
    from caf.viz import mapping, web
    from matplotlib import pyplot as plt

    plt.style.use("caf.viz.tfn")
    plt.style.use({"image.cmap": "viridis_r"})


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Healthcare Metric

    1. Load in the PT travel times
    2. Load the healthcare zones data
    3. Load the population (elderly)
        1. Disaggregate to health status
    4. Calculate the accessible zones
    5. Sum the population
    6. Map
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
    Load the population health status data to disaggregate, for now generating some random values.
    """)
    return


@app.cell
def _(population):
    rng = np.random.default_rng()
    health_status = pd.DataFrame(
        {
            "Good": rng.random(len(population)) * 10,
            "Average": rng.random(len(population)) * 50,
            "Poor": rng.random(len(population)) * 5,
        },
        index=population.index,
    )
    # Scale status to sum to 1
    health_status = health_status.div(health_status.sum(axis=1), axis=0)

    not_one = health_status.sum(axis=1).round(10) != 1
    if not_one.sum() > 0:
        warnings.warn(f"{not_one.sum():,} rows don't sum to 1 for health splits")
    health_status
    return (health_status,)


@app.cell
def _():
    gpd.read_file()
    return


@app.cell
def _():
    poor_health = pd.read_excel(
        "data/Workshop Data/TS037 - General health 2021 OA NE.xlsx"
    )
    poor_health
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Use the **fake** health status proportions to disaggregate the populations.
    """)
    return


@app.cell
def _(health_status, population):
    health_population = population.merge(
        health_status.stack().to_frame(name="proportion"),
        how="left",
        right_index=True,
        left_index=True,
        validate="1:1",
    )
    health_population["65+"] = (
        health_population["65+"] * health_population["proportion"]
    )
    health_population.index.names = ["lsoa2021", "health status"]
    health_population = health_population.reset_index().pivot(
        columns="health status", index="lsoa2021", values="65+"
    )
    health_population
    return (health_population,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Switch to real health status, **this data is loaded at OAs and needs converting to LSOAs before it can be used.**
    """)
    return


@app.cell
def _():
    pd.read_excel("data/Workshop Data/TS037 - General health 2021 OA NE.xlsx")
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
def _():
    mo.md(r"""
    Join the population to the travel times with the cutoff to show what zones are accessible by people, then join the
    hospitals to the travel time to show how many hospitals each zone can access.
    """)
    return


@app.cell
def _(health_population, hospital_lsoas, pt_times):
    lsoa_access = {
        "People's Access to Zones": accessibility(
            pt_times["travel_time_p50"], 90, health_population
        ),
        "Zone Access to Hospitals": accessibility(
            pt_times["travel_time_p50"],
            90,
            hospital_lsoas,
        ),
    }

    mo.vstack([mo.vstack([mo.md(f"### {i}"), j]) for i, j in lsoa_access.items()])
    return (lsoa_access,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Plot Access

    Load LSOA geometries and plot the number of people which can reach each LSOA in the given time.
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
    lsoas.geometry = lsoas.simplify(100)
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
    Plot the number of zones that people can access and the number of hospitals accessible by each zone.
    """)
    return


@app.cell
def _(lsoa_access, lsoas):
    map_layers = {}
    for title, data in lsoa_access.items():
        geospatial = lsoas.merge(
            data, how="left", validate="1:1", left_index=True, right_index=True
        ).reset_index()
        for column in data.columns:
            map_layers[f"{title} - {column}"] = web.MapData(
                geospatial,
                column,
                options=web.ExploreOptions(tooltip=True, show=False),
            )

    web.map_datasets(map_layers)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## People's Access to Hospitals
    Filter the zone access to hospitals to get the zones which can access 1, or more, and join the population by health status to see people's access to hospitals.
    """)
    return


@app.cell
def _(health_population, lsoa_access, lsoas):
    hospital_access = lsoa_access["Zone Access to Hospitals"]
    hospital_access = hospital_access[hospital_access > 3].merge(
        health_population, how="left", left_index=True, right_index=True, validate="1:1"
    )
    gis_hospital_access = lsoas.merge(
        hospital_access, how="left", left_index=True, right_index=True, validate="1:1"
    )
    layers = {
        i: web.MapData(
            gis_hospital_access, i, options=web.ExploreOptions(tooltip=True, show=False)
        )
        for i in hospital_access.columns
    }
    web.map_datasets(layers)
    return


if __name__ == "__main__":
    app.run()
