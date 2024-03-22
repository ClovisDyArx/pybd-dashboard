# * -={#|#}=- * -={#|#}=- * -={#|#}=- * IMPORTS * -={#|#}=- * -={#|#}=- * -={#|#}=- * #


import pandas as pd
import numpy as np
from dash import Dash, html, dcc, callback, Output, Input
import plotly.graph_objs as go

# * -={#|#}=- * -={#|#}=- * -={#|#}=- * TESTING VALUES * -={#|#}=- * -={#|#}=- * -={#|#}=- * #


dates = pd.date_range(start='2022-01-01', end='2022-12-31', freq='h')
num_data_points_per_day = 48
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


ext = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, title="Dashboard Bourse", suppress_callback_exceptions=True, external_stylesheets=ext)

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

whole_selector = html.Div(children=[
    # Div Gauche
    html.Div(children=[
        html.Label('Select stock(s) to display:'),
        stock_selector,
    ], style={'padding': 10, 'flex': 1}),

    # Div Droite
    html.Div(children=[
        html.Label('Select visualization type:'),
        graph_selector,
    ], style={'padding': 10, 'flex': 1, 'padding': '0 25%'}),

], style={'display': 'flex', 'flexDirection': 'row'})

# * -={#|#}=- * -={#|#}=- * -={#|#}=- * APP LAYOUT * -={#|#}=- * -={#|#}=- * -={#|#}=- * #
# TODO : compléter le layout.


app.layout = html.Div([
    # Div Haute
    html.Div(children=[  # TODO
        html.Label("Barre des tâches ?"),
    ], style={'display': 'flex', 'flexDirection': 'row'}),

    # Div Basse
    html.Div(children=[
        # Div Gauche
        html.Div(children=[
            dcc.Graph(id='stock-graph'),
            whole_selector,

        ], style={'padding': 10, 'flex': 1}),

        # Div Droite
        html.Div(children=[
            html.Label("Infos sur le(s) stock(s) sélectionné(s)"),
        ], style={'padding': 10, 'flex': 1}),
    ], style={'display': 'flex', 'flexDirection': 'row', 'padding': '5% 0'}),
])


# * -={#|#}=- * -={#|#}=- * -={#|#}=- * CALLBACKS * -={#|#}=- * -={#|#}=- * -={#|#}=- * #
# TODO : ajouter un callback pour chaque action utilisateur.


@callback(
    Output('stock-graph', 'figure'),
    Input('stock-selector', 'value'),
    Input('visualization-type', 'value')
)
def update_graph(selected_stocks, visualization_type):
    traces = []
    for stock in selected_stocks:
        if visualization_type == 'lines':
            traces.append(go.Scatter(x=stock_data['Date'],
                                     y=stock_data[stock],
                                     mode='lines',
                                     name=stock))

        elif visualization_type == 'candlesticks':
            traces.append(go.Candlestick(x=stock_data['Date'],
                                         open=stock_data[f'{stock}.Open'],
                                         high=stock_data[f'{stock}.High'],
                                         low=stock_data[f'{stock}.Low'],
                                         close=stock_data[f'{stock}.Close'],
                                         name=stock))

    layout = go.Layout(title='Stock Prices', xaxis=dict(title='Date'), yaxis=dict(title='Price'))

    return {'data': traces, 'layout': layout}


# * -={#|#}=- * -={#|#}=- * -={#|#}=- * RUN APP * -={#|#}=- * -={#|#}=- * -={#|#}=- * #


if __name__ == '__main__':
    app.run(debug=True)
