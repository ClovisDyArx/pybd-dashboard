# * -={#|#}=- * -={#|#}=- * -={#|#}=- * IMPORTS * -={#|#}=- * -={#|#}=- * -={#|#}=- * #
import dash.exceptions
import sqlalchemy
import pandas as pd
import numpy as np
from dash import Dash, html, dcc, callback, Output, Input, dash_table
import plotly.graph_objs as go
from datetime import date

# * -={#|#}=- * -={#|#}=- * -={#|#}=- * \/ \/ \/ \/ BEFORE MODIFS \/ \/ \/ \/ * -={#|#}=- * -={#|#}=- * -={#|#}=- * #
"""
app = dash.Dash(__name__,  title="Bourse", suppress_callback_exceptions=True)
server = app.server
app.layout = html.Div([
                dcc.Textarea(
                    id='sql-query',
                    value='''
                        SELECT * FROM pg_catalog.pg_tables
                            WHERE schemaname != 'pg_catalog' AND 
                                  schemaname != 'information_schema';
                    ''',
                    style={'width': '100%', 'height': 100},
                    ),
                html.Button('Execute', id='execute-query', n_clicks=0),
                html.Div(id='query-result')
             ])

@app.callback( ddep.Output('query-result', 'children'),
               ddep.Input('execute-query', 'n_clicks'),
               ddep.State('sql-query', 'value'),
             )
def run_query(n_clicks, query):
    if n_clicks > 0:
        try:
            result_df = pd.read_sql_query(query, engine)
            return html.Pre(result_df.to_string())
        except Exception as e:
            return html.Pre(str(e))
    return "Enter a query and press execute."
"""
# * -={#|#}=- * -={#|#}=- * -={#|#}=- * /\ /\ /\ /\ BEFORE MODIFS /\ /\ /\ /\ * -={#|#}=- * -={#|#}=- * -={#|#}=- * #


# * -={#|#}=- * -={#|#}=- * -={#|#}=- * TESTING VALUES * -={#|#}=- * -={#|#}=- * -={#|#}=- * #

dates = pd.date_range(start='2022-01-01', end='2022-12-31', freq='h')
num_data_points_per_day = 12
num_days = len(dates) // num_data_points_per_day

timestamps = np.repeat(dates[:num_days], num_data_points_per_day)

stock_data = pd.DataFrame({
    'Date': timestamps,
    'Stock_A': np.random.normal(100, 10, len(timestamps)),
    'Stock_B': np.random.normal(100, 10, len(timestamps))
})

for stock in ['Stock_A', 'Stock_B']:
    stock_data[f'{stock}.Open'] = stock_data.groupby(stock_data['Date'].dt.date)[stock].transform('first')
    stock_data[f'{stock}.High'] = stock_data.groupby(stock_data['Date'].dt.date)[stock].transform('max')
    stock_data[f'{stock}.Low'] = stock_data.groupby(stock_data['Date'].dt.date)[stock].transform('min')
    stock_data[f'{stock}.Close'] = stock_data.groupby(stock_data['Date'].dt.date)[stock].transform('last')

stock_data = stock_data.drop_duplicates(subset='Date', keep='first')

pure_stock_columns = [col for col in stock_data.columns if '.' not in col]


# * -={#|#}=- * -={#|#}=- * -={#|#}=- * APP SETUP * -={#|#}=- * -={#|#}=- * -={#|#}=- * #

DATABASE_URI = 'timescaledb://ricou:monmdp@db:5432/bourse'    # inside docker
# DATABASE_URI = 'timescaledb://ricou:monmdp@localhost:5432/bourse'  # outisde docker
engine = sqlalchemy.create_engine(DATABASE_URI)

ext = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__,  title="Bourse", suppress_callback_exceptions=True, external_stylesheets=ext)
server = app.server


# * -={#|#}=- * -={#|#}=- * -={#|#}=- * COMPONENTS * -={#|#}=- * -={#|#}=- * -={#|#}=- * #
# TODO : découper les parties en composants pour améliorer la lisibilité du code.

stock_selector = html.Div(children=[
    dcc.Dropdown(
        id='stock-selector',
        options=[{'label': stock, 'value': stock} for stock in pure_stock_columns[1:]],
        value=[pure_stock_columns[1]],
        multi=True
    )
])

graph_selector = html.Div(children=[
    dcc.Dropdown(
        id='visualization-type',
        options=[
            {'label': 'Lines', 'value': 'lines'},
            {'label': 'Candlesticks', 'value': 'candlesticks'}
        ],
        value='lines'  # valeur par défaut
    )
])

bollinger_switch = html.Div(children=[
    dcc.Checklist(
        id='bollinger-switch',
        options=[
            {'label': 'Show Bollinger Bands', 'value': 'bollinger'}
        ],
        value=[],
        style={'padding': "10px", 'margin-right': '10px'}
    )
])

date_picker = html.Div(children=[
    dcc.DatePickerRange(
        id='date-picker-range',
        min_date_allowed=min(stock_data['Date']),
        max_date_allowed=max(stock_data['Date']),
        start_date=min(stock_data['Date']),
        end_date=max(stock_data['Date']),
        display_format='YYYY-MM-DD'
    )
])

whole_selector = html.Div(children=[
    # Div Gauche
    html.Div(children=[
        html.Label('Select stock to display:', style={'font-weight': 'bold'}),
        stock_selector,
    ], style={'flex': 1, 'padding': "10px 10px 5px 10px"}),

    # Div Milieu
    html.Div(children=[
        html.Label('Select visualization type:', style={'font-weight': 'bold'}),
        graph_selector,
    ], style={'flex': 1, 'padding': '10px'}),

    # Div Droite
    html.Div(children=[
        bollinger_switch,
    ], style={'flex': 1, 'padding': '10px'}),

], style={'display': 'flex', 'flexDirection': 'row', 'justifyContent': 'space-between'})

stock_info_table = dash_table.DataTable(
    id='stock-table',
    columns=[
        {'name': 'Date', 'id': 'date-column'},
        {'name': 'Min', 'id': 'min-column'},
        {'name': 'Max', 'id': 'max-column'},
        {'name': 'Start', 'id': 'start-column'},
        {'name': 'End', 'id': 'end-column'},
        {'name': 'Mean', 'id': 'mean-column'},
        {'name': 'Std Dev', 'id': 'std-dev-column'}
    ],
    page_size=10,
    data=[],
    style_header={'textAlign': 'center'}
)

# * -={#|#}=- * -={#|#}=- * -={#|#}=- * APP LAYOUT * -={#|#}=- * -={#|#}=- * -={#|#}=- * #
# TODO : compléter le layout.


app.layout = html.Div([
    # Div Haute
    html.Div(children=[  # TODO
        html.Label("Barre des tâches ?", style={"font-weight": 'bold', "font-size": '20px'}),
        date_picker
    ], style={'display': 'flex', 'flexDirection': 'column', 'background-color': '#f0f0f0', 'padding': '10px', 'width': '100%'}),

    # Div Basse
    html.Div(children=[
        # Div Gauche
        html.Div(children=[
            dcc.Graph(id='stock-graph'),
            whole_selector,

        ], style={'flex': 1, 'padding': '20px', 'background-color': '#f9f9f9', 'border-radius': '10px', 'box-shadow': '0px 0px 10px rgba(0, 0, 0, 0.1)'}),

        # Div Droite
        html.Div(children=[
            html.Label("Info on selected stocks"),
            stock_info_table,
        ], style={'flex': 1, 'padding': '20px', 'background-color': '#f9f9f9', 'border-radius': '10px', 'box-shadow': '0px 0px 10px rgba(0, 0, 0, 0.1)'}),
    ], style={'display': 'flex', 'flexDirection': 'row', 'justifyContent': 'space-between'}),
])


# * -={#|#}=- * -={#|#}=- * -={#|#}=- * CALLBACKS * -={#|#}=- * -={#|#}=- * -={#|#}=- * #
# TODO : ajouter un callback pour chaque action utilisateur.
@callback(
    Output('stock-graph', 'figure'),
    Output('stock-table', 'data'),
    Input('stock-selector', 'value'),
    Input('visualization-type', 'value'),
    Input('bollinger-switch', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date')
)
def update_graph(selected_stocks, visualization_type, bollinger_switch_value, start_date, end_date):
    traces = []
    data = []
    filtered_data = stock_data[(pd.to_datetime(stock_data['Date']) >= start_date) & (pd.to_datetime(stock_data['Date']) <= end_date)]

    for current_stock in selected_stocks:
        if visualization_type == 'lines':
            traces.append(go.Scatter(x=filtered_data['Date'],
                                     y=filtered_data[current_stock],
                                     mode='lines',
                                     name=current_stock))

        elif visualization_type == 'candlesticks':
            traces.append(go.Candlestick(x=filtered_data['Date'],
                                         open=filtered_data[f'{current_stock}.Open'],
                                         high=filtered_data[f'{current_stock}.High'],
                                         low=filtered_data[f'{current_stock}.Low'],
                                         close=filtered_data[f'{current_stock}.Close'],
                                         name=current_stock))

        if 'bollinger' in bollinger_switch_value:
            # https://fr.wikipedia.org/wiki/Bandes_de_Bollinger
            mean = filtered_data[current_stock].rolling(window=20).mean()
            std = filtered_data[current_stock].rolling(window=20).std()

            upper_band = mean + (2 * std)
            lower_band = mean - (2 * std)

            traces.append(go.Scatter(x=filtered_data['Date'],
                                     y=upper_band, mode='lines',
                                     name=f'{current_stock} Bollinger\'s Upper Band',
                                     line=dict(color='blue', dash='dash')))

            traces.append(go.Scatter(x=filtered_data['Date'],
                                     y=lower_band,
                                     mode='lines',
                                     name=f'{current_stock} Bollinger\'s Lower Band',
                                     line=dict(color='red', dash='dash')))

    layout = go.Layout(title='Stock Prices', xaxis=dict(title='Date'), yaxis=dict(title='Price'))

    grouped_data = stock_data.groupby(pd.Grouper(key='Date', freq='d'))
    selected_dates = pd.date_range(start=start_date, end=end_date, freq='d')
    for date, group_data in grouped_data:
        if date in selected_dates:
            row_data = {
                'date-column': date,
                'min-column': group_data[selected_stocks].min().min(),
                'max-column': group_data[selected_stocks].max().max(),
                'start-column': group_data[selected_stocks].iloc[0, :].min(),
                'end-column': group_data[selected_stocks].iloc[-1, :].max(),
                'mean-column': group_data[selected_stocks].mean().mean(),
                'std-dev-column': group_data[selected_stocks].std().mean()
            }
            data.append(row_data)

        # Create the figure for the graph
    fig = {'data': traces, 'layout': layout}

    return fig, data


if __name__ == '__main__':
    app.run(debug=True)
