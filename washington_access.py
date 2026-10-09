import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")

with app.setup:
    import pathlib

    import marimo as mo
    import geopandas as gpd
    import pandas as pd
    from caf.viz import mapping, web

    DATA_FOLDER = pathlib.Path(r"data\(TfN to TNE) ID278_Washington_AM")


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
    car_costs = pd.read_csv(DATA_FOLDER / "car_costs/car_cost.csv", index_col=["from_oa_id", "to_oa_id"])
    bus_costs = pd.read_csv(
        DATA_FOLDER / "bus_costs/AM_queries-washington_OA_PWC_to_AM_queries-washington_OA_PWC_prepped_ODs_prepped_requests_responses_costs.csv",
        index_col=["from_id", "to_id"],
    )

    mo.vstack([
        mo.vstack([mo.md("### Car Costs"), car_costs]),
        mo.vstack([mo.md("### Bus Costs"), bus_costs]),
    ])
    return


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
        "Car Availability": DATA_FOLDER / "population_csvs/02b_population_car_availability_per_OA.csv",
        "Employment Status": DATA_FOLDER / "population_csvs/04b_population_employment_status_per_OA.csv",
        "Economic Status": DATA_FOLDER / "population_csvs/05b_population_economic_status_per_OA.csv"
    }

    population = {i: pd.read_csv(j, index_col="OA21CD") for i, j in population_paths.items()}

    mo.vstack([
        mo.vstack([mo.md(f"### {i}"), j]) for i, j in population.items()
    ])
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
    oas = gpd.read_file(DATA_FOLDER / "shapefiles/washington_OA.shp").set_index("OA21CD")
    boundary = gpd.read_file(DATA_FOLDER / "shapefiles/washington_boundary.shp")

    mo.vstack([
        mo.vstack([mo.md("### Output Areas"), oas]),
        mo.vstack([mo.md("### Boundary"), boundary]),
    ])
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
    selected_dataset = mo.ui.dropdown(list(population.keys()), "Car Availability", label="Employment Dataset")
    selected_dataset
    return (selected_dataset,)


@app.cell
def _(boundary, combined_pop, oas, selected_dataset):
    layers = {}
    population_geometry = oas.merge(combined_pop, left_index=True, right_index=True, validate="1:1", how="left")

    show = True
    for column in combined_pop.columns:
        if not column.startswith(selected_dataset.value):
            continue
        layers[column] = web.MapData(
            population_geometry,
            color_column=column,
            options=web.ExploreOptions(tooltip=combined_pop.columns.tolist(), show=show),
        )
        show = False

    web.map_datasets(layers, mask=boundary, mask_name="Washington Boundary")
    return


if __name__ == "__main__":
    app.run()
