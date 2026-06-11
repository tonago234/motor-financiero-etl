import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Mi Motor Financiero", page_icon="💸", layout="wide")

st.title("💸 Dashboard Financiero Personal")
st.markdown("Análisis histórico de gastos ajustados por inflación y cotización USD.")

# --- CARGA DE DATOS ---
try:
    df = pd.read_csv('tabla_maestra_gastos.csv')
    df['fecha_transaccion'] = pd.to_datetime(df['fecha_transaccion'])
except FileNotFoundError:
    st.error("No se encontró el archivo 'tabla_maestra_gastos.csv'. Ejecutá primero el motor ETL.")
    st.stop()

# --- MÉTRICAS PRINCIPALES ---
st.subheader("Resumen General (Histórico)")
col1, col2, col3 = st.columns(3)

total_gastado_historico = df['monto_original_ars'].sum()
total_poder_adquisitivo_hoy = df['monto_poder_adquisitivo_hoy'].sum()
total_dolares = df['gasto_equivalente_usd'].sum()

col1.metric("Gasto Total (Pesos Nominales)", f"${total_gastado_historico:,.2f}")
col2.metric("Poder Adquisitivo Actualizado (UVA)", f"${total_poder_adquisitivo_hoy:,.2f}")
col3.metric("Equivalente en Dólares (Blue)", f"USD {total_dolares:,.2f}")

st.divider()

# --- GRÁFICOS ---
st.subheader("Evolución del Gasto en el Tiempo")

# Agrupamos por fecha para no tener múltiples barras el mismo día
df_tiempo = df.groupby('fecha_transaccion')[['gasto_equivalente_usd', 'monto_poder_adquisitivo_hoy']].sum().reset_index()

tab1, tab2 = st.tabs(["📊 Ver en Dólares", "📈 Ver en Pesos Ajustados (UVA)"])

with tab1:
    fig_usd = px.bar(df_tiempo, x='fecha_transaccion', y='gasto_equivalente_usd', 
                     title="Gasto Diario en Dólares",
                     labels={'fecha_transaccion': 'Fecha', 'gasto_equivalente_usd': 'Monto (USD)'},
                     color_discrete_sequence=['#2E86C1'])
    st.plotly_chart(fig_usd, use_container_width=True)

with tab2:
    fig_ars = px.line(df_tiempo, x='fecha_transaccion', y='monto_poder_adquisitivo_hoy', 
                      title="Gasto Diario en Pesos (Ajustado a Hoy)",
                      labels={'fecha_transaccion': 'Fecha', 'monto_poder_adquisitivo_hoy': 'Monto Ajustado (ARS)'},
                      markers=True, color_discrete_sequence=['#28B463'])
    st.plotly_chart(fig_ars, use_container_width=True)

# --- TABLA INTERACTIVA ---
st.divider()
st.subheader("Registro Detallado de Transacciones")
st.dataframe(df, use_container_width=True, hide_index=True)