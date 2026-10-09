import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")

with app.setup:
    import pathlib

    import geopandas as gpd
    import pandas as pd
    import marimo as mo
    import numpy as np
    from matplotlib import pyplot as plt

    from caf.viz import mapping, web

    DATA_FOLDER = pathlib.Path(r"data/Workshop Data")

    # Use TfN style for matplotlib plots
    plt.style.use("caf.viz.tfn")
    # Overwrite default TfN cmap with the reverse to match web maps
    plt.style.use({"image.cmap": "viridis_r"})


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # LSOA Accessibility
    This notebook loads public transport travel times at LSOA level across Newcastle and attaches population and employment data to show accessibility.
    """)
    return


@app.cell
def _():
    lsoas = gpd.read_file(DATA_FOLDER / "LSOA boundaries 2021.gpkg").set_index("LSOA21CD")
    subset_lsoas = pd.read_csv(DATA_FOLDER / "LSOA2021_in_Tyne_and_Wear.csv", usecols=["from_id"])["from_id"].tolist()
    lsoas = lsoas.loc[subset_lsoas, :]
    lsoas
    return (lsoas,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Population Data

    Load population data which is split by age, join it to LSOA geometries and create a heatmap.
    """)
    return


@app.cell
def _():
    population = pd.read_csv(DATA_FOLDER / "population-age.csv", index_col="lsoa2021")
    population["Total"] = population.sum(axis=1)
    population
    return (population,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Create a static heatmap for the LSOA population total.
    """)
    return


@app.cell(expand_output=True)
def _(lsoas, population):
    population_lsoas = lsoas[["LSOA21NM", "geometry"]].join(population, how="inner", validate="1:1")
    mapping.heatmap_figure(population_lsoas, "Total", "Total Population by LSOA")
    return (population_lsoas,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Create an interactive web map of the LSOA population totals.
    """)
    return


@app.cell
def _(population_lsoas):
    web.map_datasets(
        {"Population": web.MapData(population_lsoas.reset_index(), color_column="Total", options=web.ExploreOptions(tooltip=True))}
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Travel Times

    Load the public transport travel times matrix.
    """)
    return


@app.cell
def _():
    pt_costs = pd.read_csv(DATA_FOLDER / "r5_PT_travel_times.csv", index_col=["from_id", "to_id"])
    pt_costs
    return (pt_costs,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Map the travel times from a selected LSOA to all others.

    Select an LSOA to use as the travel time start (or end) and a travel time percentile.
    """)
    return


@app.cell
def _(lsoas, pt_costs):
    lsoa_lookup = {j: i for i, j in lsoas["LSOA21NM"].to_dict().items()}

    selected_lsoa = mo.ui.dropdown(
        sorted(lsoa_lookup.keys()), value=list(lsoa_lookup.keys())[0], allow_select_none=False, label="LSOA"
    )
    selected_time = mo.ui.dropdown(pt_costs.columns.tolist(), value="travel_time_p50", label="Percentile")
    selected_from_to = mo.ui.checkbox(label="Travel From")
    mo.vstack([selected_lsoa, selected_time, selected_from_to])
    return lsoa_lookup, selected_from_to, selected_lsoa, selected_time


@app.cell
def _(
    lsoa_lookup,
    lsoas,
    pt_costs,
    selected_from_to,
    selected_lsoa,
    selected_time,
):
    lsoa_code = lsoa_lookup[selected_lsoa.value]

    if selected_from_to.value:
        pt_access = pt_costs.loc[lsoa_code, :]
        title = f"LSOA Travel Times from {lsoas.at[lsoa_code, 'LSOA21NM']}"
    else:
        pt_access = pt_costs.loc[:, lsoa_code, :]
        title = f"LSOA Travel Times to {lsoas.at[lsoa_code, 'LSOA21NM']}"

    lsoa_times = lsoas[["LSOA21NM", "geometry"]].merge(
        pt_access,
        left_index=True,
        right_index=True,
        validate="1:1",
        how="inner",
    )

    mapping.heatmap_figure(
        lsoa_times,
        column_name=selected_time.value,
        bins=[15, 30, 45, 60, 90, 120],
        polygon_boundary=lsoas.loc[lsoa_code, "geometry"],
        title=title,
        legend_kwds={"title": selected_time.value},
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Population Accessibility

    Join the population data to the travel times to get the number of people which can access LSOAs within the cutoff time.
    """)
    return


@app.cell
def _(population):
    selected_cutoff = mo.ui.dropdown([15, 30, 45, 60], 15, label="Cutoff Time")
    selected_population = mo.ui.dropdown(population.columns, "Total", label="Age Group")
    mo.vstack([selected_cutoff, selected_population])
    return selected_cutoff, selected_population


@app.cell
def _(population, pt_costs, selected_cutoff, selected_time):
    mask = pt_costs[selected_time.value] <= selected_cutoff.value
    print(f"{len(pt_costs):,} OD pairs, {mask.sum():,} with travel times <= {selected_cutoff.value}")

    pop_access = pt_costs[mask].reset_index().merge(
        population, left_on="from_id", right_index=True, validate="m:1", how="left"
    )
    pop_access = pop_access.groupby("to_id")[population.columns].sum()
    pop_access
    return mask, pop_access


@app.cell(hide_code=True)
def _(selected_cutoff, selected_population):
    mo.md(rf"""
    ### Population {selected_population.value} with Access to each LSOA within {selected_cutoff.value} minutes
    """)
    return


@app.cell
def _(lsoas, pop_access, selected_cutoff, selected_population):
    web.map_datasets(
        {"Population Access": web.MapData(
            lsoas[["LSOA21NM", "geometry"]].join(pop_access),
            selected_population.value,
            options=web.ExploreOptions(tooltip=True)
        )},
        textbox_text=f"Population {selected_population.value} with Access to each LSOA within {selected_cutoff.value}"
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Employment Access
    As well as looking at how many people can access LSOAs we can also look at how many jobs (or something else) a LSOA can access.
    """)
    return


@app.cell
def _():
    employment = pd.read_csv(DATA_FOLDER / "employment.csv", index_col="lsoa2021")

    selected_employment = mo.ui.dropdown(employment.columns, "Total", label="Employment Column")
    mo.vstack([selected_employment, employment])
    return employment, selected_employment


@app.cell(hide_code=True)
def _(selected_cutoff, selected_employment):
    mo.md(rf"""
    ### Employment {selected_employment.value} that each LSOA has access to within {selected_cutoff.value} minutes
    """)
    return


@app.cell
def _(employment, lsoas, mask, pt_costs, selected_cutoff, selected_employment):
    emp_access = pt_costs[mask].reset_index().merge(
        employment, left_on="to_id", right_index=True, validate="m:1", how="left"
    )
    emp_access = emp_access.groupby("from_id")[employment.columns].sum()

    emp_map = web.map_datasets(
        {"Employment Access": web.MapData(
            lsoas[["LSOA21NM", "geometry"]].join(emp_access),
            selected_employment.value,
            options=web.ExploreOptions(tooltip=["LSOA21NM", "Total", selected_employment.value])
        )},
        textbox_text=f"Population {selected_employment.value} with Access to each LSOA within {selected_cutoff.value}"
    )
    mo.vstack([emp_access, emp_map])
    return


if __name__ == "__main__":
    app.run()
