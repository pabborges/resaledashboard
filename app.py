import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

import numpy as np
import pandas as pd
import datetime
from datetime import datetime as dt
import pathlib
from dash import dash_table

app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# Path
BASE_PATH = pathlib.Path(__file__).parent.resolve()
DATA_PATH = BASE_PATH.joinpath("data").resolve()

# Read data
df = pd.read_csv(DATA_PATH.joinpath("clinical_analytics2.csv"))

clinic_list = df["Clinic Name"].unique()
df["Admit Source"] = df["Admit Source"].fillna("Not Identified")
admit_list = df["Admit Source"].unique().tolist()

# Date
# Format checkin Time
df["Check-In Time"] = df["Check-In Time"].apply(
    lambda x: dt.strptime(x, "%Y-%m-%d %I:%M:%S %p")
)  # String -> Datetime

# Insert weekday and hour of checkin time
df["Days of Wk"] = df["Check-In Hour"] = df["Check-In Time"]
df["Days of Wk"] = df["Days of Wk"].apply(
    lambda x: dt.strftime(x, "%A")
)  # Datetime -> weekday string

df["Check-In Hour"] = df["Check-In Hour"].apply(
    lambda x: dt.strftime(x, "%I %p")
)  # Datetime -> int(hour) + AM/PM

day_list = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

check_in_duration = df["Check-In Time"].describe()

# Register all departments for callbacks
all_departments = df["Department"].unique().tolist()

def description_card():
    """
    :return: A Div containing dashboard title & descriptions.
    """
    return html.Div(
        id="description-card",
        children=[
            html.H5("Resale Analytics"),
            html.H3("Welcome to the Resale Analytics Dashboard"),
            html.Div(
                id="intro",
                children="Explore devices volume by tech, date, and category",
            ),
        ],
    )

def generate_control_card():
    """
    :return: A Div containing controls for graphs.
    """
    return html.Div(
        id="control-card",
        children=[
            html.P("Select tech"),
            dcc.Dropdown(
                id="clinic-select",
                options=[{"label": i, "value": i} for i in clinic_list],
                value=[clinic_list[0]],  # Default to the first clinic
                multi=True,  # Allow multiple selection
            ),
            html.Br(),
            html.P("Select Date Range"),
            dcc.DatePickerRange(
                id="date-picker-select",
                start_date=dt(2022, 4, 27),
                end_date=dt(2023, 9, 13),
                min_date_allowed=dt(2022, 4, 27),
                max_date_allowed=dt(2023, 9, 13),
                initial_visible_month=dt(2022, 4, 27),
            ),
            html.Br(),
            html.Br(),
            html.P("Select Category"),
            dcc.Dropdown(
                id="admit-select",
                options=[{"label": i, "value": i} for i in admit_list],
                value=[],
                multi=True,
            ),
            html.Br(),
        ],
    )

def generate_patient_volume_heatmap(start, end, clinics, admit_type):
    """
    :param: start: start date from selection.
    :param: end: end date from selection.
    :param: clinics: list of clinics from selection.
    :param: admit_type: admission type from selection.
    :return: Patient volume annotated heatmap.
    """

    x_axis = [dt.strptime(f"{i:02}:00", "%H:%M").strftime("%I %p") for i in range(7, 19)]
    y_axis = day_list

    z = np.zeros((7, 24))
    annotations = []

    for clinic in clinics:
        filtered_df = df[(df["Clinic Name"] == clinic) & (df["Admit Source"].isin(admit_type))]
        filtered_df = filtered_df.sort_values("Check-In Time").set_index("Check-In Time")[start:end]

        for ind_y, day in enumerate(y_axis):
            filtered_day = filtered_df[filtered_df["Days of Wk"] == day]
            for ind_x, x_val in enumerate(x_axis):
                sum_of_record = filtered_day[filtered_day["Check-In Hour"] == x_val]["Number of Records"].sum()
                z[ind_y][ind_x] += sum_of_record  # Accumulate values

    hovertemplate = "<b> %{y}  %{x} <br><br> %{z} Devices Records"

    data = [
        dict(
            x=x_axis,
            y=y_axis,
            z=z,
            type="heatmap",
            name="",
            hovertemplate=hovertemplate,
            showscale=False,
            colorscale=[[0, "#caf3ff"], [1, "#2c82ff"]],
        )
    ]

    layout = dict(
        margin=dict(l=70, b=50, t=50, r=50),
        modebar={"orientation": "v"},
        font=dict(family="Open Sans"),
        xaxis=dict(
            side="top",
            ticks="",
            ticklen=2,
            tickfont=dict(family="sans-serif"),
            tickcolor="#ffffff",
        ),
        yaxis=dict(
            side="left", ticks="", tickfont=dict(family="sans-serif"), ticksuffix=" "
        ),
        hovermode="closest",
        showlegend=False,
    )
    return {"data": data, "layout": layout}

# Create an empty DataTable to display patient volume
patient_volume_table = dash_table.DataTable(
    id="patient_volume_table",
    columns=[
        {"name": "Tech", "id": "Clinic Name"},
        {"name": "Total Records", "id": "Total Records"},
    ],
)

app.layout = html.Div(
    id="app-container",
    children=[
        # Left column
        html.Div(
            id="left-column",
            className="four columns",
            children=[description_card(), generate_control_card()]
        ),
        # Right column
        html.Div(
            id="right-column",
            className="eight columns",
            children=[
                # Patient Volume Heatmap
                html.Div(
                    id="patient_volume_card",
                    children=[
                        html.B("Devices Volume"),
                        html.Hr(),
                        dcc.Graph(id="patient_volume_hm"),
                        patient_volume_table  # Add the DataTable here
                    ],
                ),
            ],
        ),
    ],
)

@app.callback(
    Output("patient_volume_hm", "figure"),
    [
        Input("date-picker-select", "start_date"),
        Input("date-picker-select", "end_date"),
        Input("clinic-select", "value"),
        Input("admit-select", "value"),
    ],
)
def update_heatmap(start, end, clinics, admit_type):
    start = start + " 00:00:00"
    end = end + " 00:00:00"

    return generate_patient_volume_heatmap(start, end, clinics, admit_type)

@app.callback(
    Output("patient_volume_table", "data"),  # Update the DataTable data
    [
        Input("clinic-select", "value"),
        Input("admit-select", "value"),
    ],
)
def update_patient_volume_table(clinics, admit_type):
    if clinics:
        # Calculate the total records for each selected clinic
        total_records = [
            {
                "Clinic Name": clinic,
                "Total Records": df[(df["Clinic Name"] == clinic) & (df["Admit Source"].isin(admit_type))]["Number of Records"].sum(),
            }
            for clinic in clinics
        ]
        return total_records
    else:
        return []

if __name__ == "__main__":
    app.run_server(debug=True, port=8051)
