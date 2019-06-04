########################################################################################################################
# Libraries
########################################################################################################################
import base64
import io

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import mydcc
import os

import plotly.graph_objs as go

import pandas as pd
import numpy as np

########################################################################################################################
# Initialization
########################################################################################################################
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(name=__name__, external_stylesheets=external_stylesheets)
server = app.server
server.secret_key = os.environ.get('secret_key', 'secret')

########################################################################################################################
# Class
########################################################################################################################
class user_input():
    def __init__(self):
        self = self


inp = user_input()
inp.df = pd.DataFrame()
inp.ttxd_min = 0


def get_figure_ini():
    inp.layout_timeseries = go.Layout(
        showlegend=True,
        legend=dict(x=1.08, y=0),
        hoverdistance=2,
        yaxis=dict(title='TTXM'),
        yaxis2=dict(
            title='TNH',
            overlaying="y",
            side="right",
            showgrid=False
        ))

    inp.data_timeseries = go.Scatter()

    inp.layout_radar = go.Layout(
        showlegend=False,
        autosize=False,
        polar=dict(
            angularaxis=dict(rotation=90),
        ),
        margin=dict(b=30)
    )

    inp.data_radar = go.Scatterpolar()

    inp.slider_min = 0
    inp.slider_max = 10


get_figure_ini()


########################################################################################################################
# Layout
########################################################################################################################
app.layout = html.Div([
    html.H1('Exhaust Spread Application'),
    dcc.Markdown('---'),
    mydcc.Relayout(
        id='relay',
        aim='gr_timeseries'
    ),
    dcc.Upload(
            id='cc_upload',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Files')
            ]),
            style={
                'width': '99%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=False
        ),
    dcc.Markdown(
        id='cc_upload_title',
        children=['**Imported file:**']
    ),
    html.Div(
        children=[
            dcc.Graph(
                id='gr_timeseries',
                figure={
                    'data': [inp.data_timeseries],
                    'layout': inp.layout_timeseries
                }
            ),
            dash_table.DataTable(
                id='gr_table',
                columns=[{'name':'TNH', 'id':'TNH'}, {'name':'DWATT', 'id':'DWATT'},
                         {'name':'TTXM', 'id':'TTXM'}, {'name':'TTSXP', 'id':'TTSXP'}],
                style_cell={'minWidth': '25%', 'width': '25%', 'maxWidth': '25%'}
            )
        ],
        style={'width': '48%', 'display': 'inline-block'}
    ),
    html.Div(
        children=[
            dcc.Graph(
                id='gr_radar',
                figure={
                    'data': [inp.data_radar],
                    'layout': inp.layout_radar
                }
            ),
            dcc.Slider(
                id='cc_slider',
                min=inp.slider_min,
                max=inp.slider_max,
                step=1
            ),
            dcc.Markdown(
                id='slider_value',
                children=['0']
            )
        ],
        style={'width': '48%', 'float': 'right', 'display': 'inline-block'}
    )
])

########################################################################################################################
# Main
########################################################################################################################


@app.callback([Output('cc_upload_title', 'children'),
               Output('gr_timeseries', 'figure'),
               Output('cc_slider', 'min'),
               Output('cc_slider', 'max'),
               Output('cc_slider', 'value')],
              [Input('cc_upload', 'contents'),
               Input('cc_upload', 'filename')])
def main(content, filename):
    # 1. Read file
    file_name, is_correct, min_slider, max_slider = read_imported_file(content, filename)
    if is_correct == 'Yes':
        fig_timeseries = send_data_timeseries()
    else:
        fig_timeseries = go.Figure(data=[go.Scatter()], layout=inp.layout_timeseries)
    return file_name, fig_timeseries, min_slider, max_slider, min_slider


@app.callback([Output('gr_radar', 'figure'),
               Output('gr_table', 'data'),
               Output('slider_value', 'children'),
               Output('relay', 'layout')],
              [Input('cc_slider', 'value')])
def update_slider(slider_value):
    if len(inp.df) > 0:
        fig_radar = send_data_radar(slider_value)
        data_table = send_data_table(slider_value)
        radar_date = str(inp.df.index[slider_value])
        new_layout = relayout_timeseries(slider_value)
    else:
        fig_radar = go.Figure(data=[go.Scatterpolar()], layout=inp.layout_radar)
        data_table = []
        radar_date = '0'
        new_layout = inp.layout_timeseries
    return fig_radar, data_table, radar_date, new_layout


########################################################################################################################
# Functions
########################################################################################################################


def read_imported_file(content, filename):
    if content is not None:
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        if 'csv' in filename:
            inp.df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            if ';' in inp.df.columns[0]:
                inp.df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep=";")
        elif 'xls' in filename:
            inp.df = pd.read_excel(io.BytesIO(decoded))
        file_name = '**Imported file:** {}'.format(filename)
        work_on_data()
        min_slider, max_slider = 0, len(inp.df) - 1
        inp.slider_min, inp.slider_max = min_slider, max_slider
        is_correct = 'Yes'
    else:
        file_name = '**Imported file:**'
        is_correct = 'No'
        min_slider, max_slider = 0, 10
    return file_name, is_correct, min_slider, max_slider


def work_on_data():
    inp.df.rename(str.lower, axis='columns', inplace=True)
    if 'ts' in inp.df.columns:
        time_col = 'ts'
    else:
        time_col = 'time'
    inp.df['new_time'] = pd.to_datetime(inp.df[time_col])
    inp.df.set_index('new_time', inplace=True)
    if "dwatt" not in inp.df.columns:
        inp.df.loc[inp.df.index, 'dwatt'] = 0
    ttxd_count = 0
    for idx_ttxd in inp.df.columns:
        if 'ttxd_' in idx_ttxd:
            ttxd_count += 1

    inp.tab_ttxd = []
    for idx_ttxd in range(0, ttxd_count):
        inp.tab_ttxd.append("ttxd_" + str(idx_ttxd + 1))


def send_data_timeseries():
    data_time = []
    time_x = list(inp.df.index)
    for idx in inp.tab_ttxd:
        data_time.append(
            go.Scattergl(
                x=time_x,
                y=inp.df[idx],
                name=idx,
                yaxis="y",
                hoverinfo='none',
            )
        )

    data_time.append(
        go.Scattergl(
            x=time_x,
            y=inp.df["tnh"],
            name="TNH",
            yaxis="y2",
            hoverinfo=("x", "y")
        )
    )

    inp.data_timeseries = data_time

    fig_timeseries = go.Figure(data=inp.data_timeseries, layout=inp.layout_timeseries)

    return fig_timeseries


def send_data_radar(radar_idx):

    tab_ttxd_polar = inp.tab_ttxd
    tab_ttxd_polar.append(inp.tab_ttxd[0])
    data_rad = inp.df.loc[inp.df.index[radar_idx], tab_ttxd_polar]
    plot_rad = [
        go.Scatterpolar(
            r=data_rad,
            theta=tab_ttxd_polar,
            mode="lines",
            name=str(inp.df.index[radar_idx])
        )
    ]

    inp.data_radar = plot_rad

    if inp.ttxd_min == 0:
        inp.ttxd_min = min(inp.df[min(inp.df.loc[:, inp.tab_ttxd])]) - 60
        inp.ttxd_max = max(inp.df[max(inp.df.loc[:, inp.tab_ttxd])]) + 10
        inp.layout_radar['polar'].radialaxis = dict(range=(inp.ttxd_min, inp.ttxd_max))

    fig_radar = go.Figure(data=inp.data_radar, layout=inp.layout_radar)

    return fig_radar


def send_data_table(radar_idx):
    spread = max(inp.df.loc[inp.df.index[radar_idx], inp.tab_ttxd]) - \
             min(inp.df.loc[inp.df.index[radar_idx], inp.tab_ttxd])
    df_t = pd.DataFrame(index=[0], columns=['TNH', 'DWATT', 'TTXM', 'TTSXP'])
    df_t.loc[0, 'TNH'] = round(inp.df.loc[inp.df.index[radar_idx], 'tnh'], 3)
    df_t.loc[0, 'DWATT'] = round(inp.df.loc[inp.df.index[radar_idx], 'dwatt'], 3)
    df_t.loc[0, 'TTXM'] = round(np.mean(inp.df.loc[inp.df.index[radar_idx], inp.tab_ttxd]), 1)
    df_t.loc[0, 'TTSXP'] = round(spread, 3)

    data_table = df_t.to_dict('records')

    return data_table


def relayout_timeseries(radar_idx):
    inp.layout_timeseries.shapes = [dict(
        type='rect', xanchor=inp.df.index[radar_idx], xsizemode='pixel', x0=-5, x1=5, yref='paper', y0=0, y1=1,
        opacity=0.4, fillcolor='green'
    )]
    new_layout = inp.layout_timeseries
    return new_layout


########################################################################################################################
# Show app
########################################################################################################################


if __name__ == '__main__':
    app.run_server(debug=True)
