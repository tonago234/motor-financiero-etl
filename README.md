# Motor Financiero ETL & Dashboard 💸

Un pipeline de datos (End-to-End) diseñado para extraer, transformar, enriquecer y visualizar gastos personales de Mercado Pago, ajustando históricamente los valores por inflación y cotización del dólar libre.

---

## 📌 Descripción del Proyecto

Este proyecto resuelve el problema de la pérdida de referencia de los gastos personales en economías inflacionarias. El sistema procesa reportes financieros, categoriza automáticamente los movimientos y cruza la información con APIs públicas para calcular el equivalente en USD y el poder adquisitivo actual de cada gasto histórico. Finalmente, expone los datos en un Dashboard web interactivo.

---

## 🚀 Arquitectura y Características Principales

* **Procesamiento Batch (Idempotente):** El script lee reportes locales (CSV/Excel), integra solo los datos nuevos a una base histórica y elimina duplicados automáticamente.
* **Enriquecimiento de Datos (APIs):** Integración con la API de *ArgentinaDatos* para obtener la cotización histórica diaria del Dólar Blue y el Índice UVA (Inflación).
* **Transformación y Limpieza:** Uso de `pandas` y Expresiones Regulares (Regex) para estandarizar fechas, limpiar montos y asignar categorías de gasto basadas en diccionarios de reglas.
* **Visualización Web:** Un front-end construido 100% en Python usando `Streamlit` y `Plotly` para gráficos dinámicos y métricas financieras.
* **Automatización:** Configurado para ejecutarse de forma desatendida mediante scripts `.bat` y el Programador de Tareas del sistema operativo.

---

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3.x
* **Manipulación de Datos:** Pandas, Numpy
* **Extracción y APIs:** Requests, Regex (`re`), pdfplumber
* **Front-end / Dashboard:** Streamlit, Plotly
* **Control de Versiones:** Git & GitHub

---

## 📂 Versión Alternativa: Extracción Cloud (Gmail API)

> **Nota para Reclutadores:** La rama `main` actual utiliza un enfoque de procesamiento de archivos locales (CSV) por ser más estable y eficiente a largo plazo. Sin embargo, el proyecto cuenta con una versión inicial que realiza la extracción automática leyendo correos electrónicos directamente desde la bandeja de entrada.
> 
> Pueden revisar el código de integración con **Google Cloud Platform (GCP)**, autenticación **OAuth 2.0** y la **API de Gmail** navegando a los *Tags* del repositorio y seleccionando la versión `v1.0-gmail-api`.

---

## ⚙️ Cómo ejecutar el proyecto localmente

### 1. Clonar el repositorio y preparar el entorno
Cloná este proyecto en tu computadora y creá un entorno virtual aislado para instalar las dependencias:

```bash
git clone [https://github.com/TU_USUARIO/motor-financiero-etl.git](https://github.com/TU_USUARIO/motor-financiero-etl.git)
cd motor-financiero-etl
python -m venv .venv
.venv\Scripts\activate
pip install pandas requests pdfplumber streamlit plotly
```
### 2. Cargar los datos crudos
Descargá tu reporte de movimientos desde la aplicación de Mercado Pago (en formato CSV) y guardalo en la raíz del proyecto con el nombre reporte_mercadopago_abril.csv (o ajustá el nombre en el script etl_mercadopago.py).

### 3. Ejecutar el Pipeline ETL
Corré el motor para que procese los datos, consuma las APIs y genere la base de datos maestra (tabla_maestra_gastos.csv):

```Bash
python etl_mercadopago.py
```

### 4. Levantar el Dashboard
Iniciá el servidor web local para visualizar tus datos enriquecidos y actualizados:

```Bash
streamlit run dashboard.py
```
Autor: Tomás Nahuel Villegas González - [LinkedIn](https://www.linkedin.com/in/tomas-n-villegas-g/)