from joblib import load
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from st_aggrid import AgGrid, GridOptionsBuilder

# Inicializar valores predeterminados del formulario en session_state
if 'cliente' not in st.session_state:
    st.session_state['cliente'] = ""
if 'ingreso' not in st.session_state:
    st.session_state['ingreso'] = 0.0
if 'deduccion' not in st.session_state:
    st.session_state['deduccion'] = 0.0
if 'activo' not in st.session_state:
    st.session_state['activo'] = 0.0
if 'categoria' not in st.session_state:
    st.session_state['categoria'] = "Autónomo"
if 'tipos_impuestos' not in st.session_state:
    st.session_state['tipos_impuestos'] = ["IVA"]
if 'tipos_deducciones' not in st.session_state:
    st.session_state['tipos_deducciones'] = ["Aportes Seguridad Social"]
if 'tipos_ingresos' not in st.session_state:
    st.session_state['tipos_ingresos'] = ["Alquileres"]
if 'reset_form' not in st.session_state:
    st.session_state['reset_form'] = False

# Cargar el modelo entrenado
try:
    modelo = load("modelo_predictivo.joblib")
    st.sidebar.success("Modelo cargado correctamente.")
except Exception as e:
    st.sidebar.error(f"Error al cargar el modelo: {e}")

# Variables finales después de las transformaciones
feature_names = [
    "tipo_cliente_Autónomo", "tipo_cliente_Empresa", "tipo_cliente_Persona Física",
    "tipo_impuesto_IVA", "tipo_impuesto_Impuesto a las Ganancias", "tipo_impuesto_Ingresos Brutos",
    "tipo_impuesto_Monotributo", "tipo_deduccion_Aportes Seguridad Social",
    "tipo_deduccion_Gastos Deducibles", "tipo_deduccion_Gastos Médicos",
    "tipo_deduccion_Inversiones", "tipo_ingreso_Alquileres", "tipo_ingreso_Inversiones",
    "tipo_ingreso_Prestación de Servicios", "tipo_ingreso_Venta de Bienes",
    "monto_ingreso", "monto_deduccion", "valor_activo", "deduccion_ingresos_ratio",
    "activo_ingreso_ratio"
]

# Inicializar el DataFrame en session_state si no existe
if 'dashboard_df' not in st.session_state:
    st.session_state['dashboard_df'] = pd.DataFrame({
        'Cliente': [],
        'Proyeccion_Obligacion': [],
        'Ingreso': [],
        'Deduccion': [],
        'Activo': [],
        'Categoria': [],
        'Tipos_Impuestos': [],
        'Tipos_Deducciones': [],
        'Tipos_Ingresos': []
    })

# Botón para limpiar el formulario
if st.sidebar.button("Limpiar Formulario"):
    st.session_state['reset_form'] = True
    st.sidebar.success("Formulario reiniciado dinámicamente.")

# Restablecer los valores del formulario si se activó el reinicio
if st.session_state['reset_form']:
    st.session_state['cliente'] = ""
    st.session_state['ingreso'] = 0.0
    st.session_state['deduccion'] = 0.0
    st.session_state['activo'] = 0.0
    st.session_state['categoria'] = "Autónomo"
    st.session_state['tipos_impuestos'] = ["IVA"]
    st.session_state['tipos_deducciones'] = ["Aportes Seguridad Social"]
    st.session_state['tipos_ingresos'] = ["Alquileres"]
    st.session_state['reset_form'] = False

# Umbral de alerta definido por el usuario
st.sidebar.subheader("Configuración de Alertas")
umbral_proyeccion = st.sidebar.number_input(
    "Umbral para Proyecciones ($)", min_value=0.0, value=100000.0, step=5000.0
)

# Función para procesar el archivo Excel cargado
def procesar_excel(archivo):
    try:
        # Leer el archivo Excel
        data = pd.read_excel(archivo)
        
        # Verificar que tenga las columnas necesarias
        columnas_necesarias = ["Cliente", "Ingreso", "Deduccion", "Activo", "Categoria", "Tipos_Impuestos", "Tipos_Deducciones", "Tipos_Ingresos"]
        for columna in columnas_necesarias:
            if columna not in data.columns:
                st.error(f"Falta la columna '{columna}' en el archivo cargado.")
                return
        
        # Procesar cada cliente
        nuevos_clientes = []
        for _, fila in data.iterrows():
            # Crear el DataFrame para el modelo
            cliente_features = pd.DataFrame(0, index=[0], columns=feature_names)
            cliente_features["monto_ingreso"] = fila["Ingreso"]
            cliente_features["monto_deduccion"] = fila["Deduccion"]
            cliente_features["valor_activo"] = fila["Activo"]
            cliente_features["deduccion_ingresos_ratio"] = fila["Deduccion"] / fila["Ingreso"] if fila["Ingreso"] != 0 else 0
            cliente_features["activo_ingreso_ratio"] = fila["Activo"] / fila["Ingreso"] if fila["Ingreso"] != 0 else 0
            cliente_features[f"tipo_cliente_{fila['Categoria']}"] = 1
            
            # Marcar columnas para múltiples selecciones
            for impuesto in fila["Tipos_Impuestos"].split(","):
                cliente_features[f"tipo_impuesto_{impuesto.strip()}"] = 1
            for deduccion in fila["Tipos_Deducciones"].split(","):
                cliente_features[f"tipo_deduccion_{deduccion.strip()}"] = 1
            for ingreso_tipo in fila["Tipos_Ingresos"].split(","):
                cliente_features[f"tipo_ingreso_{ingreso_tipo.strip()}"] = 1
            
            # Hacer la predicción
            proyeccion = modelo.predict(cliente_features)[0]
            
            # Agregar a la lista de nuevos clientes
            nuevos_clientes.append({
                "Cliente": fila["Cliente"],
                "Proyeccion_Obligacion": round(proyeccion, 2),
                "Ingreso": fila["Ingreso"],
                "Deduccion": fila["Deduccion"],
                "Activo": fila["Activo"],
                "Categoria": fila["Categoria"],
                "Tipos_Impuestos": fila["Tipos_Impuestos"],
                "Tipos_Deducciones": fila["Tipos_Deducciones"],
                "Tipos_Ingresos": fila["Tipos_Ingresos"]
            })
        
        # Crear DataFrame para nuevos clientes
        nuevos_df = pd.DataFrame(nuevos_clientes)
        
        # Evitar duplicados combinando con los existentes
        st.session_state['dashboard_df'] = pd.concat(
            [st.session_state['dashboard_df'], nuevos_df]
        ).drop_duplicates(subset=["Cliente"], ignore_index=True)

        st.success("Archivo procesado exitosamente. Los clientes se han agregado al dashboard.")
    
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

# Sección para cargar el archivo Excel
st.sidebar.subheader("Cargar Clientes desde Excel")
archivo_excel = st.sidebar.file_uploader("Sube un archivo Excel con los datos de los clientes", type=["xlsx"])

if archivo_excel:
    procesar_excel(archivo_excel)

# Formulario para agregar clientes
st.sidebar.subheader("Agregar Cliente Manualmente")
with st.sidebar.form("formulario_cliente"):
    cliente = st.text_input("Nombre del Cliente", key="cliente")
    ingreso = st.number_input("Ingreso Anual ($)", min_value=0.0, key="ingreso")
    deduccion = st.number_input("Deducción Anual ($)", min_value=0.0, key="deduccion")
    activo = st.number_input("Valor del Activo ($)", min_value=0.0, key="activo")
    categoria = st.selectbox("Categoría", ["Autónomo", "Empresa", "Persona Física"], key="categoria")
    tipos_impuestos = st.multiselect(
        "Tipos de Impuestos",
        ["IVA", "Impuesto a las Ganancias", "Ingresos Brutos", "Monotributo"],
        default=st.session_state['tipos_impuestos']
    )
    tipos_deducciones = st.multiselect(
        "Tipos de Deducciones",
        ["Aportes Seguridad Social", "Gastos Deducibles", "Gastos Médicos", "Inversiones"],
        default=st.session_state['tipos_deducciones']
    )
    tipos_ingresos = st.multiselect(
        "Tipos de Ingresos",
        ["Alquileres", "Inversiones", "Prestación de Servicios", "Venta de Bienes"],
        default=st.session_state['tipos_ingresos']
    )
    calcular = st.form_submit_button("Calcular Proyección")

    if calcular:
        nuevo_cliente_features = pd.DataFrame(0, index=[0], columns=feature_names)
        nuevo_cliente_features["monto_ingreso"] = ingreso
        nuevo_cliente_features["monto_deduccion"] = deduccion
        nuevo_cliente_features["valor_activo"] = activo
        nuevo_cliente_features["deduccion_ingresos_ratio"] = deduccion / ingreso if ingreso != 0 else 0
        nuevo_cliente_features["activo_ingreso_ratio"] = activo / ingreso if ingreso != 0 else 0
        nuevo_cliente_features[f"tipo_cliente_{categoria}"] = 1

        # Marcar columnas para múltiples selecciones
        for impuesto in tipos_impuestos:
            nuevo_cliente_features[f"tipo_impuesto_{impuesto}"] = 1
        for deduccion in tipos_deducciones:
            nuevo_cliente_features[f"tipo_deduccion_{deduccion}"] = 1
        for ingreso_tipo in tipos_ingresos:
            nuevo_cliente_features[f"tipo_ingreso_{ingreso_tipo}"] = 1

        try:
            proyeccion = modelo.predict(nuevo_cliente_features)[0]
            st.success(f"La proyección de obligación para '{cliente}' es de ${proyeccion:.2f}")

            nuevo_cliente = pd.DataFrame({
                "Cliente": [cliente],
                "Proyeccion_Obligacion": [round(proyeccion, 2)],
                "Ingreso": [ingreso],
                "Deduccion": [deduccion],
                "Activo": [activo],
                "Categoria": [categoria],
                "Tipos_Impuestos": [", ".join(tipos_impuestos)],
                "Tipos_Deducciones": [", ".join(tipos_deducciones)],
                "Tipos_Ingresos": [", ".join(tipos_ingresos)]
            })

            st.session_state['dashboard_df'] = pd.concat(
                [st.session_state['dashboard_df'], nuevo_cliente]
            ).drop_duplicates(subset=["Cliente"], ignore_index=True)

            # Generar alerta si la proyección excede el umbral
            if proyeccion > umbral_proyeccion:
                st.warning(f"¡Alerta! La proyección de '{cliente}' supera el umbral definido (${umbral_proyeccion:.2f}).")

        except Exception as e:
            st.error(f"Error al calcular la proyección: {e}")

# Mostrar la tabla actualizada en el panel principal con AgGrid
st.subheader("Datos de Clientes y Proyecciones")

gb = GridOptionsBuilder.from_dataframe(st.session_state['dashboard_df'])
gb.configure_auto_height(True)
gb.configure_column("Cliente", wrapText=True, autoHeight=True)
grid_options = gb.build()

AgGrid(
    st.session_state['dashboard_df'],
    gridOptions=grid_options,
    height=400,
    fit_columns_on_grid_load=True,
)

# Gráficos interactivos
if not st.session_state['dashboard_df'].empty:
    st.subheader("Gráficos Interactivos")

   # Gráfico de Distribución de Obligaciones Fiscales
if not st.session_state['dashboard_df'].empty:
    st.subheader("Distribución de Obligaciones Fiscales")
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.histplot(st.session_state['dashboard_df']["Proyeccion_Obligacion"], bins=10, kde=True, ax=ax)
    ax.set_title("Distribución de Obligaciones Fiscales", fontsize=10)
    ax.set_xlabel("Monto Proyectado ($)", fontsize=8)
    ax.set_ylabel("Frecuencia", fontsize=8)
    st.pyplot(fig)
else:
    st.info("No hay datos para mostrar el gráfico de distribución.")

# Gráfico de Promedio de Obligaciones por Categoría
if not st.session_state['dashboard_df'].empty:
    st.subheader("Promedio de Obligaciones por Categoría")
    category_avg = st.session_state['dashboard_df'].groupby("Categoria")["Proyeccion_Obligacion"].mean()
    if not category_avg.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        category_avg.plot(kind="bar", color="skyblue", ax=ax)
        ax.set_title("Promedio de Obligaciones por Categoría", fontsize=10)
        ax.set_xlabel("Categoría", fontsize=8)
        ax.set_ylabel("Monto Promedio Proyectado ($)", fontsize=8)
        st.pyplot(fig)
    else:
        st.info("No hay datos disponibles para mostrar el promedio por categoría.")
else:
    st.info("No hay datos para mostrar el gráfico de promedio por categoría.")

# Gráfico de Proyecciones por Tipo de Impuesto
if not st.session_state['dashboard_df'].empty:
    st.subheader("Distribución de Proyecciones por Tipo de Impuesto")
    if "Tipos_Impuestos" in st.session_state['dashboard_df'].columns:
        expanded_tipos_impuestos = st.session_state['dashboard_df'].explode("Tipos_Impuestos")
        impuestos_avg = expanded_tipos_impuestos.groupby("Tipos_Impuestos")["Proyeccion_Obligacion"].mean()
        if not impuestos_avg.empty:
            fig, ax = plt.subplots(figsize=(6, 4))
            impuestos_avg.plot(kind="bar", color="coral", ax=ax)
            ax.set_title("Promedio de Proyecciones por Tipo de Impuesto", fontsize=10)
            ax.set_xlabel("Tipo de Impuesto", fontsize=8)
            ax.set_ylabel("Monto Promedio Proyectado ($)", fontsize=8)
            st.pyplot(fig)
        else:
            st.info("No hay datos disponibles para mostrar las proyecciones por tipo de impuesto.")
    else:
        st.info("No hay datos en la columna 'Tipos_Impuestos' para procesar el gráfico.")
else:
    st.info("No hay datos para mostrar el gráfico de proyecciones por tipo de impuesto.")
