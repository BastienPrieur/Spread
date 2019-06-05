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
# Class
########################################################################################################################
class user_input():
    def __init__(self):
        self = self


inp = user_input()
inp.df = pd.DataFrame()
inp.ttxd_min = 0


########################################################################################################################
# Global Functions
########################################################################################################################

def get_figure_ini():
    inp.layout_timeseries = go.Layout(
        showlegend=True,
        legend=dict(x=1.08, y=0),
        hoverdistance=2,
        height=520,
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

    inp.data_timeseries = go.Scatter()

    inp.layout_radar = go.Layout(
        showlegend=False,
        autosize=False,
        polar=dict(
            angularaxis=dict(rotation=90),
        ),
        margin=dict(t=30, b=30)
    )

    inp.data_radar = go.Scatterpolar()

    inp.slider_min = 0
    inp.slider_max = 10


def template_download_plotly(fig, slider_value):

    if 'data' in fig:
        fig_json = fig.to_plotly_json()
        if slider_value != 0:
            fig_json['layout']['title']['text'] = 'Spread at {}'.format(inp.df.index[slider_value])
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


get_figure_ini()


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
                        'data': [inp.data_radar],
                        'layout': inp.layout_radar
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
    ],
    style={'width': '95%', 'margin-left': '2.5%', 'margin-right': '2.5%'}
)


########################################################################################################################
# Read files and provide timeseries
########################################################################################################################
@app.callback([Output('cc_upload_title', 'children'),
               Output('gr_timeseries', 'figure'),
               Output('cc_slider', 'min'),
               Output('cc_slider', 'max'),
               Output('dl_fig_timeseries', 'href')],
              [Input('cc_upload', 'contents'),
               Input('cc_upload', 'filename')])
def main(content, filename):
    file_name, is_correct, min_slider, max_slider = read_imported_file(content, filename)
    if is_correct == 'Yes':
        fig_timeseries = send_data_timeseries()
    else:
        fig_timeseries = go.Figure(data=[go.Scatter()], layout=inp.layout_timeseries)

    return file_name, fig_timeseries, min_slider, max_slider, template_download_plotly(fig_timeseries, 0)


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
        min_slider, max_slider = 0, len(inp.df.index) - 1
        inp.slider_min, inp.slider_max = min_slider, max_slider
        is_correct = 'Yes'
    else:
        file_name = '**Imported file:**'
        is_correct = 'No'
        min_slider, max_slider = 0, 10
    return file_name, is_correct, min_slider, max_slider


def work_on_data():
    inp.df.rename(str.lower, axis='columns', inplace=True)
    for column in inp.df.columns:
        if '.' in column:
            inp.df = inp.df.rename(columns={column: column.split('.')[1]})

    if 'time' in inp.df.columns:
        if 'Units' in inp.df['time'][0]:
            # File coming from the OSM, we remove the two first lines (Units and Description)
            inp.df = inp.df.drop(inp.df.index[0])
            inp.df = inp.df.drop(inp.df.index[0])

    if 'ts' in inp.df.columns:
        inp.df['new_time'] = pd.to_datetime(inp.df['ts'], format='%d/%m/%Y %H:%M:%S')
    else:
        if 'date' in inp.df.columns:
            inp.df['new_time'] = pd.to_datetime(inp.df['date'] + ' ' + inp.df['time'])
        else:
            inp.df['new_time'] = pd.to_datetime(inp.df['time'])
    inp.df.set_index('new_time', inplace=True)

    if "dwatt" in inp.df.columns:
        inp.df['dwatt'] = pd.to_numeric(inp.df['dwatt'])
    else:
        inp.df.loc[:, 'dwatt'] = 0

    if 'tnh' in inp.df.columns:
        inp.df['tnh'] = pd.to_numeric(inp.df['tnh'])
    else:
        inp.df.loc[:, 'tnh'] = 0

    ttxd_count = 0
    for idx_ttxd in inp.df.columns:
        if 'ttxd_' in idx_ttxd:
            inp.df[idx_ttxd] = pd.to_numeric(inp.df[idx_ttxd])
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


########################################################################################################################
# Provide radar and green shape on slider change
########################################################################################################################
@app.callback([Output('gr_radar', 'figure'),
               Output('gr_table', 'data'),
               Output('slider_value', 'children'),
               Output('relay', 'layout'),
               Output('dl_fig_radar', 'href')],
              [Input('cc_slider', 'value'),
               Input('radar_range', 'value')])
def update_slider(slider_value, radar_extr):
    if len(inp.df) > 0:
        fig_radar = send_data_radar(slider_value, radar_extr)
        data_table = send_data_table(slider_value)
        radar_date = str(inp.df.index[slider_value])
        new_layout = relayout_timeseries(slider_value)
    else:
        fig_radar = go.Figure(data=[go.Scatterpolar()], layout=inp.layout_radar)
        data_table = []
        radar_date = '0'
        new_layout = inp.layout_timeseries
    return fig_radar, data_table, radar_date, new_layout, template_download_plotly(fig_radar, slider_value)


def send_data_radar(radar_idx, radar_extr):

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

    inp.layout_radar['polar'].radialaxis = dict(range=(radar_extr[0], radar_extr[1]))
    inp.layout_radar['title']['text'] = ''

    fig_radar = go.Figure(data=inp.data_radar, layout=inp.layout_radar)

    return fig_radar


def send_data_table(radar_idx):
    tab_calc = []
    for idx_ttxd in inp.tab_ttxd:
        if inp.df[idx_ttxd].mean() > 0:
            tab_calc.append(idx_ttxd)

    spread = max(inp.df.loc[inp.df.index[radar_idx], tab_calc]) - min(inp.df.loc[inp.df.index[radar_idx], tab_calc])
    df_t = pd.DataFrame(index=[0], columns=['TNH', 'DWATT', 'TTXM', 'TTSXP'])
    df_t.loc[0, 'TNH'] = round(inp.df.loc[inp.df.index[radar_idx], 'tnh'], 3)
    df_t.loc[0, 'DWATT'] = round(inp.df.loc[inp.df.index[radar_idx], 'dwatt'], 3)
    df_t.loc[0, 'TTXM'] = round(np.mean(inp.df.loc[inp.df.index[radar_idx], tab_calc]), 1)
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
# Timeseries click
########################################################################################################################
@app.callback(Output('cc_slider', 'value'),
              [Input('gr_timeseries', 'clickData')])
def timeseries_click(sel_pt):

    if sel_pt is not None:
        sel_date = pd.to_datetime(sel_pt['points'][0]['x'], format='%Y-%m-%d %H:%M:%S')
        for idx in range(0, len(inp.df.index) + 1):
            if inp.df.index[idx] == sel_date:
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
