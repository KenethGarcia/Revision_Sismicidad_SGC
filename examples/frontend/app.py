# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# ----------------------------------------------------------------------------------------------------------------------
# This file contains a Streamlit application that allows users to interact with the seismic review routine without
# using the command line. The application provides a user-friendly interface for selecting input files,
# configuring parameters, and visualizing results.
# ----------------------------------------------------------------------------------------------------------------------
import os
import getpass
import pandas as pd
import streamlit as st
from datetime import datetime

# Page config
st.set_page_config(
    page_title="RSNC - Revisión de Sismicidad",
    page_icon="地震",
    layout="wide",
    initial_sidebar_state="expanded"
)

# File for persistent storage of logs
LOG_FILE = "historical_revision_log.csv"

# Helper function
@st.cache_data
def load_mock_data():
    """Generates dummy data to simulate the Runner output."""
    return pd.DataFrame({
        "time_value": ["2026-09-09 06:21:29", "2026-09-09 05:09:53", "2026-09-09 04:17:34", "2026-09-08 23:23:42"],
        "publicID": ["sgc2026abcd", "sgc2026efgh", "sgc2026ijkl", "sgc2026mnop"],
        "text": ["SUNDA STRAIT, INDONESIA", "JAVA, INDONESIA", "ANTOFAGASTA, CHILE", "MARIANA ISLANDS"],
        "magnitude_value": [4.0, 4.3, 4.0, 4.9],
        "event_type": ["earthquake", "earthquake", "earthquake", "earthquake"],
        "creationInfo_author": ["scautoloc", "scanloc", "kgarcia", "scautoloc"],
        "Observations": ["High RMS; Potentially locatable", "High Depth", "Potentially locatable", "High RMS"]
    })

def load_history():
    """Loads the historical review logs."""
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    return pd.DataFrame()


# Sidebar navigation
with st.sidebar:
    # SGC logo placeholder
    st.image("sgc.jpg", width=160)
    st.caption("NAVEGACIÓN")

    view = st.radio(
        "Seleccionar vista",
        ["Revisión Actual", "Historial de Revisiones"],
        label_visibility="collapsed"
    )

    st.divider()
    current_user = getpass.getuser()
    st.caption(f"Usuario actual: {current_user}")

# View 1: Revisión Actual
if view == "Revisión Actual":
    st.title("Rutina de Revisión de Sismicidad")
    st.write("Filtre, ejecute y marque los eventos revisados.")

    # Input section
    with st.container(border=True):
        st.subheader("Parámetros de Búsqueda")

        col1, col2, col3 = st.columns(3)
        with col1:
            revisor_name = st.text_input("Nombre del Revisor", value=current_user)
            author_sel = st.selectbox(
                "Búsqueda por autor",
                ["gerard", "kgarcia", "dcreina", "muruena", "william", "axlopez", "amarin", "hmoreno", "seismo", "sismologo"]
            )
        with col2:
            start_date = st.date_input("Fecha de Inicio *")
            end_date = st.date_input("Fecha de Fin (Opcional)", value=None)
        with col3:
            st.write("Características / Filtros")
            potentially_locatable = st.checkbox("Eventos con 7 o menos fases")
            check_rms = st.checkbox("RMS > 0.5")

        run_btn = st.button("Ejecutar Revisión", type="primary")

    # Main content section
    if run_btn or "df_results" in st.session_state:
        # Simulate running the pipeline and storing results in session state
        if run_btn:
            st.session_state["df_results"] = load_mock_data()
            st.session_state["df_totals"] = load_mock_data()

        # Prep Dataframes and ensure Checkbox column exists
        df = st.session_state["df_results"].copy()
        df_totals = st.session_state["df_totals"].copy()

        # Ensure checkbox column exists
        if "Revisado" not in df.columns:
            df.insert(0, "Revisado", False)
        if "Revisado" not in df_totals.columns:
            df_totals.insert(0, "Revisado", False)

        st.divider()

        # Table 1: Display the results with observations
        st.subheader("Resultados de la Revisión")
        st.write("Marque los eventos que han sido revisados y agregue observaciones si es necesario.")

        # Row limit control
        col_limit, _ = st.columns([1, 10])
        with col_limit:
            row_limit = st.selectbox("Número de filas a mostrar", [10, 20, 50, 100], key="limit_obs")

        # Interactive Data Editor for Observations
        with st.container(border=True):
            edited_df = st.data_editor(
                df.head(row_limit),
                column_config={
                    "Revisado": st.column_config.CheckboxColumn(
                        "Revisado",
                        help="Marque si el evento ha sido revisado."
                    ),
                    "Observations": st.column_config.TextColumn(
                        "Observaciones",
                        help="Agregue cualquier observación relevante sobre el evento."
                    )
                },
                disabled=[col for col in df.columns if col != "Revisado" and col != "Observations"],
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        # Table 2: Display the total results for reference
        st.subheader("Todos los eventos obtenidos")

        col_limit_tot, _ = st.columns([1, 10])
        with col_limit_tot:
            row_limit_tot = st.selectbox("Número de filas a mostrar (Totales)", [10, 20, 50, 100], key="limit_totals")

        with st.container(border=True):
            edited_df_totals = st.data_editor(
                df_totals.head(row_limit_tot),
                column_config={
                    "Revisado": st.column_config.CheckboxColumn(
                        "Revisado",
                        help="Marque si el evento ha sido revisado.",
                        default=False
                    ),
                    "Observations": st.column_config.TextColumn(
                        "Observaciones",
                        help="Agregue cualquier observación relevante sobre el evento."
                    )
                },
                disabled=[col for col in df_totals.columns if col != "Revisado" and col != "Observations"],
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        # Save action button
        col_save, _ = st.columns([1, 2])
        with col_save:
            if st.button("Guardar Eventos Revisados", type="primary", use_container_width=True):
                # Extract checked rows from BOTH tables
                rev1 = edited_df[edited_df["Revisado"] == True].copy()
                rev2 = edited_df_totals[edited_df_totals["Revisado"] == True].copy()

                # Combine them into a single DataFrame
                reviewed = pd.concat([rev1, rev2], ignore_index=True)

                # Drop duplicates (in case the user checked the same event in both tables)
                # Assuming 'publicID' is your unique identifier
                reviewed = reviewed.drop_duplicates(subset=["publicID"])

                if not reviewed.empty:
                    # Add audit columns
                    reviewed["Revisor"] = revisor_name
                    reviewed["Fecha Revisión"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Save to CSV
                    save_header = not os.path.exists(LOG_FILE)
                    reviewed.to_csv(LOG_FILE, mode='a', header=save_header, index=False)

                    st.success(f"¡{len(reviewed)} eventos únicos guardados exitosamente en el historial!")
                else:
                    st.warning("No se ha seleccionado ningún evento en ninguna de las tablas para guardar.")


# VIEW 2: HISTORIAL DE REVISIONES
elif view == "Historial de Revisiones":
    st.title("Historial de Revisiones")
    st.caption("Registro histórico de todos los eventos marcados como revisados.")

    df_hist = load_history()

    if df_hist.empty:
        st.info("No hay registros históricos disponibles aún.")
    else:
        col_limit_hist, _ = st.columns([1, 5])
        with col_limit_hist:
            row_limit_hist = st.selectbox("Mostrar filas", [10, 50, 100, 500], key="limit_hist")

        with st.container(border=True):
            # Display history, making sure newer reviews are at the top (sorting by date descending)
            st.dataframe(
                df_hist.sort_values(by="Fecha Revisión", ascending=False).head(row_limit_hist),
                use_container_width=True,
                hide_index=True
            )