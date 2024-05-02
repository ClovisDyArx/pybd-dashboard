# * -={#|#}=- * -={#|#}=- * -={#|#}=- * IMPORTS * -={#|#}=- * -={#|#}=- * -={#|#}=- * #
from logging import warning

import sqlalchemy
import pandas as pd
from dash import Dash, html, dcc, callback, Output, Input, dash_table
import plotly.graph_objs as go

# * -={#|#}=- * -={#|#}=- * -={#|#}=- * APP SETUP * -={#|#}=- * -={#|#}=- * -={#|#}=- * #

DATABASE_URI = 'timescaledb://ricou:monmdp@db:5432/bourse'  # inside docker
# DATABASE_URI = 'timescaledb://ricou:monmdp@localhost:5432/bourse'  # outisde docker
engine = sqlalchemy.create_engine(DATABASE_URI)

df_companies = pd.DataFrame()
df_daystocks = pd.DataFrame()
# df_stocks = pd.DataFrame()

with engine.connect() as connection:
    df_companies = pd.read_sql('SELECT * FROM companies;', connection)
    df_daystocks = pd.read_sql('SELECT * FROM daystocks;', connection)
    # df_stocks = pd.read_sql('SELECT * FROM stocks;', connection)

df_companies = df_companies[['id', 'name', 'mid', 'symbol']].copy()
df_daystocks.rename(columns={"cid": "id", "date": "date_daystocks", "volume": "volume_daystocks"}, inplace=True)
# df_stocks.rename(columns={"cid": "id", "date": "date_stocks", "volume": "volume_stocks"}, inplace=True)
df_daystocks.sort_values(by='date_daystocks', inplace=True)
warning("test")
# df_stocks.sort_values(by='date_stocks', inplace=True)

ext = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, title="Bourse", suppress_callback_exceptions=True, external_stylesheets=ext)
server = app.server

# * -={#|#}=- * -={#|#}=- * -={#|#}=- * COMPONENTS * -={#|#}=- * -={#|#}=- * -={#|#}=- * #

# Colors
colors = {
    'background': '#FFF4F2',
    'text': '#333333',
    'accent': '#FFC0CB',
    'border': '#DDDDDD'
}

# Selectors
stock_selector = html.Div(children=[
    html.Label('Select stocks:', style={'font-weight': 'bold', 'color': colors['text']}),
    dcc.Dropdown(
        id='stock-selector',
        options=[{'label': row['symbol'], 'value': row['symbol']} for index, row in df_companies.iterrows()],
        value=[df_companies.iloc[0]['symbol']],
        multi=True,
        style={'width': '100%', 'background-color': colors['accent'],
               'box-shadow': '0px 0px 10px rgba(0, 0, 0, 0.1)', 'color': colors['text']},
    )
], style={'width': '45%'})

graph_selector = html.Div(children=[
    dcc.Dropdown(
        id='visualization-type',
        options=[
            {'label': 'Lines', 'value': 'lines'},
            {'label': 'Candlesticks', 'value': 'candlesticks'}
        ],
        value='lines',  # valeur par défaut
        style={'background-color': colors['accent'], 'color': colors['text']}
    )
])

# Switches
bollinger_switch = html.Div(children=[
    dcc.Checklist(
        id='bollinger-switch',
        options=[
            {'label': 'Show Bollinger Bands', 'value': 'bollinger'}
        ],
        value=[],
        style={'margin-top': '10px', 'color': colors['text']}
    )
])

trix_indicator_switch = html.Div(children=[
    dcc.Checklist(
        id='trix-indicator-switch',
        options=[
            {'label': 'Show TRIX Indicator', 'value': 'trix'}
        ],
        value=[],
        style={'margin-top': '10px', 'color': colors['text']}
    )
])

# Date picker
date_picker = dcc.DatePickerRange(
    id='date-picker-range',
    min_date_allowed=min(df_daystocks['date_daystocks']),
    max_date_allowed=max(df_daystocks['date_daystocks']),
    start_date=min(df_daystocks['date_daystocks']),
    end_date=max(df_daystocks['date_daystocks']),
    display_format='YYYY-MM-DD',
    style={'width': '100%', 'color': colors['accent']}
)

# Table
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
    style_header={'text-align': 'center', 'background-color': colors['accent']},
)

# * -={#|#}=- * -={#|#}=- * -={#|#}=- * APP LAYOUT * -={#|#}=- * -={#|#}=- * -={#|#}=- * #

app.layout = html.Div(children=[
    # Title
    html.H1("Stock Dashboard", style={'text-align': 'center', 'color': colors['text'], 'margin': '20px',
                                      'font-family': 'Avantgarde, TeX Gyre Adventor, URW Gothic L, sans-serif',
                                      'font-weight': 'bold'}),

    html.Div(children=[
        html.Div(stock_selector, style={'flex': '1'}),
        html.Div(date_picker, style={'flex': '1', 'margin-left': '20px'}),
    ],
        style={'height': '100px', 'display': 'flex', 'justify-content': 'space-between', 'align-items': 'center',
               'padding-left': '30px', 'background-color': colors['background']}),

    # Div Down
    html.Div(
        children=[
            # Div Left (Graph)
            html.Div(
                children=[
                    dcc.Graph(id='stock-graph'),
                ],
                style={'flex': '70%', 'padding': '20px', 'background-color': '#f9f9f9', 'border-radius': '10px',
                       'box-shadow': '0px 0px 20px rgba(0, 0, 0, 0.3)', 'width': '70%', 'margin-right': '10px'}
            ),

            # Div Right (Settings)
            html.Div(
                children=[
                    html.H4("Graph Settings", style={'color': colors['text'],
                                                     'margin-bottom': '10px'}),
                    html.Label("Select visualization type:", style={'font-weight': 'bold', 'color': colors['text']}),
                    graph_selector,
                    bollinger_switch,
                    trix_indicator_switch,
                ],
                style={'flex': '30%', 'padding': '20px', 'background-color': colors['background'],
                       'border-radius': '10px',
                       'box-shadow': '0px 0px 20px rgba(0, 0, 0, 0.3)', 'width': '30%', 'margin-left': '10px'}
            ),
        ],
        style={'display': 'flex', 'justify-content': 'space-between', 'align-items': 'stretch',
               'margin': '20px', 'background-color': colors['background'], 'padding': '20px'}
    ),

    # Div Table
    html.Div(
        children=[
            html.Label("Info on selected stocks", style={'fontWeight': 'bold', 'color': colors['text']}),
            stock_info_table,
        ],
        style={'margin': '30px', 'padding': '30px', 'background-color': colors['background'], 'border-radius': '10px',
               'box-shadow': '0px 0px 20px rgba(0, 0, 0, 0.3)'}
    )
],
    style={'background-color': colors['background'], 'font-family': 'Arial, sans-serif', 'color': colors['text'],
           'border-radius': '15px', 'box-shadow': '0px 0px 20px rgba(0, 0, 0, 0.3)', 'margin': '20px',
           'padding': '20px'}
)


# * -={#|#}=- * -={#|#}=- * -={#|#}=- * CALLBACKS * -={#|#}=- * -={#|#}=- * -={#|#}=- * #

@callback(
    Output('stock-graph', 'figure'),
    Output('stock-table', 'data'),
    Input('stock-selector', 'value'),
    Input('visualization-type', 'value'),
    Input('bollinger-switch', 'value'),
    Input('trix-indicator-switch', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date')
)
def update_graph(selected_stocks, visualization_type, bollinger_switch_value, trix_switch_value, start_date, end_date):
    traces = []
    data = []
    selected_stock_ids = [df_companies[df_companies['symbol'] == stock]['id'].iloc[0] for stock in selected_stocks]
    with engine.connect() as connection2:
        stock_condition = f"cid IN ({','.join(map(str, selected_stock_ids))})"
        query = f"SELECT * FROM stocks WHERE {stock_condition}"
        df_stocks = pd.read_sql(query, connection2)
        df_stocks.rename(columns={"cid": "id", "date": "date_stocks", "volume": "volume_stocks"}, inplace=True)
        df_stocks.sort_values(by='date_stocks', inplace=True)

    filtered_daystocks = df_daystocks[
        (df_daystocks['date_daystocks'] >= start_date) & (df_daystocks['date_daystocks'] <= end_date)]
    for current_stock_symbol in selected_stocks:
        current_stock_id = df_companies[df_companies['symbol'] == current_stock_symbol]['id'].iloc[0]
        if visualization_type == 'lines':
            filtered_dates = filtered_daystocks['date_daystocks'].dt.date
            stock_data = df_stocks[(df_stocks['id'] == current_stock_id) &
                                   (df_stocks['date_stocks'].dt.date.isin(filtered_dates))]
            traces.append(go.Scatter(x=stock_data['date_stocks'],
                                     y=stock_data['value'],
                                     mode='lines',
                                     name=current_stock_symbol))

        elif visualization_type == 'candlesticks':
            stock_data = filtered_daystocks[filtered_daystocks['id'] == current_stock_id]
            traces.append(go.Candlestick(x=stock_data['date_daystocks'],
                                         open=stock_data['open'],
                                         high=stock_data['high'],
                                         low=stock_data['low'],
                                         close=stock_data['close'],
                                         name=current_stock_symbol))

        # Bollinger bands
        if 'bollinger' in bollinger_switch_value:
            filtered_dates = filtered_daystocks['date_daystocks'].dt.date
            stock_data = df_stocks[(df_stocks['id'] == current_stock_id) &
                                   (df_stocks['date_stocks'].dt.date.isin(filtered_dates))]
            mean = stock_data['value'].rolling(window=20).mean()
            std = stock_data['value'].rolling(window=20).std()

            upper_band = mean + (2 * std)
            lower_band = mean - (2 * std)

            # Trace Bollinger bands
            traces.append(go.Scatter(x=stock_data['date_stocks'],
                                     y=upper_band,
                                     mode='lines',
                                     name=f'{current_stock_symbol} Bollinger\'s Upper Band',
                                     line=dict(color='blue', dash='dash')))
            traces.append(go.Scatter(x=stock_data['date_stocks'],
                                     y=mean,
                                     mode='lines',
                                     name=f'{current_stock_symbol} Bollinger\'s Central Band',
                                     line=dict(color='black', dash='dash')))
            traces.append(go.Scatter(x=stock_data['date_stocks'],
                                     y=lower_band,
                                     mode='lines',
                                     name=f'{current_stock_symbol} Bollinger\'s Lower Band',
                                     line=dict(color='red', dash='dash')))
            # Fill space between upper and lower bands
            traces.append(go.Scatter(x=stock_data['date_stocks'],
                                     y=upper_band,
                                     mode='lines',
                                     line=dict(color='rgba(0,0,255,0)'),
                                     showlegend=False))
            traces.append(go.Scatter(x=stock_data['date_stocks'],
                                     y=lower_band,
                                     mode='lines',
                                     fill='tonexty',
                                     fillcolor='rgba(0,0,255,0.1)',
                                     line=dict(color='rgba(0,0,255,0)'),
                                     name=f'{current_stock_symbol} Bollinger\'s Band Area'))

        # TRIX indicator
        if 'trix' in trix_switch_value:
            trix_data = filtered_daystocks.copy()
            trix_data[f'{current_stock_symbol}.TRIX'] = calculate_trix(trix_data, current_stock_symbol, 14,
                                                                       df_companies)

            traces.append(go.Scatter(x=trix_data['date_daystocks'],
                                     y=trix_data[f'{current_stock_symbol}.TRIX'],
                                     mode='lines',
                                     line=dict(color='green', dash='dot'),
                                     name=f'{current_stock_symbol} TRIX'))

    layout = go.Layout(title='Stock Prices', xaxis=dict(title='Date'), yaxis=dict(title='Price', type='log'))

    # Grouped data for table
    grouped_data = df_daystocks.groupby(pd.Grouper(key='date_daystocks', freq='d'))
    for date, group_data in grouped_data:
        if pd.Timestamp(start_date).day <= date.day <= pd.Timestamp(end_date).day:
            date_string = date.day
            filtered_stocks = df_stocks[df_stocks['date_stocks'].dt.day == date_string]
            merged_data = pd.merge(group_data, filtered_stocks, on='id')
            row_data = {
                'date-column': date_string,
                'min-column': merged_data['low'].min(),
                'max-column': merged_data['high'].max(),
                'start-column': merged_data['open'].iloc[0],
                'end-column': merged_data['close'].iloc[-1],
                'mean-column': merged_data['value'].mean(),
                'std-dev-column': merged_data['value'].std()
            }
            data.append(row_data)

    fig = {'data': traces, 'layout': layout}

    return fig, data


def calculate_trix(data, current_stock, period, company):
    # Exponential Moving Average (EMA) of close prices
    ema_close = data[company['symbol'] == current_stock]['close'].ewm(span=period, min_periods=period).mean()

    # Rate of change of EMA of close prices
    roc_ema_close = ema_close.pct_change()

    # Triple Exponential Moving Average (TRIX)
    trix = roc_ema_close.ewm(span=period, min_periods=period).mean() * 100

    return trix


if __name__ == '__main__':
    app.run(debug=True)
