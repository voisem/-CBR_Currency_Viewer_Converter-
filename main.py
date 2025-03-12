import streamlit as st
import pandas as pd
import requests
from io import StringIO
import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Курсы валют", layout="wide")
st.markdown(
    """
    <style>
        header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

@st.cache_data
def get_currency_data():
    url = 'http://www.cbr.ru/scripts/XML_daily.asp'
    response = requests.get(url)
    df = pd.read_xml(StringIO(response.text), encoding='cp1251')

    df['Value'] = df['Value'].str.replace(',', '.').astype(float)
    df['Rate'] = df['Value'] / df['Nominal'].astype(float)  # Курс с учетом номинала

    return df[['CharCode', 'Nominal', 'Name', 'Rate', 'ID']]


@st.cache_data
def get_currency_history(currency_id, days):
    end_date = datetime.date.today().strftime("%d/%m/%Y")
    start_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%d/%m/%Y")

    url = f'https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={start_date}&date_req2={end_date}&VAL_NM_RQ={currency_id}'
    response = requests.get(url)
    df_hist = pd.read_xml(StringIO(response.text), encoding='cp1251')

    if df_hist is None or df_hist.empty:
        return None

    df_hist['Value'] = df_hist['Value'].str.replace(',', '.').astype(float)
    df_hist['Date'] = pd.to_datetime(df_hist['Date'], format='%d.%m.%Y')

    # Используем Nominal из df
    nominal = df[df["ID"] == currency_id]["Nominal"].values
    if len(nominal) > 0:
        df_hist['Value'] /= nominal[0]

    return df_hist



df = get_currency_data()

if "selected_currency" not in st.session_state:
    st.session_state.selected_currency = df[df["CharCode"] == "USD"].iloc[0].to_dict()

with st.sidebar:
    st.title("Выберите валюту")
    search_query = st.text_input("Поиск валюты")
    filtered_df = df[
        df["CharCode"].str.contains(search_query.upper(), na=False) |
        df["Name"].str.contains(search_query, na=False, case=False)
    ] if search_query else df

    col1, col2 = st.columns([2, 1])
    with col1:
        sort_option = st.selectbox("Сортировка", ["Названию", "Курсу"], label_visibility="collapsed")
    with col2:
        sort_order = st.radio("Порядок", ["⬆", "⬇"], horizontal=True, label_visibility="collapsed")

    ascending = (sort_order == "⬆")
    filtered_df = filtered_df.sort_values("Name" if sort_option == "Названию" else "Rate", ascending=ascending)

    for _, row in filtered_df.iterrows():
        if st.button(f"{row['CharCode']} - {row['Name']}\n{row['Rate']:.3f} ₽", key=row['CharCode'], use_container_width=True):
            st.session_state.selected_currency = row.to_dict()

selected_currency = st.session_state.selected_currency


st.title(f"{selected_currency['Name']} ({selected_currency['CharCode']})")

days = st.slider("Период отображения(в днях)", min_value=7, max_value=360, value=30, step=1)
df_hist = get_currency_history(selected_currency["ID"], days)

if df_hist is not None and not df_hist.empty:
    colors = ["green" if df_hist["Value"].iloc[i] >= df_hist["Value"].iloc[i - 1] else "red" for i in range(1, len(df_hist))]

    fig = go.Figure()

    for i in range(1, len(df_hist)):
        fig.add_trace(go.Scatter(
            x=[df_hist["Date"].iloc[i - 1], df_hist["Date"].iloc[i]],
            y=[df_hist["Value"].iloc[i - 1], df_hist["Value"].iloc[i]],
            mode="lines",
            line=dict(color=colors[i - 1], width=2.5, shape="spline")
        ))

    fig.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        yaxis_title="Курс",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        dragmode=False,
        xaxis=dict(fixedrange=True),
        yaxis=dict(
            fixedrange=True,
            tickformat=".4f",  # Форматирование числа с 4 знаками после запятой
            showgrid=True,  # Включил сетку для наглядности
            zeroline=False  # Убрал нулевую линию, если она была лишней
        )
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

mode = st.radio("Режим конвертации", [ f"RUB → {selected_currency['CharCode']}", f"{selected_currency['CharCode']} → RUB"], horizontal=True)


st.subheader("Конвертер валют")


if mode == f"RUB → {selected_currency['CharCode']}":
    amount = st.number_input(f"RUB в {selected_currency['CharCode']}", min_value=0.0, format="%.2f", step=1.0)
    converted = amount / selected_currency["Rate"]
    st.write(f"**{amount:.2f} RUB = {converted:.2f} {selected_currency['CharCode']}**")
else:
    amount = st.number_input(f"{selected_currency['CharCode']} в RUB", min_value=0.0, format="%.2f", step=1.0)
    converted = amount * selected_currency["Rate"]
    st.write(f"**{amount:.2f} {selected_currency['CharCode']} = {converted:.2f} RUB**")

