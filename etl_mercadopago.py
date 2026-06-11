import os
import requests
import pandas as pd
from datetime import datetime

def enriquecer_con_dolar(df_gastos):
    print("🌐 Consumiendo API Dólar Histórico...")
    url = "https://api.argentinadatos.com/v1/cotizaciones/dolares/blue"
    respuesta = requests.get(url)
    respuesta.raise_for_status()
    
    df_dolar = pd.DataFrame(respuesta.json())[['fecha', 'venta']].rename(columns={'venta': 'cotizacion_usd_dia'})
    df_gastos['fecha_transaccion'] = pd.to_datetime(df_gastos['fecha_transaccion']).astype('datetime64[ns]')
    df_dolar['fecha'] = pd.to_datetime(df_dolar['fecha']).astype('datetime64[ns]')
    
    df_gastos = df_gastos.sort_values('fecha_transaccion')
    df_dolar = df_dolar.sort_values('fecha')
    
    df_final = pd.merge_asof(df_gastos, df_dolar, left_on='fecha_transaccion', right_on='fecha', direction='backward')
    df_final['gasto_equivalente_usd'] = round(df_final['monto_original_ars'] / df_final['cotizacion_usd_dia'], 2)
    return df_final.drop(columns=['fecha'])

def enriquecer_con_inflacion(df_gastos):
    print("📈 Consumiendo API Índice UVA (Inflación)...")
    url = "https://api.argentinadatos.com/v1/finanzas/indices/uva"
    respuesta = requests.get(url)
    respuesta.raise_for_status()
    
    df_uva = pd.DataFrame(respuesta.json())
    df_uva['fecha'] = pd.to_datetime(df_uva['fecha']).astype('datetime64[ns]')
    df_uva = df_uva.sort_values('fecha')
    
    uva_hoy = df_uva.iloc[-1]['valor']
    
    df_final = pd.merge_asof(
        df_gastos, 
        df_uva[['fecha', 'valor']], 
        left_on='fecha_transaccion', 
        right_on='fecha', 
        direction='backward'
    )
    
    df_final = df_final.rename(columns={'valor': 'indice_uva_dia_compra'})
    df_final['monto_poder_adquisitivo_hoy'] = round(df_final['monto_original_ars'] * (uva_hoy / df_final['indice_uva_dia_compra']), 2)
    
    return df_final.drop(columns=['fecha', 'indice_uva_dia_compra']).sort_values('fecha_transaccion', ascending=False)

def cargar_reporte_mp(ruta_archivo):
    print(f"📥 Extrayendo datos locales de: {ruta_archivo}")
    
    # Leemos el archivo respetando el separador de punto y coma
    df_crudo = pd.read_csv(ruta_archivo, sep=';', encoding='utf-8-sig') 

    # Mapeo de columnas (Eliminamos el Concepto y Agregamos el ID único)
    COL_ID = 'SOURCE_ID'
    COL_FECHA = 'TRANSACTION_DATE'          
    COL_MONTO = 'TRANSACTION_AMOUNT'          
    
    # Renombramos
    df = df_crudo.rename(columns={
        COL_ID: 'id_transaccion',
        COL_FECHA: 'fecha_transaccion',
        COL_MONTO: 'monto_original_ars'
    })
    
    # Limpiamos la fecha
    df['fecha_transaccion'] = pd.to_datetime(df['fecha_transaccion'], utc=True).dt.date
    
    # Convertimos los montos a números
    if df['monto_original_ars'].dtype == object:
        df['monto_original_ars'] = df['monto_original_ars'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
    
    # FILTRO: Solo gastos (salidas de plata)
    df = df[df['monto_original_ars'] < 0].copy()
    
    # Pasamos a positivo
    df['monto_original_ars'] = df['monto_original_ars'].abs()
    
    return df

def main():
    ARCHIVO_REPORTE_MP = "reporte.csv" 
    
    if not os.path.exists(ARCHIVO_REPORTE_MP):
        print(f"❌ No se encontró el archivo '{ARCHIVO_REPORTE_MP}'.")
        return

    print("🚀 Iniciando Motor ETL (Sin Categorías)...")
    
    df_gastos = cargar_reporte_mp(ARCHIVO_REPORTE_MP)
        
    if df_gastos.empty:
        print("⚠️ No se encontraron gastos.")
        return

    # ENRIQUECER (Directo a la matemática)
    df_gastos = enriquecer_con_dolar(df_gastos)
    df_final = enriquecer_con_inflacion(df_gastos)
    
    columnas_ordenadas = [
        'id_transaccion', 'fecha_transaccion', 'monto_original_ars', 
        'cotizacion_usd_dia', 'gasto_equivalente_usd', 'monto_poder_adquisitivo_hoy'
    ]
    df_final = df_final[columnas_ordenadas]

    # CARGAR (GUARDADO HISTÓRICO)
    archivo_maestro = 'tabla_maestra_gastos.csv'
    
    if os.path.exists(archivo_maestro):
        print("\n📚 Archivo histórico encontrado. Uniendo datos...")
        df_historico = pd.read_csv(archivo_maestro)
        
        df_historico['fecha_transaccion'] = pd.to_datetime(df_historico['fecha_transaccion']).dt.date
        df_final['fecha_transaccion'] = pd.to_datetime(df_final['fecha_transaccion']).dt.date
        
        df_completo = pd.concat([df_historico, df_final], ignore_index=True)
        
        # IDEMPOTENCIA PERFECTA: Borramos duplicados basándonos exclusivamente en el ID Único del ticket
        df_completo = df_completo.drop_duplicates(subset=['id_transaccion'], keep='last')
    else:
        print("\n🆕 No hay histórico. Creando nueva base de datos...")
        df_completo = df_final

    df_completo = df_completo.sort_values('fecha_transaccion', ascending=False)
    df_completo.to_csv(archivo_maestro, index=False)
    
    print("\n✅ ¡ETL COMPLETADO! La Tabla Maestra Definitiva:")
    print(df_final.head(10).to_markdown(index=False))
    print(f"\n👉 Base de datos Maestra actualizada: '{archivo_maestro}' (Total histórico: {len(df_completo)} transacciones)")

if __name__ == '__main__':
    main()