import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")

with app.setup:
    import pathlib

    import geopandas as gpd
    import marimo as mo
    import numpy as np
    import pandas as pd
    from matplotlib import pyplot as plt

    plt.style.use("caf.viz.tfn")

    DATA_ROOT = pathlib.Path(r"data")
    DATA_FOLDER = DATA_ROOT / "Workshop Data"


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Metro walkability - walking access to Newcastle Metros within X minutes

    This assessment compares walking access to the existing Metro network
    against access to the existing and proposed Metro network.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Directory set-up & data loading.
    Establish directory paths and load required datasets
    """)
    return


@app.cell
def _():
    # directory set-up
    proposed_network_dir = DATA_ROOT / "RG to CS - email"
    current_network_lines_dir = proposed_network_dir / "Metro_Lines"
    current_network_stops_dir = proposed_network_dir / "Metro_Stations"

    # define project CRS - BnG allows for distances in metres.
    target_crs = "EPSG:27700"

    # load infrastructure
    additional_lines = gpd.read_file(
        proposed_network_dir / "M2W_Line_PelawToSouthHylton.gpkg"
    ).to_crs(target_crs)

    additional_stops = gpd.read_file(
        proposed_network_dir / "M2W_Stations.gpkg"
    ).to_crs(target_crs)

    current_lines = gpd.read_file(
        current_network_lines_dir / "Metro_Lines.shp"
    ).to_crs(target_crs)

    current_stops = gpd.read_file(
        current_network_stops_dir / "Metro_Stations.shp"
    ).to_crs(target_crs)
    return (
        additional_lines,
        additional_stops,
        current_lines,
        current_stops,
        target_crs,
    )


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Get the impact area

    The study area is defined using a selected buffer around the current and
    proposed Metro network.
    """)
    return


@app.cell
def _(
    additional_lines,
    additional_stops,
    current_lines,
    current_stops,
    target_crs,
):
    # combine network infrastructure into relevant stages
    additional_network = gpd.GeoDataFrame(
        pd.concat([additional_lines, additional_stops], ignore_index=True),
        geometry="geometry",
        crs=target_crs,
    )

    current_network = gpd.GeoDataFrame(
        pd.concat([current_lines, current_stops], ignore_index=True),
        geometry="geometry",
        crs=target_crs,
    )
    # proposed will be current + additional.
    proposed_network = gpd.GeoDataFrame(
        pd.concat([current_network, additional_network], ignore_index=True),
        geometry="geometry",
        crs=target_crs,
    ).dissolve()

    # load the washington boundary - used to identify origins within the Washington area.
    washington_boundary = gpd.read_file(
        DATA_ROOT
        / "(TfN to TNE) ID278_Washington_AM"
        / "shapefiles"
        / "washington_boundary.shp"
    )
    washington_boundary = washington_boundary.to_crs(target_crs)
    return (
        additional_network,
        current_network,
        proposed_network,
        washington_boundary,
    )


@app.cell
def _(proposed_network):
    # apply numerous buffers to the proposed infrastructure, yielding the 'study area'
    buffers_metres = [800, 1200, 1600, 2000, 5000]

    buffered_networks = {
        str(distance): proposed_network.buffer(distance)
        for distance in buffers_metres
    }

    print(
        "Buffers applied: "
        f"{', '.join(str(distance) for distance in buffers_metres)} metres"
    )
    return (buffered_networks,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Lets visualise the proposed network, and one of the buffers (impact area) we have just created.
    """)
    return


@app.cell
def _(buffered_networks, proposed_network):
    fig, ax = plt.subplots(figsize=(10, 10))

    # Plot the 5 km buffer first as the background layer.
    buffered_networks["5000"].plot(
        ax=ax,
        color="lightblue",
        edgecolor="blue",
        alpha=0.4,
    )

    # Plot the proposed network over the buffer.
    proposed_network.plot(
        ax=ax,
        color="red",
        linewidth=2,
    )

    ax.set_title("Proposed Metro Network and 5 km Buffer")
    ax.set_axis_off()

    plt.tight_layout()
    plt.show()

    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Select a specific impact area for this study and visualise the current and additional networks with the study origins - arbitrarily let's select 5,000 metres.
    """)
    return


@app.cell
def _(buffered_networks):
    SELECTED_BUFFER = 5000
    study_area = buffered_networks[str(SELECTED_BUFFER)]
    return SELECTED_BUFFER, study_area


@app.cell
def _(study_area):
    output_area_origins = gpd.read_file(DATA_FOLDER / "OA 2021 PWC.gpkg")

    # clip the loaded origins to the study area buffer.
    output_area_origins = output_area_origins.to_crs(study_area.crs)
    output_area_origins_clipped = output_area_origins.clip(study_area)

    output_area_origins_clipped = (
        output_area_origins_clipped
        .dropna(subset=["OA21CD", "geometry"])
        .drop_duplicates(subset="OA21CD")
        .copy()
    )

    print(
        f"{output_area_origins_clipped['OA21CD'].nunique():,} origins remain ({len(output_area_origins):,} loaded) "
        "within the study area."
    )
    return (output_area_origins_clipped,)


@app.cell
def _(
    SELECTED_BUFFER,
    buffered_networks,
    output_area_origins_clipped,
    proposed_network,
):
    fig2, ax2 = plt.subplots(figsize=(10, 10))

    # Plot the 5 km buffer first as the background layer.
    buffered_networks[str(SELECTED_BUFFER)].plot(
        ax=ax2,
        color="lightblue",
        edgecolor="blue",
        alpha=0.4,
    )

    # Plot the proposed network over the buffer.
    proposed_network.plot(
        ax=ax2,
        color="red",
        linewidth=2,
    )

    output_area_origins_clipped.plot(
        ax=ax2,
        color="blue",
        alpha=0.2,
    )


    ax2.set_title(f"Proposed Metro Network and origins within {SELECTED_BUFFER:,}m Buffer")
    ax2.set_axis_off()

    plt.tight_layout()
    plt.show()


    # output_area_origins_clipped.plot()
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Now we have defiend the study area, transport network and relevant origins, let us export this data to route and derive walking costs from OA origins to the current and proposed metro stops.
    """)
    return


@app.cell
def _(additional_stops, current_stops, output_area_origins_clipped):
    current_stops_export = current_stops.copy()
    additional_stops_export = additional_stops.copy()

    for label, stations in (
        ("current", current_stops_export),
        ("additional", additional_stops_export),
    ):
        if "StationName" not in stations.columns:
            if "Name" not in stations.columns:
                raise KeyError(
                    f"The {label} station data contains neither "
                    "'StationName' nor 'Name'."
                )
            stations["StationName"] = stations["Name"]
        elif "Name" in stations.columns:
            stations["StationName"] = stations["StationName"].fillna(
                stations["Name"]
            )

        stations["StationName"] = (
            stations["StationName"].astype("string").str.strip()
        )

    current_stops_export = (
        current_stops_export
        .dropna(subset=["StationName", "geometry"])
        .drop_duplicates(subset="StationName")
        .copy()
    )
    additional_stops_export = (
        additional_stops_export
        .dropna(subset=["StationName", "geometry"])
        .drop_duplicates(subset="StationName")
        .copy()
    )

    all_stations = gpd.GeoDataFrame(
        pd.concat(
            [current_stops_export, additional_stops_export],
            ignore_index=True,
        ),
        geometry="geometry",
        crs=current_stops_export.crs,
    ).drop_duplicates(subset="StationName")

    current_station_ids = set(current_stops_export["StationName"])
    all_station_ids = set(all_stations["StationName"])

    output_area_origins_clipped[["OA21CD", "geometry"]].to_csv(
        "oa2021_pwc_in_study_area.csv",
        index=False,
    )
    all_stations[["StationName", "geometry"]].to_csv(
        "all_stations.csv",
        index=False,
    )

    print(f"Exported {len(output_area_origins_clipped):,} origins.")
    print(f"Exported {len(all_stations):,} unique stations.")
    print(f"Current stations: {len(current_station_ids):,}.")
    print(
        f"Additional stations: "
        f"{len(all_station_ids - current_station_ids):,}."
    )
    return all_station_ids, current_station_ids


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Post-processing

    Now walking costs are complete - load these in and process derived costs to understand walkability to the metro network pre and post proposed intervention.

    Load the costs and apply or currently selected journey time cap in minutes.
    """)
    return


@app.cell
def _():
    # First, define the JT cap (X mins) for our analysis.
    JT_CAP_MINS = 15
    return (JT_CAP_MINS,)


@app.cell
def _(JT_CAP_MINS):
    # Define path to GraphHopper costs.
    costs_path = (
        pathlib.Path(r"Y:\Accessibility\washington-metro-trip-data")
        / "post workshop data"
        / (
            "oa2021_pwc_in_study_area_to_all_stations_"
            "prepped_ODs_CrowFly_100km_prepped_requests_"
            "responses_costs.csv"
        )
    )

    if not costs_path.exists():
        raise FileNotFoundError(f"Could not find the routed costs file:\n{costs_path}")

    # Read and validate costs data.
    costs = pd.read_csv(costs_path, low_memory=False)
    required_columns = {"from_id", "to_id", "processed_time_s"}
    missing_columns = required_columns - set(costs.columns)
    if missing_columns:
        raise KeyError(
            "The routed costs file is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    print(f"Loaded {len(costs):,} routed costs.")

    # Format data types.
    costs["processed_time_s"] = pd.to_numeric(
        costs["processed_time_s"], errors="coerce"
    )
    costs = costs.dropna(
        subset=["from_id", "to_id", "processed_time_s"]
    ).copy()
    costs["from_id"] = costs["from_id"].astype("string").str.strip()
    costs["to_id"] = costs["to_id"].astype("string").str.strip()

    # Filter costs based on defined JT CAP MINS.
    costs = costs.loc[
        costs["processed_time_s"] <= JT_CAP_MINS * 60
    ].copy()

    print(
        f"Filtered walking costs to journeys <= {JT_CAP_MINS} minutes."
    )
    print(f"Post-filter costs remaining: {len(costs):,}.")
    return (costs,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Accessibility evidence

    Make use of the journey time capped costs to create evidence on improved walkability to metro network including the additional/proposed stops.

    Baseline access includes current Metro stations. <br>
    Intervention access includes current and proposed Metro stations. <br>
    Origins with no station within the journey-time cap are retained with zero access.
    """)
    return


@app.cell(hide_code=True)
def _(
    all_station_ids,
    costs,
    current_station_ids,
    output_area_origins_clipped,
):
    all_origin_ids = (
        output_area_origins_clipped["OA21CD"]
        .astype("string")
        .str.strip()
        .dropna()
        .drop_duplicates()
        .tolist()
    )

    # Get accessibile metro stops.
    baseline_costs = costs.loc[
        costs["to_id"].isin(current_station_ids)
    ].drop_duplicates(subset=["from_id", "to_id"])
    intervention_costs = costs.loc[
        costs["to_id"].isin(all_station_ids)
    ].drop_duplicates(subset=["from_id", "to_id"])

    baseline_counts = baseline_costs.groupby("from_id").size()
    intervention_counts = intervention_costs.groupby("from_id").size()

    base_metro_total_access = (
        baseline_counts
        .reindex(all_origin_ids, fill_value=0)
        .rename("n_metro_access")
        .rename_axis("from_id")
        .reset_index()
    )
    intervention_metro_total_access = (
        intervention_counts
        .reindex(all_origin_ids, fill_value=0)
        .rename("n_metro_access")
        .rename_axis("from_id")
        .reset_index()
    )

    base_metro_total_access["has_metro_access"] = (
        base_metro_total_access["n_metro_access"] >= 1
    )
    intervention_metro_total_access["has_metro_access"] = (
        intervention_metro_total_access["n_metro_access"] >= 1
    )

    base_access_to_metro = int(
        base_metro_total_access["has_metro_access"].sum()
    )
    intervention_access_to_metro = int(
        intervention_metro_total_access["has_metro_access"].sum()
    )

    unmatched_ids = sorted(set(costs["to_id"]) - set(all_station_ids))
    print(
        f"Origins represented in each result: "
        f"{len(base_metro_total_access):,}."
    )
    if unmatched_ids:
        print(
            f"Warning: {len(unmatched_ids):,} unique to_id values did not "
            f"match StationName. First values: {unmatched_ids[:10]}"
        )
    return (
        base_access_to_metro,
        base_metro_total_access,
        intervention_access_to_metro,
        intervention_metro_total_access,
    )


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ^ 1,708 unique to_id values did not match station names.<br>That is because the derived GraphHopper costs contain both access (to metro stops) and egress (from metro to origins) costs.<br>This analysis is focused on Access to the metro.
    """)
    return


@app.cell(hide_code=True)
def _(
    JT_CAP_MINS,
    base_access_to_metro,
    intervention_access_to_metro,
    output_area_origins_clipped,
):
    total_origins = len(output_area_origins_clipped)
    net_change = intervention_access_to_metro - base_access_to_metro
    baseline_pct = base_access_to_metro / total_origins * 100 if total_origins else np.nan
    intervention_pct = (
        intervention_access_to_metro / total_origins * 100
        if total_origins
        else np.nan
    )
    pct_increase = (
        net_change / base_access_to_metro * 100
        if base_access_to_metro
        else np.nan
    )

    print(
        f"Baseline Metro access: {base_access_to_metro:,}/{total_origins:,} "
        f"within {JT_CAP_MINS} minutes ({baseline_pct:,.2f}%)."
    )
    print(
        f"Intervention Metro access: {intervention_access_to_metro:,}/"
        f"{total_origins:,} within {JT_CAP_MINS} minutes "
        f"({intervention_pct:,.2f}%)."
    )
    print(f"Net increase in origins with access: {net_change:,}.")
    print(
        "Change in proportion with access: "
        f"{intervention_pct - baseline_pct:,.2f} percentage points."
    )
    if np.isnan(pct_increase):
        print("Relative percentage increase is undefined because baseline access is zero.")
    else:
        print(f"Percentage increase relative to baseline: {pct_increase:,.2f}%.")
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Washington-only walk assessment

    Washington origins are selected spatially from the study-area origins.
    """)
    return


@app.cell(hide_code=True)
def _(
    base_metro_total_access,
    intervention_metro_total_access,
    output_area_origins_clipped,
    washington_boundary,
):
    washington_boundary_aligned = washington_boundary.to_crs(
        output_area_origins_clipped.crs
    )
    try:
        washington_geometry = washington_boundary_aligned.geometry.union_all()
    except AttributeError:
        washington_geometry = washington_boundary_aligned.geometry.unary_union

    washington_origins = output_area_origins_clipped.loc[
        output_area_origins_clipped.geometry.intersects(washington_geometry)
    ].copy()
    washington_origins["OA21CD"] = (
        washington_origins["OA21CD"].astype("string").str.strip()
    )
    washington_origins = (
        washington_origins
        .dropna(subset=["OA21CD", "geometry"])
        .drop_duplicates(subset="OA21CD")
    )
    washington_origin_ids = set(washington_origins["OA21CD"])

    washington_base_total_access_to_metro = base_metro_total_access.loc[
        base_metro_total_access["from_id"].isin(washington_origin_ids)
    ].copy()
    washington_intervention_total_access_to_metro = (
        intervention_metro_total_access.loc[
            intervention_metro_total_access["from_id"].isin(
                washington_origin_ids
            )
        ].copy()
    )

    washington_base_access_to_metro = int(
        washington_base_total_access_to_metro["has_metro_access"].sum()
    )
    washington_intervention_access_to_metro = int(
        washington_intervention_total_access_to_metro[
            "has_metro_access"
        ].sum()
    )

    print(
        "Origins within both Washington and the study area: "
        f"{len(washington_origin_ids):,}."
    )
    print(
        "Washington origins matched to baseline results: "
        f"{len(washington_base_total_access_to_metro):,}."
    )
    print(
        "Washington origins matched to intervention results: "
        f"{len(washington_intervention_total_access_to_metro):,}."
    )
    return (
        washington_base_access_to_metro,
        washington_base_total_access_to_metro,
        washington_boundary_aligned,
        washington_intervention_access_to_metro,
        washington_intervention_total_access_to_metro,
    )


@app.cell(hide_code=True)
def _(
    JT_CAP_MINS,
    washington_base_access_to_metro,
    washington_base_total_access_to_metro,
    washington_intervention_access_to_metro,
    washington_intervention_total_access_to_metro,
):
    total_washington_origins = len(washington_base_total_access_to_metro)
    if len(washington_intervention_total_access_to_metro) != total_washington_origins:
        raise ValueError(
            "Baseline and intervention Washington results have different "
            "numbers of origins."
        )

    washington_net_change = (
        washington_intervention_access_to_metro
        - washington_base_access_to_metro
    )
    washington_baseline_pct = (
        washington_base_access_to_metro / total_washington_origins * 100
        if total_washington_origins
        else np.nan
    )
    washington_intervention_pct = (
        washington_intervention_access_to_metro
        / total_washington_origins
        * 100
        if total_washington_origins
        else np.nan
    )
    washington_pct_increase = (
        washington_net_change / washington_base_access_to_metro * 100
        if washington_base_access_to_metro
        else np.nan
    )

    print(
        f"Baseline Washington Metro access: "
        f"{washington_base_access_to_metro:,}/{total_washington_origins:,} "
        f"within {JT_CAP_MINS} minutes ({washington_baseline_pct:,.2f}%)."
    )
    print(
        f"Intervention Washington Metro access: "
        f"{washington_intervention_access_to_metro:,}/"
        f"{total_washington_origins:,} within {JT_CAP_MINS} minutes "
        f"({washington_intervention_pct:,.2f}%)."
    )
    print(f"Net increase in Washington origins with access: {washington_net_change:,}.")
    print(
        "Change in Washington proportion with access: "
        f"{washington_intervention_pct - washington_baseline_pct:,.2f} percentage points."
    )
    if np.isnan(washington_pct_increase):
        print(
            "Relative percentage increase is undefined because baseline "
            "Washington access is zero."
        )
    else:
        print(
            "Percentage increase relative to the Washington baseline: "
            f"{washington_pct_increase:,.2f}%."
        )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    With analysis complete - let us visualise the whole network, stuudy area (buffered network) and the specific Washing5ton boundary of intrest.
    """)
    return


@app.cell(hide_code=True)
def _(
    SELECTED_BUFFER,
    additional_network,
    buffered_networks,
    current_network,
    output_area_origins_clipped,
    washington_boundary_aligned,
):
    fig3, ax3 = plt.subplots(figsize=(10, 10))

    # Plot the 5 km buffer first as the background layer.
    buffered_networks[str(SELECTED_BUFFER)].plot(
        ax=ax3,
        color="lightblue",
        edgecolor="blue",
        alpha=0.4,
    )

    # Plot the proposed network over the buffer.
    #  current network / additiional network
    current_network.plot(
        ax=ax3,
        color="black",
        linewidth=2,
    )

    additional_network.plot(
        ax=ax3,
        color="red",
        linewidth=2
    )

    output_area_origins_clipped.plot(
        ax=ax3,
        color="blue",
        alpha=0.2,
    )

    washington_boundary_aligned.geometry.boundary.plot(
        ax=ax3,
        color="green",
        linewidth=2,
    )

    ax3.set_title(f"Current and Additional Metro Network and OA2021 origins within {SELECTED_BUFFER:,}m Buffer - including Washington Boundary")
    ax3.set_axis_off()

    plt.tight_layout()
    plt.show()


    # output_area_origins_clipped.plot()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
