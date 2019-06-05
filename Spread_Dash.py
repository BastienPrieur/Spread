########################################################################################################################
# Libraries
########################################################################################################################
import base64
import io

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import mydcc
import os
from urllib.parse import quote

import plotly
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
# Global Functions
########################################################################################################################
layout_timeseries = go.Layout(
    showlegend=True,
    legend=dict(x=1.08, y=0),
    hoverdistance=2,
    height=480,
    yaxis=dict(
        title='TTXM [°F]'
    ),
    yaxis2=dict(
        title='TNH [%]',
        overlaying="y",
        side="right",
        showgrid=False
    )
)

layout_radar = go.Layout(
    showlegend=False,
    autosize=False,
    polar=dict(
        angularaxis=dict(rotation=90),
    ),
    margin=dict(t=30, b=30)
)


def template_download_plotly(fig, slider_date):

    if 'data' in fig:
        fig_json = fig.to_plotly_json()
        if slider_date != 0:
            fig_json['layout']['title']['text'] = 'Spread at {}'.format(slider_date)
            fig_json['layout']['margin'] = dict(t=80)
        html_body = plotly.offline.plot(fig_json, include_plotlyjs=False, output_type='div')
        html_str = '''<html>
             <head>
                 <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
             </head>
             <body>
                 {}
             </body>
             </html>
             '''.format(html_body)
        html_str = "data:text/html;charset=utf-8," + quote(html_str)

        return html_str


########################################################################################################################
# Layout
########################################################################################################################
app.layout = html.Div(
    children=[
        html.H1('Exhaust Spread Application'),
        dcc.Markdown('---'),
        dcc.Markdown('''
        Developped and imagined by Thierry DELACOUR
        Supported by Bastien PRIEUR-GARROUSTE'''),
        html.Div(
            id='df_save',
            style={'display': 'none'}
        ),
        html.Div(
            id='ttxd_save',
            style={'display': 'none'}
        ),
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
                html.Div(
                    dcc.Markdown('''Number of exhaust sensor to plot: '''),
                    style={'display': 'inline-block'}
                ),
                html.Div(
                    dcc.Dropdown(
                        id='drop_nb',
                        options=[]
                    ),
                    style={'display': 'inline-block', 'width': '25%', 'margin-left': '5%'}
                ),
                dcc.Graph(
                    id='gr_timeseries',
                    figure={
                        'data': [go.Scatter()],
                        'layout': layout_timeseries
                    }
                ),
                html.Div(
                    children=[
                        html.A(
                            'Download this Graph',
                            id='dl_fig_timeseries',
                            download="Graph_Spread_Time.html",
                            href='',
                            target="_blank"
                        )
                    ],
                    style={'width': '26%', 'margin-left': '74%'}
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
                html.Div(
                    dcc.RangeSlider(
                        id='radar_range',
                        min=0,
                        max=1200,
                        step=50,
                        marks={100 * i: '{}°F'.format(100 * i) for i in range(13)},
                        value=[100, 1000]
                    ),
                    style={'margin-bottom': '50px'}
                ),
                dcc.Graph(
                    id='gr_radar',
                    figure={
                        'data': [go.Scatterpolar()],
                        'layout': layout_radar
                    }
                ),
                html.Div(
                    children=[
                        html.A(
                            'Download this Graph',
                            id='dl_fig_radar',
                            download="Graph_Spread_Radar.html",
                            href='',
                            target="_blank"
                        )
                    ],
                    style={'width': '26%', 'margin-left': '74%'}
                ),
                dcc.Slider(
                    id='cc_slider',
                    min=0,
                    max=10,
                    step=1
                ),
                dcc.Markdown(
                    id='slider_value',
                    children=['0']
                )
            ],
            style={'width': '48%', 'float': 'right', 'display': 'inline-block'}
        )
    ],
    style={'width': '95%', 'margin-left': '2.5%', 'margin-right': '2.5%'}
)


########################################################################################################################
# Read file
########################################################################################################################
@app.callback([Output('cc_upload_title', 'children'),
               Output('drop_nb', 'options'),
               Output('cc_slider', 'min'),
               Output('cc_slider', 'max'),
               Output('df_save', 'children'),
               Output('ttxd_save', 'children')],
              [Input('cc_upload', 'contents'),
               Input('cc_upload', 'filename')])
def get_data(content, filename):

    new_file_name, min_slider, max_slider, df_data, tab_ttxd = read_imported_file(content, filename)
    drop_opt = [{'label': x, 'value': x} for x in range(1, len(tab_ttxd) + 1)]
    if content is not None:
        df_json = df_data.to_json()
    else:
        df_json = None

    return new_file_name, drop_opt, min_slider, max_slider, df_json, tab_ttxd


def read_imported_file(content, filename):
    if content is not None:
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            if ';' in df.columns[0]:
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep=";")
        elif 'xls' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
        file_name = '**Imported file:** {}'.format(filename)
        df_data, tab_ttxd = work_on_data(df)
        min_slider, max_slider = 0, len(df_data.index) - 1
    else:
        file_name = '**Imported file:**'
        min_slider, max_slider = 0, 10
        df_data = pd.DataFrame()
        tab_ttxd = []
    return file_name, min_slider, max_slider, df_data, tab_ttxd


def work_on_data(df):
    df.rename(str.lower, axis='columns', inplace=True)
    for column in df.columns:
        if '.' in column:
            df = df.rename(columns={column: column.split('.')[1]})

    if 'time' in df.columns:
        if 'Units' in df['time'][0]:
            # File coming from the OSM, we remove the two first lines (Units and Description)
            df = df.drop(df.index[0])
            df = df.drop(df.index[0])

    if 'ts' in df.columns:
        df['new_time'] = pd.to_datetime(df['ts'], format='%d/%m/%Y %H:%M:%S')
    else:
        if 'date' in df.columns:
            df['new_time'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        else:
            df['new_time'] = pd.to_datetime(df['time'])
    df.set_index('new_time', inplace=True)

    if "dwatt" in df.columns:
        df['dwatt'] = pd.to_numeric(df['dwatt'])
    else:
        df.loc[:, 'dwatt'] = 0

    if 'tnh' in df.columns:
        df['tnh'] = pd.to_numeric(df['tnh'])
    else:
        df.loc[:, 'tnh'] = 0

    ttxd_count = 0
    for idx_ttxd in df.columns:
        if 'ttxd_' in idx_ttxd:
            df[idx_ttxd] = pd.to_numeric(df[idx_ttxd])
            ttxd_count += 1

    tab_ttxd = []
    for idx_ttxd in range(0, ttxd_count):
        tab_ttxd.append("ttxd_" + str(idx_ttxd + 1))

    return df, tab_ttxd


@app.callback([Output('gr_timeseries', 'figure'),
               Output('dl_fig_timeseries', 'href')],
              [Input('drop_nb', 'value')],
              [State('df_save', 'children'),
               State('ttxd_save', 'children')])
def send_data_timeseries(drop_nb, df_json, tab_ttxd):
    if drop_nb is not None:
        if drop_nb != 0:
            df_data = pd.read_json(df_json)
            data_time = []
            time_x = list(df_data.index)
            for idx in tab_ttxd[:drop_nb]:
                data_time.append(
                    go.Scattergl(
                        x=time_x,
                        y=df_data[idx],
                        name=idx,
                        yaxis="y",
                    )
                )

            data_time.append(
                go.Scattergl(
                    x=time_x,
                    y=df_data["tnh"],
                    name="TNH",
                    yaxis="y2",
                    hoverinfo=("x", "y")
                )
            )

            fig_timeseries = go.Figure(data=data_time, layout=layout_timeseries)

        else:

            fig_timeseries = go.Figure(data=[go.Scatter()], layout=layout_timeseries)

    else:

        fig_timeseries = go.Figure(data=[go.Scatter()], layout=layout_timeseries)

    return fig_timeseries, template_download_plotly(fig_timeseries, 0)


########################################################################################################################
# Provide radar and green shape on slider change
########################################################################################################################
@app.callback([Output('gr_radar', 'figure'),
               Output('gr_table', 'data'),
               Output('slider_value', 'children'),
               Output('relay', 'layout'),
               Output('dl_fig_radar', 'href')],
              [Input('cc_slider', 'value'),
               Input('radar_range', 'value')],
              [State('df_save', 'children'),
               State('ttxd_save', 'children')])
def update_slider(slider_value, radar_extr, df_json, tab_ttxd):
    if df_json is not None:
        df_data = pd.read_json(df_json)
        fig_radar = send_data_radar(slider_value, radar_extr, df_data, tab_ttxd)
        data_table = send_data_table(slider_value, df_data, tab_ttxd)
        radar_date = str(df_data.index[slider_value])
        new_layout = relayout_timeseries(slider_value, df_data)
        slider_date = df_data.index[slider_value]
    else:
        fig_radar = go.Figure(data=[go.Scatterpolar()], layout=layout_radar)
        data_table = []
        radar_date = '0'
        new_layout = layout_timeseries
        slider_date = 0
    return fig_radar, data_table, radar_date, new_layout, template_download_plotly(fig_radar, slider_date)


def send_data_radar(radar_idx, radar_extr, df_data, tab_ttxd):

    tab_ttxd_polar = tab_ttxd
    tab_ttxd_polar.append(tab_ttxd[0])
    data_rad = df_data.loc[df_data.index[radar_idx], tab_ttxd_polar]
    plot_rad = [
        go.Scatterpolar(
            r=data_rad,
            theta=tab_ttxd_polar,
            mode="lines",
            name=str(df_data.index[radar_idx])
        )
    ]

    layout_radar['polar'].radialaxis = dict(range=(radar_extr[0], radar_extr[1]))
    layout_radar['title']['text'] = ''

    fig_radar = go.Figure(data=plot_rad, layout=layout_radar)

    return fig_radar


def send_data_table(radar_idx, df_data, tab_ttxd):
    tab_calc = []
    for idx_ttxd in tab_ttxd:
        if df_data[idx_ttxd].mean() > 0:
            tab_calc.append(idx_ttxd)

    spread = max(df_data.loc[df_data.index[radar_idx], tab_calc]) - min(df_data.loc[df_data.index[radar_idx], tab_calc])
    df_t = pd.DataFrame(index=[0], columns=['TNH', 'DWATT', 'TTXM', 'TTSXP'])
    df_t.loc[0, 'TNH'] = round(df_data.loc[df_data.index[radar_idx], 'tnh'], 3)
    df_t.loc[0, 'DWATT'] = round(df_data.loc[df_data.index[radar_idx], 'dwatt'], 3)
    df_t.loc[0, 'TTXM'] = round(np.mean(df_data.loc[df_data.index[radar_idx], tab_calc]), 1)
    df_t.loc[0, 'TTSXP'] = round(spread, 3)

    data_table = df_t.to_dict('records')

    return data_table


def relayout_timeseries(radar_idx, df_data):
    layout_timeseries.shapes = [dict(
        type='rect', xanchor=df_data.index[radar_idx], xsizemode='pixel', x0=-5, x1=5, yref='paper', y0=0, y1=1,
        opacity=0.4, fillcolor='green'
    )]
    new_layout = layout_timeseries

    return new_layout


########################################################################################################################
# Timeseries click
########################################################################################################################
@app.callback(Output('cc_slider', 'value'),
              [Input('gr_timeseries', 'clickData')],
              [State('df_save', 'children')])
def timeseries_click(sel_pt, df_json):

    if sel_pt is not None:
        sel_date = pd.to_datetime(sel_pt['points'][0]['x'], format='%Y-%m-%d %H:%M:%S')
        df_data = pd.read_json(df_json)
        sl_value = 0
        for idx in range(0, len(df_data.index) + 1):
            if df_data.index[idx] == sel_date:
                sl_value = idx
                break
    else:
        sl_value = 0

    return sl_value


########################################################################################################################
# Show app
########################################################################################################################
if __name__ == '__main__':
    app.run_server(debug=True)
