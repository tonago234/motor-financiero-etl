import os
import io
import re
import base64
import requests
import pandas as pd
import pdfplumber
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def autenticar_gmail():
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    return build('gmail', 'v1', credentials=creds)

def extraer_texto_correo(mensaje_completo):
    payload = mensaje_completo.get('payload', {})
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] in ['text/plain', 'text/html']:
                datos = part['body'].get('data')
                if datos:
                    return base64.urlsafe_b64decode(datos).decode('utf-8')
    else:
        datos = payload['body'].get('data')
        if datos:
            return base64.urlsafe_b64decode(datos).decode('utf-8')
    return ""

def extraer_monto_pdf_carrefour(url_del_pdf):
    """Descarga el PDF de Carrefour en la memoria RAM y extrae el texto (sin guardar archivos)"""
    print(f"📥 Detectado link de Carrefour. Extrayendo PDF en memoria...")
    try:
        respuesta = requests.get(url_del_pdf)
        respuesta.raise_for_status()
        
        with pdfplumber.open(io.BytesIO(respuesta.content)) as pdf:
            primera_pagina = pdf.pages[0]
            texto_pdf = primera_pagina.extract_text()
            
            # Buscamos la palabra TOTAL seguida del signo peso en el PDF
            match = re.search(r'TOTAL:\s*\$\s*([\d\.,]+)', texto_pdf)
            if match:
                # Limpiamos el texto para convertirlo a número matemático
                monto_str = match.group(1).replace('.', '').replace(',', '.')
                return float(monto_str)
    except Exception as e:
        print(f"⚠️ Error procesando el PDF de Carrefour: {e}")
    return 0.0

def parsear_datos(html_crudo):
    # --- INTERCEPTOR DE CARREFOUR ---
    # Si detectamos que es un mail de Carrefour y tiene un link a un PDF
    if 'carrefour' in html_crudo.lower() and '.pdf' in html_crudo.lower():
        # Busca un link que termine en .pdf
        patron_link = r'href="(https://[^"]+\.pdf)"'
        match_link = re.search(patron_link, html_crudo)
        if match_link:
            link_pdf = match_link.group(1)
            monto_pdf = extraer_monto_pdf_carrefour(link_pdf)
            if monto_pdf > 0:
                return monto_pdf, "Carrefour (Extraído de PDF)"

    # --- LÓGICA ESTÁNDAR PARA MERCADO PAGO ---
    patron_monto = r'\$\s*([\d\.]+)'
    patron_nombre = r'Nombre y apellido:\s*<strong>(.*?)<\/strong>'
    
    match_monto = re.search(patron_monto, html_crudo)
    match_nombre = re.search(patron_nombre, html_crudo)
    
    monto_limpio = match_monto.group(1).replace('.', '') if match_monto else "0"
    nombre_limpio = match_nombre.group(1).strip() if match_nombre else "Desconocido"
    
    return float(monto_limpio), nombre_limpio

def categorizar_gastos(df_gastos):
    print("🏷️ Categorizando operaciones...")
    reglas = {
        'Zheng': 'Supermercado',
        'Carrefour': 'Supermercado',
        'BUFET': 'Comida/Salidas',
        'Bull Market': 'Inversiones',
        'TFM': 'Servicios/Proveedores'
    }
    
    def asignar_categoria(concepto):
        for clave, categoria in reglas.items():
            if clave.lower() in str(concepto).lower():
                return categoria
        return 'Transferencia a terceros'
        
    df_gastos['categoria_asignada'] = df_gastos['concepto_original'].apply(asignar_categoria)
    return df_gastos

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

def main():
    # 1. FECHAS DINÁMICAS: Detecta automáticamente el mes en el que estás ejecutando el script
    hoy = datetime.now()
    anio_reporte = hoy.year
    mes_reporte = hoy.month
    
    fecha_inicio = f"{anio_reporte}/{mes_reporte:02d}/01"
    if mes_reporte == 12:
        fecha_fin = f"{anio_reporte + 1}/01/01"
    else:
        fecha_fin = f"{anio_reporte}/{mes_reporte + 1:02d}/01"
        
    print(f"🚀 Iniciando Motor ETL - Reporte Mensual [{mes_reporte:02d}/{anio_reporte}]...")
    servicio = autenticar_gmail()
    
    # Query de Gmail (Si en el futuro recibís facturas de Carrefour en tu mail, 
    # podés ampliar esta query agregando un "OR from:facturacion@carrefour.com.ar")
    query = f'from:info@mercadopago.com subject:"Tu transferencia fue enviada" after:{fecha_inicio} before:{fecha_fin}'
    print(f"Buscando correos con la query: {query}")
    
    resultados = servicio.users().messages().list(userId='me', q=query).execute()
    id_mensajes_completos = resultados.get('messages', [])
    
    # Paginación (maneja más de 100 correos)
    while 'nextPageToken' in resultados:
        token_siguiente_pagina = resultados['nextPageToken']
        resultados = servicio.users().messages().list(userId='me', q=query, pageToken=token_siguiente_pagina).execute()
        id_mensajes_completos.extend(resultados.get('messages', []))
        
    total_comprobantes = len(id_mensajes_completos)
    if total_comprobantes == 0:
        print(f'❌ No se encontraron transferencias en el período {fecha_inicio} al {fecha_fin}.')
        return
        
    print(f'📊 Se encontraron {total_comprobantes} comprobantes. Descargando y transformando...')

    gastos_extraidos = []

    for msg in id_mensajes_completos:
        meta = servicio.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Date']).execute()
        headers = meta.get('payload', {}).get('headers', [])
        fecha_cruda = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        
        mensaje_completo = servicio.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        html_crudo = extraer_texto_correo(mensaje_completo)
        
        # Acá adentro corre el interceptor de PDFs si aplica, o el parser de Mercado Pago
        monto, nombre = parsear_datos(html_crudo)
        
        gastos_extraidos.append({
            'fecha_transaccion': fecha_cruda,
            'concepto_original': nombre,
            'monto_original_ars': monto
        })

    df_gastos = pd.DataFrame(gastos_extraidos)
    df_gastos['fecha_transaccion'] = pd.to_datetime(df_gastos['fecha_transaccion'], utc=True).dt.tz_convert('America/Argentina/Buenos_Aires').dt.date

    # --- PIPELINE DE TRANSFORMACIÓN ---
    df_gastos = categorizar_gastos(df_gastos)
    df_gastos = enriquecer_con_dolar(df_gastos)
    df_final = enriquecer_con_inflacion(df_gastos)
    
    columnas_ordenadas = [
        'fecha_transaccion', 'concepto_original', 'categoria_asignada', 
        'monto_original_ars', 'cotizacion_usd_dia', 'gasto_equivalente_usd', 
        'monto_poder_adquisitivo_hoy'
    ]
    df_final = df_final[columnas_ordenadas]

    # --- 3. GUARDADO HISTÓRICO E IDEMPOTENCIA ---
    archivo_maestro = 'tabla_maestra_gastos.csv'
    
    if os.path.exists(archivo_maestro):
        print("\n📚 Archivo histórico encontrado. Uniendo datos y eliminando duplicados...")
        df_historico = pd.read_csv(archivo_maestro)
        
        # Estandarizamos fechas antes de mezclar para evitar falsos duplicados
        df_historico['fecha_transaccion'] = pd.to_datetime(df_historico['fecha_transaccion']).dt.date
        df_final['fecha_transaccion'] = pd.to_datetime(df_final['fecha_transaccion']).dt.date
        
        # Unimos lo viejo con lo nuevo
        df_completo = pd.concat([df_historico, df_final], ignore_index=True)
        
        # MAGIA DE LA IDEMPOTENCIA: Si el gasto ya existía, lo borra y se queda solo con uno.
        df_completo = df_completo.drop_duplicates(
            subset=['fecha_transaccion', 'concepto_original', 'monto_original_ars'],
            keep='last'
        )
    else:
        print("\n🆕 No hay histórico. Creando nueva base de datos...")
        df_completo = df_final

    # Ordenamos de más reciente a más viejo y guardamos la base maestra
    df_completo = df_completo.sort_values('fecha_transaccion', ascending=False)
    df_completo.to_csv(archivo_maestro, index=False)
    
    # (Opcional) Guardamos un backup específico del mes
    nombre_archivo_mensual = f'reporte_gastos_{anio_reporte}_{mes_reporte:02d}.csv'
    df_final.to_csv(nombre_archivo_mensual, index=False)
    
    print(f"\n✅ Pipeline finalizado exitosamente.")
    print(f"👉 Base de datos Maestra actualizada: '{archivo_maestro}' (Total histórico acumulado: {len(df_completo)} transacciones)")

if __name__ == '__main__':
    main()