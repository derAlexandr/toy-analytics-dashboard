import pandas as pd
import sqlite3
import dash
from dash import dcc, html, Input, Output, State, callback
import plotly.express as px

# --- 1. Создаём базу данных, если её нет ---
def create_database():
    if not pd.io.common.file_exists('toy_store.db'):
        data = pd.DataFrame({
            'date': ['2025-01-01', '2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04',
                     '2025-01-05', '2025-01-05', '2025-01-06', '2025-01-07', '2025-01-07'],
            'product_name': [
                'Конструктор "Робот"', 'Мягкий медведь', 'Набор карандашей', 'Конструктор "Робот"',
                'Пазл "Галактика"', 'Мягкий заяц', 'Конструктор "Космос"', 'Пазл "Динозавры"',
                'Мягкий кот', 'Набор фломастеров'
            ],
            'category': [
                'Конструкторы', 'Мягкие игрушки', 'Канцелярия', 'Конструкторы', 'Пазлы',
                'Мягкие игрушки', 'Конструкторы', 'Пазлы', 'Мягкие игрушки', 'Канцелярия'
            ],
            'quantity': [10, 25, 15, 12, 8, 20, 7, 14, 18, 10],
            'price_per_unit': [1500, 800, 300, 1500, 1200, 750, 1800, 1300, 900, 350],
            'region': [
                'Москва', 'Санкт-Петербург', 'Москва', 'Казань', 'Новосибирск',
                'Екатеринбург', 'Москва', 'Санкт-Петербург', 'Казань', 'Москва'
            ]
        })

        conn = sqlite3.connect('toy_store.db')
        data.to_sql('sales', conn, if_exists='replace', index=False)
        conn.close()
        print("✅ База данных создана: toy_store.db")

# --- 2. Загружаем данные ---
def load_data():
    conn = sqlite3.connect('toy_store.db')
    query = """
        SELECT 
            *,
            quantity * price_per_unit AS revenue
        FROM sales
    """
    df = pd.read_sql(query, conn)
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'].astype(str), errors='coerce')
    conn.close()
    return df

# Создаём базу
create_database()

# Загружаем
df = load_data()

# --- 3. Создаём дашборд ---
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("🎯 Аналитика продаж игрушек", style={'textAlign': 'center', 'color': '#2c3e50'}),

    # Фильтры
    html.Div([
        html.Div([
            html.Label("Категория:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='category-filter',
                options=[{'label': cat, 'value': cat} for cat in df['category'].unique()],
                value=df['category'].tolist(),
                multi=True,
                style={'width': '100%'}
            )
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '0 10px'}),

        html.Div([
            html.Label("Регион:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='region-filter',
                options=[{'label': reg, 'value': reg} for reg in df['region'].unique()],
                value=df['region'].tolist(),
                multi=True,
                style={'width': '100%'}
            )
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '0 10px'})
    ], style={'textAlign': 'center', 'marginBottom': '30px'}),

    # График 1 + кнопка
    html.Div([
        dcc.Graph(id='revenue-by-product'),
        html.Button("📥 Скачать график (PNG)", id="btn-png-1", n_clicks=0),
        dcc.Download(id="download-png-1")
    ], style={'padding': '0 20px'}),

    # График 2 + кнопка
    html.Div([
        dcc.Graph(id='sales-trend'),
        html.Button("📥 Скачать график (PNG)", id="btn-png-2", n_clicks=0),
        dcc.Download(id="download-png-2")
    ], style={'padding': '0 20px'})

], style={'backgroundColor': '#f8f9fa', 'fontFamily': 'Arial, sans-serif'})

# --- Callback'и ---
@app.callback(
    [Output('revenue-by-product', 'figure'),
     Output('sales-trend', 'figure')],
    [Input('category-filter', 'value'),
     Input('region-filter', 'value')]
)
def update_charts(selected_categories, selected_regions):
    if isinstance(selected_categories, str): selected_categories = [selected_categories]
    if isinstance(selected_regions, str): selected_regions = [selected_regions]

    filtered_df = df[
        df['category'].isin(selected_categories) &
        df['region'].isin(selected_regions)
    ]

    revenue_df = filtered_df.groupby('product_name', as_index=False)['revenue'].sum()
    bar_fig = px.bar(revenue_df, x='product_name', y='revenue', title='Выручка по товарам',
                     labels={'revenue': 'Выручка (руб)'}, text='revenue')
    bar_fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    bar_fig.update_layout(xaxis_tickangle=-45)

    trend_df = filtered_df.groupby('date', as_index=False)['quantity'].sum()
    line_fig = px.line(trend_df, x='date', y='quantity', title='Динамика продаж',
                       labels={'quantity': 'Количество'}, markers=True)
    line_fig.update_layout(hovermode='x unified')

    return bar_fig, line_fig

# --- Кнопки экспорта ---
@app.callback(
    Output("download-png-1", "data"),
    Input("btn-png-1", "n_clicks"),
    State("revenue-by-product", "figure"),
    prevent_initial_call=True
)
def download_bar(n_clicks, fig):
    if n_clicks == 0: raise PreventUpdate
    return dcc.send_bytes(px.Figure(fig).to_image(format="png"), "revenue_by_product.png")

@app.callback(
    Output("download-png-2", "data"),
    Input("btn-png-2", "n_clicks"),
    State("sales-trend", "figure"),
    prevent_initial_call=True
)
def download_line(n_clicks, fig):
    if n_clicks == 0: raise PreventUpdate
    return dcc.send_bytes(px.Figure(fig).to_image(format="png"), "sales_trend.png")

# --- Запуск ---
if __name__ == '__main__':
    app.run(debug=True, port=8050)
