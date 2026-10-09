import marimo

__generated_with = "0.25.1"
app = marimo.App(width="full")

with app.setup:
    import pathlib

    import geopandas as gpd
    import marimo as mo
    import numpy as np
    import pandas as pd

    from caf.viz import web

    DATA_FOLDER = pathlib.Path(r"data\Workshop Data")

    COSTS_PATH = (
        DATA_FOLDER
        / "new-metro-WALK_PT-AcessEgress"
        / "from_places_OA21_PWCs_to_to_places_NewStations_prepped_ODs_CrowFly_100km_prepped_requests_responses_costs.csv"
    )

    # This is the OA boundary file used in washington_access.py.
    # Change this path if the Output Area geometry is stored elsewhere.
    OA_BOUNDARIES_PATH = pathlib.Path(
        r"data\(TfN to TNE) ID278_Washington_AM\shapefiles\washington_OA.shp"
    )

    STATIONS = [
        "Follingsby",
        "Washington North",
        "Washington South",
    ]


    CUTOFFS_MINUTES = [15, 30, 45, 60]


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # New Metro Stations: Walking and Public Transport Accessibility

    This notebook maps walking and public transport accessibility between
    Output Areas and the three proposed Metro stations:

    - **Follingsby**
    - **Washington North**
    - **Washington South**

    Four accessibility movements are shown:

    1. Walking **to** the stations
    2. Walking **from** the stations
    3. Public transport **to** the stations
    4. Public transport **from** the stations

    Walking journey time is taken from `processed_time_s`.

    Public transport journey time is taken from `dt_delta_s`.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Load the travel-cost data

    Load the combined walking and public transport results and verify that
    the expected columns are present.
    """)
    return


@app.cell(expand_output=True)
def _():
    required_columns = {
        "from_id",
        "to_id",
        "profile",
        "processed_time_s",
        "dt_delta_s",
    }

    costs = pd.read_csv(
        COSTS_PATH,
        dtype={
            "from_id": "string",
            "to_id": "string",
            "profile": "string",
        },
        low_memory=False,
    )

    mo.vstack(
        [
            mo.md(f"**Travel-cost file:** `{COSTS_PATH}`"),
            mo.md(f"**Rows loaded:** {len(costs):,}"),
            mo.md(
                "**Profiles found:** "
                + ", ".join(sorted(costs["profile"].dropna().unique()))
            ),
            costs.head(20),
        ]
    )
    return (costs,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Process walking and public transport records

    The data is converted into a consistent long-form accessibility table
    containing:

    - Output Area ID
    - Station
    - Direction
    - Mode
    - Travel time in seconds
    - Travel time in minutes

    If more than one journey exists for the same Output Area, station,
    direction and mode, the minimum valid journey time is retained.
    """)
    return


@app.function
def prepare_accessibility_costs(
    costs: pd.DataFrame,
    stations: list[str],
) -> pd.DataFrame:
    station_set = set(stations)

    from_is_station = costs["from_id"].isin(station_set)
    to_is_station = costs["to_id"].isin(station_set)

    relevant = costs.loc[from_is_station ^ to_is_station].copy()

    irrelevant_rows = len(costs) - len(relevant)

    if irrelevant_rows:
        print(
            f"Excluded {irrelevant_rows:,} rows that were not a journey "
            "between one Output Area and one selected station."
        )

    relevant["station"] = np.where(
        relevant["from_id"].isin(station_set),
        relevant["from_id"],
        relevant["to_id"],
    )

    relevant["oa_id"] = np.where(
        relevant["from_id"].isin(station_set),
        relevant["to_id"],
        relevant["from_id"],
    )

    relevant["direction"] = np.where(
        relevant["to_id"].isin(station_set),
        "To station",
        "From station",
    )

    relevant["mode"] = relevant["profile"].map(
        {
            "foot": "Walking",
            "bus": "Public transport",
        }
    )

    relevant["travel_time_s"] = np.where(
        relevant["mode"].eq("Walking"),
        relevant["processed_time_s"],
        relevant["dt_delta_s"],
    )

    relevant["travel_time_s"] = pd.to_numeric(
        relevant["travel_time_s"],
        errors="coerce",
    )

    relevant = relevant.loc[
        relevant["mode"].notna()
        & relevant["oa_id"].notna()
        & relevant["station"].notna()
        & relevant["travel_time_s"].notna()
        & relevant["travel_time_s"].ge(0)
    ].copy()

    relevant["travel_time_min"] = relevant["travel_time_s"] / 60

    relevant = (
        relevant.groupby(
            ["oa_id", "station", "mode", "direction"],
            as_index=False,
            dropna=False,
        )
        .agg(
            travel_time_s=("travel_time_s", "min"),
            travel_time_min=("travel_time_min", "min"),
        )
        .sort_values(
            ["mode", "direction", "station", "travel_time_min", "oa_id"]
        )
        .reset_index(drop=True)
    )

    return relevant


@app.cell(expand_output=True)
def _(costs):
    accessibility_costs = prepare_accessibility_costs(
        costs=costs,
        stations=STATIONS,
    )

    journey_summary = (
        accessibility_costs.groupby(
            ["mode", "direction", "station"],
            as_index=False,
        )
        .agg(
            output_areas=("oa_id", "nunique"),
            minimum_minutes=("travel_time_min", "min"),
            median_minutes=("travel_time_min", "median"),
            maximum_minutes=("travel_time_min", "max"),
        )
        .sort_values(["mode", "direction", "station"])
    )

    for column in [
        "minimum_minutes",
        "median_minutes",
        "maximum_minutes",
    ]:

        journey_summary[column] = journey_summary[column].round(1)

    mo.vstack(
        [
            mo.md(
                f"**Valid processed OA-to-station movements:** "
                f"{len(accessibility_costs):,}"
            ),
            journey_summary,
            accessibility_costs.head(20),
        ]
    )
    return (accessibility_costs,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Load Output Area boundaries

    The Output Area code field must be `OA21CD`.

    If your OA boundaries are not stored at the path below, change
    `OA_BOUNDARIES_PATH` in the setup cell.
    """)
    return


@app.cell(expand_output=True)
def _():
    # if not OA_BOUNDARIES_PATH.exists():
    #     raise FileNotFoundError(
    #         f"Could not find the Output Area boundaries at:\n"
    #         f"{OA_BOUNDARIES_PATH}\n\n"
    #         "Update OA_BOUNDARIES_PATH in the setup cell."
    #     )

    oas = gpd.read_file(OA_BOUNDARIES_PATH)

    # if "OA21CD" not in oas.columns:
    #     raise ValueError(
    #         "The Output Area geometry does not contain an 'OA21CD' column. "
    #         f"Available columns are: {oas.columns.tolist()}"
    #     )

    oas["OA21CD"] = oas["OA21CD"].astype("string").str.strip()

    oas = (
        oas.dropna(subset=["OA21CD", "geometry"])
        .drop_duplicates(subset=["OA21CD"])
        .set_index("OA21CD")
    )
    oas = oas[["LSOA21CD", "LSOA21NM", "geometry"]]  # OA21CD is index.

    # Web maps generally expect WGS84 longitude and latitude.
    oas_web = oas.to_crs(epsg=4326)

    mo.vstack(
        [
            mo.md(f"**OA boundary file:** `{OA_BOUNDARIES_PATH}`"),
            mo.md(f"**Output Areas loaded:** {len(oas_web):,}"),
            mo.md(f"**Web-map CRS:** `{oas_web.crs}`"),
            oas_web.head(),
        ]
    )
    return oas, oas_web


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Accessibility controls

    Select a station and a travel-time cutoff.

    The controls are shared by all four maps so that walking and public
    transport accessibility can be compared consistently.
    """)
    return


@app.cell
def _(accessibility_costs):
    selected_station = mo.ui.dropdown(
        options=STATIONS,
        value=STATIONS[0],
        allow_select_none=False,
        label="Metro station",
    )

    selected_cutoff = mo.ui.slider(
        start=min(CUTOFFS_MINUTES),
        stop=max(CUTOFFS_MINUTES),
        step=15,
        value=30,
        show_value=True,
        label="Travel-time cutoff in minutes",
    )

    available_modes = accessibility_costs["mode"].unique().tolist()
    selected_mode = mo.ui.dropdown(
        options=available_modes,
        value=available_modes[0],
        allow_select_none=False,
        label="Select mode",
    )

    available_directions = accessibility_costs["direction"].unique().tolist()
    selected_direction = mo.ui.dropdown(
        options=available_directions,
        value=available_directions[0],
        allow_select_none=False,
        label="Direction",
    )

    mo.hstack(
        [selected_station, selected_mode, selected_direction, selected_cutoff],
        justify="start",
        gap=1.5,
    )

    return selected_cutoff, selected_direction, selected_mode, selected_station


@app.cell
def create_accessibility_map_data(
    accessibility_costs,
    oas,
    selected_cutoff,
    selected_direction,
    selected_mode,
    selected_station,
):
    selected_costs = accessibility_costs.loc[
        accessibility_costs["station"].eq(selected_station.value)
        & accessibility_costs["mode"].eq(selected_mode.value)
        & accessibility_costs["direction"].eq(selected_direction.value),
        ["oa_id", "travel_time_s", "travel_time_min"],
    ].copy()

    selected_costs = (
        selected_costs.sort_values("travel_time_min")
        .drop_duplicates(
            subset=["oa_id"],
            keep="first",
        )
        .set_index("oa_id")
    )

    map_data = oas[["geometry"]].join(
        selected_costs,
        how="left",
        validate="1:1",
    )

    map_data["station"] = selected_station.value
    map_data["mode"] = selected_mode.value
    map_data["direction"] = selected_direction.value
    map_data["cutoff_minutes"] = selected_cutoff.value

    map_data["within_cutoff"] = (
        map_data["travel_time_min"].notna()
        & map_data["travel_time_min"].le(selected_cutoff.value)
    )

    map_data["accessibility"] = np.select(
        [
            map_data["within_cutoff"],
            map_data["travel_time_min"].notna(),
        ],
        [
            f"Within {selected_cutoff.value} minutes",
            f"Over {selected_cutoff.value} minutes",
        ],
        default="No journey returned",
    )

    map_data["travel_time_min"] = map_data["travel_time_min"].round(1)

    reachable_count = int(map_data["within_cutoff"].sum())
    journey_count = int(map_data["travel_time_min"].notna().sum())
    return


@app.function
def accessibility_map(
    map_data: gpd.GeoDataFrame,
    title: str,
):
    return web.map_datasets(
        {
            title: web.MapData(
                map_data.reset_index(),
                color_column="accessibility",
                options=web.ExploreOptions(
                    tooltip=[
                        "OA21CD",
                        "station",
                        "mode",
                        "direction",
                        "travel_time_min",
                        "cutoff_minutes",
                        "accessibility",
                    ],
                    show=True,
                ),
            )
        },
        textbox_text=title,
    )


@app.cell(hide_code=True)
def _(selected_cutoff, selected_station):
    mo.md(rf"""
    # Results

    ## {selected_station.value}

    Current accessibility cutoff:
    **{selected_cutoff.value} minutes**
    """)
    return


@app.cell
def _():
    return


@app.function
def create_accessibility_map_data(
    accessibility_costs: pd.DataFrame,
    oas: gpd.GeoDataFrame,
    station: str,
    mode: str,
    direction: str,
    cutoff_minutes: int,
) -> tuple[gpd.GeoDataFrame, int, int]:
    selected_costs = accessibility_costs.loc[
        accessibility_costs["station"].eq(station)
        & accessibility_costs["mode"].eq(mode)
        & accessibility_costs["direction"].eq(direction),
        ["oa_id", "travel_time_s", "travel_time_min"],
    ].copy()

    selected_costs = (
        selected_costs.sort_values("travel_time_min")
        .drop_duplicates(
            subset=["oa_id"],
            keep="first",
        )
        .set_index("oa_id")
    )

    map_data = oas[["geometry"]].join(
        selected_costs,
        how="left",
        validate="1:1",
    )

    map_data["station"] = station
    map_data["mode"] = mode
    map_data["direction"] = direction
    map_data["cutoff_minutes"] = cutoff_minutes

    map_data["within_cutoff"] = (
        map_data["travel_time_min"].notna()
        & map_data["travel_time_min"].le(cutoff_minutes)
    )

    map_data["accessibility"] = np.select(
        [
            map_data["within_cutoff"],
            map_data["travel_time_min"].notna(),
        ],
        [
            f"Within {cutoff_minutes} minutes",
            f"Over {cutoff_minutes} minutes",
        ],
        default="No journey returned",
    )

    map_data["travel_time_min"] = map_data["travel_time_min"].round(1)

    reachable_count = int(map_data["within_cutoff"].sum())
    journey_count = int(map_data["travel_time_min"].notna().sum())

    return map_data, reachable_count, journey_count


@app.cell
def _(accessibility_costs, oas_web, selected_cutoff, selected_station):
    walk_to_data, walk_to_reachable, walk_to_journeys = (
        create_accessibility_map_data(
            oas=oas_web,
            accessibility_costs=accessibility_costs,
            station=selected_station.value,
            mode="Walking",
            direction="To station",
            cutoff_minutes=selected_cutoff.value,
        )
    )

    walk_to_title = (
        f"Walking to {selected_station.value}: "
        f"{walk_to_reachable:,} OAs within "
        f"{selected_cutoff.value} minutes"
    )

    walk_to_map = accessibility_map(
        map_data=walk_to_data,
        title=walk_to_title,
    )

    mo.vstack(
        [
            mo.md(
                rf"""
                ## Walking access to the station

                **{walk_to_reachable:,}** of the
                **{walk_to_journeys:,}** Output Areas with returned walking
                journeys can reach **{selected_station.value}** within
                **{selected_cutoff.value} minutes**.
                """
            ),
            walk_to_map,
        ]
    )
    return walk_to_journeys, walk_to_reachable


@app.cell
def _(accessibility_costs, oas_web, selected_cutoff, selected_station):
    walk_from_data, walk_from_reachable, walk_from_journeys = (
        create_accessibility_map_data(
            oas=oas_web,
            accessibility_costs=accessibility_costs,
            station=selected_station.value,
            mode="Walking",
            direction="From station",
            cutoff_minutes=selected_cutoff.value,
        )
    )

    walk_from_title = (
        f"Walking from {selected_station.value}: "
        f"{walk_from_reachable:,} OAs within "
        f"{selected_cutoff.value} minutes"
    )

    walk_from_map = accessibility_map(
        map_data=walk_from_data,
        title=walk_from_title,
    )

    mo.vstack(
        [
            mo.md(
                rf"""
                ## Walking access from the station

                **{walk_from_reachable:,}** of the
                **{walk_from_journeys:,}** Output Areas with returned walking
                journeys are reachable from **{selected_station.value}**
                within **{selected_cutoff.value} minutes**.
                """
            ),
            walk_from_map,
        ]
    )
    return walk_from_journeys, walk_from_reachable


@app.cell
def _(accessibility_costs, oas_web, selected_cutoff, selected_station):
    pt_to_data, pt_to_reachable, pt_to_journeys = (
        create_accessibility_map_data(
            oas=oas_web,
            accessibility_costs=accessibility_costs,
            station=selected_station.value,
            mode="Public transport",
            direction="To station",
            cutoff_minutes=selected_cutoff.value,
        )
    )

    pt_to_title = (
        f"Public transport to {selected_station.value}: "
        f"{pt_to_reachable:,} OAs within "
        f"{selected_cutoff.value} minutes"
    )

    pt_to_map = accessibility_map(
        map_data=pt_to_data,
        title=pt_to_title,
    )

    mo.vstack(
        [
            mo.md(
                rf"""
                ## Public transport access to the station

                **{pt_to_reachable:,}** of the
                **{pt_to_journeys:,}** Output Areas with returned public
                transport journeys can reach **{selected_station.value}**
                within **{selected_cutoff.value} minutes**.

                Public transport accessibility uses `dt_delta_s`.
                """
            ),
            pt_to_map,
        ]
    )
    return pt_to_journeys, pt_to_reachable


@app.cell
def _(accessibility_costs, oas_web, selected_cutoff, selected_station):
    pt_from_data, pt_from_reachable, pt_from_journeys = (
        create_accessibility_map_data(
            oas=oas_web,
            accessibility_costs=accessibility_costs,
            station=selected_station.value,
            mode="Public transport",
            direction="From station",
            cutoff_minutes=selected_cutoff.value,
        )
    )

    pt_from_title = (
        f"Public transport from {selected_station.value}: "
        f"{pt_from_reachable:,} OAs within "
        f"{selected_cutoff.value} minutes"
    )

    pt_from_map = accessibility_map(
        map_data=pt_from_data,
        title=pt_from_title,
    )

    mo.vstack(
        [
            mo.md(
                rf"""
                ## Public transport access from the station

                **{pt_from_reachable:,}** of the
                **{pt_from_journeys:,}** Output Areas with returned public
                transport journeys are reachable from
                **{selected_station.value}** within
                **{selected_cutoff.value} minutes**.

                Public transport accessibility uses `dt_delta_s`.
                """
            ),
            pt_from_map,
        ]
    )
    return pt_from_journeys, pt_from_reachable


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Accessibility comparison

    The table below compares the number of reachable Output Areas across
    the four mode and direction combinations.
    """)
    return


@app.cell
def _(
    pt_from_journeys,
    pt_from_reachable,
    pt_to_journeys,
    pt_to_reachable,
    selected_cutoff,
    selected_station,
    walk_from_journeys,
    walk_from_reachable,
    walk_to_journeys,
    walk_to_reachable,
):
    comparison = pd.DataFrame(
        [
            {
                "station": selected_station.value,
                "mode": "Walking",
                "direction": "To station",
                "cutoff_minutes": selected_cutoff.value,
                "oas_with_journeys": walk_to_journeys,
                "oas_within_cutoff": walk_to_reachable,
            },
            {
                "station": selected_station.value,
                "mode": "Walking",
                "direction": "From station",
                "cutoff_minutes": selected_cutoff.value,
                "oas_with_journeys": walk_from_journeys,
                "oas_within_cutoff": walk_from_reachable,
            },
            {
                "station": selected_station.value,
                "mode": "Public transport",
                "direction": "To station",
                "cutoff_minutes": selected_cutoff.value,
                "oas_with_journeys": pt_to_journeys,
                "oas_within_cutoff": pt_to_reachable,
            },
            {
                "station": selected_station.value,
                "mode": "Public transport",
                "direction": "From station",
                "cutoff_minutes": selected_cutoff.value,
                "oas_with_journeys": pt_from_journeys,
                "oas_within_cutoff": pt_from_reachable,
            },
        ]
    )

    comparison["percentage_within_cutoff"] = np.where(
        comparison["oas_with_journeys"].gt(0),
        (
            comparison["oas_within_cutoff"]
            / comparison["oas_with_journeys"]
            * 100
        ).round(1),
        np.nan,
    )

    comparison
    return


if __name__ == "__main__":
    app.run()
