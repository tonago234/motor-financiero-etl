import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Mi Motor Financiero", page_icon="💸", layout="wide")

st.title("Finanzas Personales vs. Inflación")
st.markdown("Análisis de gastos diarios de Mercado Pago.")

# --- CARGA DE DATOS ---
# Leemos el CSV que generó nuestro motor ETL
try:
    df = pd.read_csv('tabla_maestra_gastos.csv')
    df['fecha_transaccion'] = pd.to_datetime(df['fecha_transaccion'])
except FileNotFoundError:
    st.error("No se encontró el archivo 'tabla_maestra_gastos.csv'. Ejecutá primero el motor ETL.")
    st.stop()

hoy = datetime.now()
mes_reporte = hoy.month

if{mes_reporte} == 1:
    mes_reporte = "Enero"
elif mes_reporte == 2:
    mes_reporte = "Febrero"
elif mes_reporte == 3:
    mes_reporte = "Marzo"
elif mes_reporte == 4:
    mes_reporte = "Abril"
elif mes_reporte == 5:
    mes_reporte = "Mayo"
elif mes_reporte == 6:
    mes_reporte = "Junio"
elif mes_reporte == 7:
    mes_reporte = "Julio"
elif mes_reporte == 8:
    mes_reporte = "Agosto"
elif mes_reporte == 9:
    mes_reporte = "Septiembre"
elif mes_reporte == 10:
    mes_reporte = "Octubre"
elif mes_reporte == 11:
    mes_reporte = "Noviembre"
elif mes_reporte == 12:
    mes_reporte = "Diciembre"

# --- MÉTRICAS PRINCIPALES ---
st.subheader(f"Resumen General ({mes_reporte})")
col1, col2, col3 = st.columns(3)

total_gastado_historico = df['monto_original_ars'].sum()
total_poder_adquisitivo_hoy = df['monto_poder_adquisitivo_hoy'].sum()
total_dolares = df['gasto_equivalente_usd'].sum()

col1.metric("Gasto Total (Nominal)", f"${total_gastado_historico:,.2f}")
col2.metric("Gasto Ajustado a Hoy (Inflación)", f"${total_poder_adquisitivo_hoy:,.2f}")
col3.metric("Equivalente en USD (Blue)", f"USD {total_dolares:,.2f}")

st.divider()

# --- GRÁFICOS ---
col_grafico1, col_grafico2 = st.columns(2)

with col_grafico1:
    st.subheader("Distribución por Categorías")
    # Agrupamos por categoría y sumamos los montos ajustados a hoy
    df_cat = df.groupby('categoria_asignada')['monto_poder_adquisitivo_hoy'].sum().reset_index()
    fig_pie = px.pie(df_cat, values='monto_poder_adquisitivo_hoy', names='categoria_asignada', hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_grafico2:
    st.subheader("Evolución del Gasto en el Tiempo (USD)")
    # Gráfico de barras viendo día a día cuánto se gastó en dólares
    df_tiempo = df.groupby('fecha_transaccion')['gasto_equivalente_usd'].sum().reset_index()
    fig_bar = px.bar(df_tiempo, x='fecha_transaccion', y='gasto_equivalente_usd', 
                     labels={'fecha_transaccion': 'Fecha', 'gasto_equivalente_usd': 'Dólares'})
    st.plotly_chart(fig_bar, use_container_width=True)

# --- TABLA INTERACTIVA ---
st.divider()
st.subheader("Detalle de Transacciones")
# Mostramos la tabla en la web para poder ordenarla por columnas
st.dataframe(df, use_container_width=True)