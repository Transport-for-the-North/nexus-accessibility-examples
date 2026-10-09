import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", auto_download=["html"])

with app.setup:
    import math
    import pathlib

    import geopandas as gpd
    import marimo as mo
    import pandas as pd
    from caf.viz import mapping, web
    from matplotlib import pyplot as plt

    DATA_FOLDER = pathlib.Path(r"data\(TfN to TNE) ID278_Washington_AM")

    # Use TfN style for matplotlib plots
    plt.style.use("caf.viz.tfn")
    # Overwrite default TfN cmap with the reverse to match web maps
    plt.style.use({"image.cmap": "viridis_r"})


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Washington Access
    This notebook uses the Washington car and bus costs and population data to determine people's accessibility to other Ouput Areas.

    Load the bus travel costs (time and distance) and the car travel distances.
    """)
    return


@app.cell(expand_output=True)
def _():
    car_costs = pd.read_csv(
        DATA_FOLDER / "car_costs/car_cost.csv", index_col=["from_oa_id", "to_oa_id"]
    )

    bus_costs = pd.read_csv(
        DATA_FOLDER
        / "bus_costs/AM_queries-washington_OA_PWC_to_AM_queries-washington_OA_PWC_prepped_ODs_prepped_requests_responses_costs.csv",
        index_col=["from_id", "to_id"],
    )
    bus_costs["processed_time_min"] = bus_costs["processed_time_s"] / 60
    bus_costs["processed_distance_km"] = bus_costs["processed_distance_m"] / 1000

    mo.vstack(
        [
            mo.vstack([mo.md("### Car Costs"), car_costs]),
            mo.vstack([mo.md("### Bus Costs"), bus_costs]),
        ]
    )
    return (bus_costs,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Population Data
    Load the Output Areas population data.
    """)
    return


@app.cell(expand_output=True)
def _():
    population_paths = {
        "Car Availability": DATA_FOLDER
        / "population_csvs/02b_population_car_availability_per_OA.csv",
        "Employment Status": DATA_FOLDER
        / "population_csvs/04b_population_employment_status_per_OA.csv",
        "Economic Status": DATA_FOLDER
        / "population_csvs/05b_population_economic_status_per_OA.csv",
    }

    population = {
        i: pd.read_csv(j, index_col="OA21CD") for i, j in population_paths.items()
    }

    mo.vstack([mo.vstack([mo.md(f"### {i}"), j]) for i, j in population.items()])
    return (population,)


@app.cell(hide_code=True)
def _(population):
    mo.md(rf"""
    Combine the {len(population)} datasets into a single DataFrame.
    """)
    return


@app.function
def combine_datasets(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    concat = []
    for name, data in datasets.items():
        concat.append(data.rename(columns={i: f"{name} - {i}" for i in data.columns}))
    return pd.concat(concat, axis=1)


@app.cell
def _(population):
    combined_pop = combine_datasets(population)
    combined_pop
    return (combined_pop,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Output Areas
    Load the Output Areas and Washington boundary geospatial datasets.
    """)
    return


@app.cell
def _():
    oas = gpd.read_file(DATA_FOLDER / "shapefiles/washington_OA.shp").set_index(
        "OA21CD"
    )
    boundary = gpd.read_file(DATA_FOLDER / "shapefiles/washington_boundary.shp")

    mo.vstack(
        [
            mo.vstack([mo.md("### Output Areas"), oas]),
            mo.vstack([mo.md("### Boundary"), boundary]),
        ]
    )
    return boundary, oas


@app.cell(hide_code=True)
def _(population):
    mo.md(rf"""
    ## Population Maps
    Plot all the columns from one of the {len(population)} population datasets on a map.
    """)
    return


@app.cell
def _(population):
    selected_dataset = mo.ui.dropdown(
        list(population.keys()), "Car Availability", label="Employment Dataset"
    )
    selected_dataset
    return (selected_dataset,)


@app.cell
def _(boundary, combined_pop, oas, selected_dataset):
    layers = {}
    population_geometry = oas.merge(
        combined_pop, left_index=True, right_index=True, validate="1:1", how="left"
    )

    show = True
    for column in combined_pop.columns:
        if not column.startswith(selected_dataset.value):
            continue
        layers[column] = web.MapData(
            population_geometry,
            color_column=column,
            options=web.ExploreOptions(
                tooltip=["OA21CD"] + combined_pop.columns.tolist(), show=show
            ),
        )
        show = False

    web.map_datasets(layers, mask=boundary, mask_name="Washington Boundary")
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Bus Travel Times
    Select a single zone to show the bus travel times to/from the Output Area.
    """)
    return


@app.cell
def _(oas):
    selected_oa = mo.ui.dropdown(
        sorted(oas.index.get_level_values(0)),
        oas.index[0],
        label="Selected Output Area",
    )
    selected_from = mo.ui.checkbox(True, label="Start at Zone")

    mo.vstack([selected_oa, selected_from])
    return selected_from, selected_oa


@app.cell
def _(bus_costs, selected_from, selected_oa):
    if selected_from.value:
        bus_oa_times = bus_costs.loc[selected_oa.value, :]
        title = f"Bus Times from {selected_oa.value}"
    else:
        bus_oa_times = bus_costs.loc[:, selected_oa.value, :]
        title = f"Bus Times to {selected_oa.value}"

    selected_column = mo.ui.dropdown(
        bus_oa_times.select_dtypes((float, int)).columns,
        "processed_time_min",
        label="Mapped Column",
    )

    mo.vstack([mo.md(f"### {title}"), bus_oa_times, selected_column])
    return bus_oa_times, selected_column, title


@app.cell
def _(bus_oa_times, oas, selected_column, selected_oa, title):
    bus_times_layer = web.MapData(
        oas.join(bus_oa_times, how="left", validate="1:1"),
        selected_column.value,
        options=web.ExploreOptions(tooltip=["OA21CD"] + bus_oa_times.columns.tolist()),
    )
    web.map_datasets(
        {
            "Selected OA": web.MapData(oas.loc[[selected_oa.value]]),
            title: bus_times_layer,
        },
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Bus Accessibility
    Map the number of people which can access, or can be accessed from, the selected Output Area based on the cutoff.
    """)
    return


@app.cell
def _(bus_costs, selected_column):
    selected_cutoff = mo.ui.number(
        0,
        math.ceil(bus_costs[selected_column.value].max()),
        value=math.ceil(bus_costs[selected_column.value].median()),
        label=f"Cutoff for {selected_column.value}",
    )
    selected_cutoff
    return (selected_cutoff,)


@app.cell(hide_code=True)
def _(selected_column, selected_cutoff, selected_from):
    mo.md(rf"""
    Produce accessibility map by:

    1. Filtering the bus costs by {selected_column.value} <= {selected_cutoff.value}
    2. Joining to the population dataset to the bus cost {"start" if selected_from.value else "end"} column
    3. Calculating the total population reachable from/to each Output Area.
    """)
    return


@app.cell
def _(
    bus_costs,
    combined_pop,
    selected_column,
    selected_cutoff,
    selected_from,
):
    mask = bus_costs[selected_column.value] <= selected_cutoff.value
    print(
        f"Filtering bus times from {len(bus_costs):,} rows to {mask.sum():,} rows using {selected_column.value} <= {selected_cutoff.value:,}"
    )

    bus_access = (
        bus_costs.loc[mask, [selected_column.value]]
        .merge(
            combined_pop,
            left_on="from_id" if selected_from.value else "to_id",
            right_index=True,
            validate="m:1",
        )
        .groupby("to_id" if selected_from.value else "from_id")
        .sum()
    )

    selected_population = mo.ui.dropdown(
        combined_pop.columns.tolist(), combined_pop.columns[0], label="Column for Map"
    )

    mo.vstack(
        [
            mo.md(
                f"Filtering bus times from {len(bus_costs):,} rows to {mask.sum():,}"
                f" rows using {selected_column.value} <= {selected_cutoff.value:,}"
            ),
            bus_access,
            selected_population,
        ]
    )
    return bus_access, selected_population


@app.cell
def _(
    bus_access,
    oas,
    selected_column,
    selected_cutoff,
    selected_from,
    selected_population,
):
    mapping.heatmap_figure(
        oas.merge(
            bus_access,
            left_index=True,
            right_index=True,
            how="left",
            validate="1:1",
        ),
        selected_population.value,
        title=f"{selected_population.value} Population\nAccessible"
        f" {'from' if selected_from.value else 'to'} Output"
        f" Areas within {selected_cutoff.value} {selected_column.value}",
    )
    return


if __name__ == "__main__":
    app.run()
