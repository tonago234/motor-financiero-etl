import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página web
st.set_page_config(page_title="Mi Motor Financiero", page_icon="💸", layout="wide")

st.title("💸 Dashboard Financiero Personal Histórico")
st.markdown("Análisis inteligente de gastos mensuales acumulados, ajustados por inflación (UVA) y USD Blue.")

# --- CARGA DE DATOS ---
try:
    df = pd.read_csv('tabla_maestra_gastos.csv')
    df['fecha_transaccion'] = pd.to_datetime(df['fecha_transaccion'])
except FileNotFoundError:
    st.error("No se encontró el archivo 'tabla_maestra_gastos.csv'. Ejecutá primero el motor ETL.")
    st.stop()

# --- PROCESAMIENTO TEMPORAL (Magia de Pandas) ---
df['Año'] = df['fecha_transaccion'].dt.year
df['Mes_Num'] = df['fecha_transaccion'].dt.month

meses_es = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
df['Mes_Nombre'] = df['Mes_Num'].map(meses_es)
df['Periodo'] = df['Mes_Nombre'] + " " + df['Año'].astype(str)

# --- 🔮 MÓDULO PREDICTIVO (Cálculo de Promedio Real Intermensual) ---
# 1. Agrupamos por Año y Mes para saber cuánto se gastó EN TOTAL en cada mes (usando pesos ajustados a hoy)
df_totales_por_mes = df.groupby(['Año', 'Mes_Num'])['monto_poder_adquisitivo_hoy'].sum().reset_index()

# 2. Sacamos la media (promedio) de esos totales mensuales
if not df_totales_por_mes.empty:
    promedio_gasto_mensual_real = df_totales_por_mes['monto_poder_adquisitivo_hoy'].mean()
    cantidad_meses_analizados = len(df_totales_por_mes)
else:
    promedio_gasto_mensual_real = 0.0
    cantidad_meses_analizados = 0

# --- FILTRO INTERACTIVO (Barra lateral) ---
periodos_disponibles = df.sort_values('fecha_transaccion', ascending=False)['Periodo'].unique().tolist()
opciones_selector = ["Todos los meses (General)"] + periodos_disponibles

st.sidebar.header("🗓️ Selector de Período")
periodo_seleccionado = st.sidebar.selectbox(
    "Elegí qué mes querés auditar o ver el reporte general:",
    opciones_selector
)

if periodo_seleccionado == "Todos los meses (General)":
    df_filtrado = df.copy()
    titulo_resumen = "Resumen General (Todo el Historial Acumulado)"
else:
    df_filtrado = df[df['Periodo'] == periodo_seleccionado].copy()
    titulo_resumen = f"Resumen General ({periodo_seleccionado})"

# --- MÉTRICAS PRINCIPALES DINÁMICAS ---
st.subheader(titulo_resumen)
col1, col2, col3, col4 = st.columns(4)

total_gastado_nominal = df_filtrado['monto_original_ars'].sum()
total_poder_adquisitivo_hoy = df_filtrado['monto_poder_adquisitivo_hoy'].sum()
total_dolares = df_filtrado['gasto_equivalente_usd'].sum()

col1.metric("Gasto Total (Pesos Nominales)", f"${total_gastado_nominal:,.2f}")
col2.metric("Poder Adquisitivo Actualizado (UVA)", f"${total_poder_adquisitivo_hoy:,.2f}")
col3.metric("Predicción de Gasto próximo mes", f"$ {promedio_gasto_mensual_real:,.2f}")
col4.metric("Equivalente en Dólares (Blue)", f"USD {total_dolares:,.2f}")

st.divider()

# --- SECCIÓN DE GRÁFICOS CONMUTABLES ---
if periodo_seleccionado == "Todos los meses (General)":
    st.subheader("📈 Análisis Evolutivo Intermensual (Comparativa)")
    
    df_mensual = df.groupby(['Año', 'Mes_Num', 'Periodo'])[['gasto_equivalente_usd', 'monto_poder_adquisitivo_hoy']].sum().reset_index()
    df_mensual = df_mensual.sort_values(['Año', 'Mes_Num'])
    
    tab1, tab2 = st.tabs(["📊 Evolución en USD por Mes", "📈 Evolución en Pesos Ajustados por Mes"])
    
    with tab1:
        fig_usd = px.bar(df_mensual, x='Periodo', y='gasto_equivalente_usd', 
                         title="Gasto Total Consolidado por Mes (USD)",
                         labels={'Periodo': 'Mes', 'gasto_equivalente_usd': 'Monto Total (USD)'},
                         color_discrete_sequence=['#2E86C1'])
        st.plotly_chart(fig_usd, use_container_width=True)
        
    with tab2:
        fig_ars = px.line(df_mensual, x='Periodo', y='monto_poder_adquisitivo_hoy', 
                          title="Evolución del Gasto Mensual Ajustado por Inflación (ARS)",
                          labels={'Periodo': 'Mes', 'monto_poder_adquisitivo_hoy': 'Poder Adquisitivo Real (ARS)'},
                          markers=True, color_discrete_sequence=['#28B463'])
        
        # Agregamos una línea punteada horizontal que muestre el promedio para ver visualmente si un mes estuviste por encima o por debajo
        fig_ars.add_hline(y=promedio_gasto_mensual_real, line_dash="dash", line_color="red", 
                          annotation_text=f"Promedio Real Predictivo: ${promedio_gasto_mensual_real:,.0f}", 
                          annotation_position="bottom right")
        
        st.plotly_chart(fig_ars, use_container_width=True)

else:
    st.subheader(f"📊 Comportamiento Diario de Gastos: {periodo_seleccionado}")
    
    df_diario = df_filtrado.groupby('fecha_transaccion')[['gasto_equivalente_usd', 'monto_poder_adquisitivo_hoy']].sum().reset_index()
    df_diario = df_diario.sort_values('fecha_transaccion')
    
    tab1, tab2 = st.tabs(["📊 Distribución Diaria (USD)", "📈 Tendencia Diaria Ajustada (ARS)"])
    
    with tab1:
        fig_diario_usd = px.bar(df_diario, x='fecha_transaccion', y='gasto_equivalente_usd',
                                title=f"Gastos por Día en USD - Período {periodo_seleccionado}",
                                labels={'fecha_transaccion': 'Día del Mes', 'gasto_equivalente_usd': 'Monto (USD)'},
                                color_discrete_sequence=['#34495E'])
        st.plotly_chart(fig_diario_usd, use_container_width=True)
        
    with tab2:
        fig_diario_ars = px.line(df_diario, x='fecha_transaccion', y='monto_poder_adquisitivo_hoy',
                                 title=f"Fluctuación Diaria en Pesos Constantes - Período {periodo_seleccionado}",
                                 labels={'fecha_transaccion': 'Día del Mes', 'monto_poder_adquisitivo_hoy': 'Monto Ajustado (ARS)'},
                                 markers=True, color_discrete_sequence=['#E67E22'])
        st.plotly_chart(fig_diario_ars, use_container_width=True)

# --- TABLA INTERACTIVA DINÁMICA ---
st.divider()
st.subheader(f"📋 Transacciones Filtradas del Período: {periodo_seleccionado}")
columnas_vista = ['id_transaccion', 'fecha_transaccion', 'monto_original_ars', 'cotizacion_usd_dia', 'gasto_equivalente_usd', 'monto_poder_adquisitivo_hoy']

st.dataframe(df_filtrado[columnas_vista].sort_values('fecha_transaccion', ascending=False), use_container_width=True, hide_index=True)