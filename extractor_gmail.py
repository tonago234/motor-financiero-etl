import os.path
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def autenticar_gmail():
    """Usa el token guardado para conectarse silenciosamente"""
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    return build('gmail', 'v1', credentials=creds)

def extraer_texto_correo(mensaje_completo):
    """Navega por el correo para encontrar el texto y desencriptarlo de Base64"""
    payload = mensaje_completo.get('payload', {})
    
    # Buscamos en las partes del correo (si es multiparte)
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] in ['text/plain', 'text/html']:
                datos = part['body'].get('data')
                if datos:
                    return base64.urlsafe_b64decode(datos).decode('utf-8')
    else:
        # Si no está dividido en partes
        datos = payload['body'].get('data')
        if datos:
            return base64.urlsafe_b64decode(datos).decode('utf-8')
            
    return "No se pudo extraer el texto."

def main():
    servicio = autenticar_gmail()
    
    # ¡NUEVA QUERY EXACTA!
    query = 'from:info@mercadopago.com subject:"Tu transferencia fue enviada"'
    print(f"Buscando con la query: {query}\n")
    
    resultados = servicio.users().messages().list(userId='me', q=query, maxResults=1).execute()
    mensajes = resultados.get('messages', [])

    if mensajes:
        primer_id = mensajes[0]['id']
        print(f"Abriendo el correo ID: {primer_id}...\n")
        
        mensaje_completo = servicio.users().messages().get(userId='me', id=primer_id, format='full').execute()
        texto_crudo = extraer_texto_correo(mensaje_completo)
        
        print("--- INICIO DEL CUERPO DEL CORREO ---")
        print(texto_crudo)
        print("--- FIN DEL CUERPO DEL CORREO ---")
    else:
        print('No se encontraron correos con este asunto.')

if __name__ == '__main__':
    main()