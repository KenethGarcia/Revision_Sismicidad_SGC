# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# ----------------------------------------------------------------------------------------------------------------------
# This file contains a Streamlit application that allows users to interact with the seismic review routine without
# using the command line. The application provides a user-friendly interface for selecting input files,
# configuring parameters, and visualizing results.
# ----------------------------------------------------------------------------------------------------------------------
import os
import sys
import ftfy
import getpass
import matplotlib
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime
from translations import CHECK_TRANSLATIONS, TEXTS
matplotlib.use('Agg')  # Prevents Matplotlib from initializing GTK/Gdk display backends

# Package path and backend imports
# Dynamically locate the project root directory and add it to sys.path for module imports
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR
while not (ROOT_DIR / "src").exists() and ROOT_DIR != ROOT_DIR.parent:
    ROOT_DIR = ROOT_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.io.sql import load_sql
from src.core.runner import Runner

# Cutoff constant for SC3/SC6 database migration
RSNC_CUTOFF = pd.to_datetime("2026-03-17 00:00:00", utc=True)
# Default configuration file path for the seismic revision routine
DEFAULT_CONFIG = ROOT_DIR / "examples" / "data" / "configs" / "seismic_revision_routine.toml"
# File for persistent storage of logs
LOG_FILE = "historical_revision_log.csv"

# Function to translate the Observations string based on the selected language
def translate_flags(obs_string, lang):
    """Splits, translates, and rejoins the backend Observations string."""
    if pd.isna(obs_string) or lang == "ES":
        return obs_string

    # Split the string by the semicolon separator
    flags = [flag.strip() for flag in str(obs_string).split(";")]

    # Translate each flag using the dictionary.
    # .get(flag, flag) ensures that if a translation is missing, it safely keeps the Spanish text.
    translated = [CHECK_TRANSLATIONS.get(flag, flag) for flag in flags]

    return "; ".join(translated)

# Page config
st.set_page_config(
    page_title="RSNC - Revisión de Sismicidad",
    page_icon="地震",
    layout="wide",
    initial_sidebar_state="expanded"
)


def get_categorized_checks(config_path: Path, lang: str = "ES") -> dict:
    """Dynamically loads and groups all 30 checks from the TOML configuration."""
    runner = Runner(config_path=config_path)
    all_checks = runner._cm.config_data.get("checks", [])

    cats = {
        "ES": {
            "q_unc": "📊 Calidad e Incertidumbre",
            "vel": "🗺️ Modelos de Velocidad",
            "mag": "📈 Magnitudes por Zona",
            "lab": "🏷️ Etiquetas y Comentarios",
            "spec": "⚙️ Reglas Especiales"
        },
        "EN": {
            "q_unc": "📊 Quality & Uncertainty",
            "vel": "🗺️ Velocity Models",
            "mag": "📈 Magnitudes by Zone",
            "lab": "🏷️ Labels & Comments",
            "spec": "⚙️ Special Rules"
        }
    }
    categories = {v: [] for v in cats[lang].values()}

    for check in all_checks:
        name = check.get("name", "")
        if any(k in name for k in ["RMS", "Err", "Depth", "stations", "phases"]):
            categories[cats[lang]["q_unc"]].append(name)
        elif "model" in name or "NLL" in name:
            categories[cats[lang]["vel"]].append(name)
        elif "mag type" in name:
            categories[cats[lang]["mag"]].append(name)
        elif any(k in name for k in ["label", "unassociated", "DESTACADO", "comment"]):
            categories[cats[lang]["lab"]].append(name)
        else:
            categories[cats[lang]["spec"]].append(name)

            # Remove "Potentially locatable event" from special rules if present
            if "Potentially locatable event" in categories[cats[lang]["spec"]]:
                categories[cats[lang]["spec"]].remove("Potentially locatable event")

    return categories


def run_backend_pipeline(
    config_path: Path,
    st_date: datetime | None,
    e_date: datetime | None,
    author: str,
    disabled: list,
    lang: str = "ES"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Executes the backend seismic review pipeline across SeisComP databases,
    applying exact UTC datetime bounds, dynamic check filtering, and text cleanup.
    """
    # 1. Parse exact combined datetimes directly to UTC
    start_dt = pd.to_datetime(st_date, utc=True) if st_date else None
    end_dt = pd.to_datetime(e_date, utc=True) if e_date else None

    # Default end_dt to current UTC time if start_dt is provided without an end_dt
    if start_dt and not end_dt:
        end_dt = pd.Timestamp.utcnow()

    # 2. Determine execution plan across database cutoffs
    execution_plan = []
    if start_dt and end_dt:
        if end_dt <= RSNC_CUTOFF:
            execution_plan.append(("SeisComP3", start_dt, end_dt))
        elif start_dt >= RSNC_CUTOFF:
            execution_plan.append(("SeisComP6", start_dt, end_dt))
        else:
            # Time window spans across both databases[cite: 1]
            execution_plan.append(("SeisComP3", start_dt, RSNC_CUTOFF))
            execution_plan.append(("SeisComP6", RSNC_CUTOFF, end_dt))
    else:
        # Author-only query or unbounded search[cite: 1]
        execution_plan.append(("SeisComP3", None, RSNC_CUTOFF))
        execution_plan.append(("SeisComP6", RSNC_CUTOFF, None))

    # 3. Initialize Runner and retrieve query configuration
    runner = Runner(config_path=config_path)
    time_col = runner._cm.get_time_column()
    available_queries = runner.list_queries()
    frames = []

    # 4. Execute queries across each database leg
    for q_name, q_start, q_end in execution_plan:
        if q_name not in available_queries:
            continue

        sql_params = {}
        where_clauses = []

        if q_start:
            sql_params["start_time"] = q_start.strftime('%Y-%m-%d %H:%M:%S')
            where_clauses.append(f"base_query.{time_col} >= %(start_time)s")
        if q_end:
            sql_params["end_time"] = q_end.strftime('%Y-%m-%d %H:%M:%S')
            where_clauses.append(f"base_query.{time_col} < %(end_time)s")
        if author and author != "Todos":
            sql_params["author_pattern"] = f"%{author}%"
            where_clauses.append("base_query.creationInfo_author LIKE %(author_pattern)s")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Load base SQL text and construct wrapped dynamic query
        query_cfg = runner._cm.select_query(name=q_name)
        base_sql = load_sql(
            query_cfg=query_cfg,
            base_dir=runner._cm.base_dir,
            config_name=runner._cm.config_path.name
        )
        wrapped_sql = f"SELECT * FROM ({base_sql}) AS base_query WHERE {where_sql} ORDER BY base_query.{time_col} ASC"

        res = runner.run(
            query_name=q_name,
            multi_query=False,
            perform_duplicates=False,
            perform_checks=False,
            sql_text_override=wrapped_sql,
            sql_params=sql_params
        )
        frames.append(res.total_events)

    # Return empty DataFrames if no events were returned
    if not frames or sum(len(f) for f in frames) == 0:
        return pd.DataFrame(), pd.DataFrame()

    combined_events = pd.concat(frames, axis=0, ignore_index=True)

    # 5. Dynamically strip out disabled checks prior to running rules engine
    if disabled:
        original_checks = runner._cm.config_data.get("checks", [])
        runner._cm.config_data["checks"] = [
            c for c in original_checks if c.get("name") not in disabled
        ]

    # 6. Execute rules engine on combined dataset
    final_result = runner.update_from_cache(events_df=combined_events, reload_config=False)
    df_obs = final_result.output.copy()
    df_tot = final_result.total_events.copy()

    # 7. Apply ftfy encoding fixes and region text cleanups[cite: 1, 4]
    for df_target in [df_obs, df_tot]:
        if "text" in df_target.columns and not df_target.empty:
            mask = df_target["text"].notna()
            df_target.loc[mask, "text"] = df_target.loc[mask, "text"].astype(str).apply(ftfy.fix_text)
            df_target.loc[mask, "text"] = df_target.loc[mask, "text"].str.replace(", Colombia", "", regex=False)

            # TRANSLATE OBSERVATIONS IF REQUESTED (e.g., for English display)
            if "Observations" in df_target.columns and not df_target.empty:
                df_target["Observations"] = df_target["Observations"].apply(
                    lambda x: translate_flags(x, lang)
                )

    return df_obs, df_tot

def load_history():
    """Loads the historical review logs."""
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    return pd.DataFrame()

# Sidebar navigation
with st.sidebar:
    lang = st.radio("🌐 Language / Idioma", ["ES", "EN"], horizontal=True, label_visibility="collapsed")
    st.divider()

    # SGC logo placeholder
    if (ROOT_DIR / "sgc.jpg").exists():
        st.image(str(ROOT_DIR / "sgc.jpg"), width=160)
    st.caption("NAVEGACIÓN")

    view = st.radio(
        "Seleccionar vista",
        ["Revisión Actual", "Historial de Revisiones"],
        label_visibility="collapsed"
    )

    st.divider()
    current_user = getpass.getuser()
    st.caption(f"🟢 **{current_user}** @ RSNC")

# View 1: Revisión Actual
if view == TEXTS["view_1"][lang]:
    st.title(TEXTS["v1_title"][lang])
    st.write(TEXTS["v1_subtitle"][lang])

    # Input section
    with st.container(border=True):
        st.subheader("Parámetros de Búsqueda")

        col1, col2, col3 = st.columns(3)
        with col1:
            revisor_name = st.text_input("Nombre del Revisor", value=current_user)
            author_sel = st.selectbox(
                "Búsqueda por autor",
                ["Todos", "gerard", "kgarcia", "dcreina", "muruena", "william", "axlopez", "amarin", "hmoreno", "seismo", "sismologo"]
            )
        with col2:
            # Start Date & Time
            col_sd, col_st = st.columns([1.2, 1])
            with col_sd:
                start_d = st.date_input("Fecha Inicio*", value=None, key="start_d")
            with col_st:
                start_t = st.time_input("Hora Inicio", value=datetime.strptime("00:00:00", "%H:%M:%S").time(), step=1,
                                        key="start_t")

            # End Date & Time (Optional)
            col_ed, col_et = st.columns([1.2, 1])
            with col_ed:
                end_d = st.date_input("Fecha Fin", value=None, key="end_d")
            with col_et:
                end_t = st.time_input("Hora Fin", value=datetime.strptime("23:59:59", "%H:%M:%S").time(), step=1,
                                      key="end_t")

            # Combine Date and Time into full Python datetime objects
            start_date = datetime.combine(start_d, start_t) if start_d else None
            end_date = datetime.combine(end_d, end_t) if end_d else None
        with col3:
            # Standalone selectbox for Potentially Locatable Event
            eval_locatable = st.selectbox(
                "Potentially Locatable",
                options=[True, False],
                index=1,
                format_func=lambda x: "Evaluar" if x else "Ignorar",
                help="Seleccione si desea evaluar o ignorar la regla de 'Eventos Potencialmente Localizables'."
            )

            # Popover for configuring the remaining 30 checks
            categorized_checks = get_categorized_checks(DEFAULT_CONFIG)
            disabled_checks = []

            with st.popover("⚙️ Configurar Chequeos", width="stretch"):
                st.markdown("**Desmarque los chequeos que desea descartar:**")
                for cat_name, check_list in categorized_checks.items():
                    with st.expander(f"{cat_name} ({len(check_list)})", expanded=False):
                        for check_name in check_list:
                            is_active = st.checkbox(check_name, value=True, key=f"chk_{check_name}")
                            if not is_active:
                                disabled_checks.append(check_name)

            # Add 'Potentially locatable event' to disabled list if set to False
            if not eval_locatable:
                disabled_checks.append("Potentially locatable event")

        run_btn = st.button("Ejecutar Revisión", type="primary")

    # Main content section
    if run_btn:
        if not start_date and author_sel == "Todos":
            st.error("Debe proporcionar al menos una fecha de inicio o seleccionar un autor específico.")
        elif start_date and end_date and start_date > end_date:
            st.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
        else:
            with st.spinner("Conectando a la base de datos de SeisComP y ejecutando la rutina de revisión..."):
                df_obs, df_tot = run_backend_pipeline(
                    config_path=DEFAULT_CONFIG,
                    st_date=start_date,
                    e_date=end_date,
                    author=author_sel,
                    disabled=disabled_checks
                )
                st.session_state["df_results"] = df_obs
                st.session_state["df_totals"] = df_tot
                st.success(f"Revisión completada con éxito. Los resultados se muestran a continuación.")

    # Simulate running the pipeline and storing results in session state
    if "df_results" in st.session_state:
        df = st.session_state["df_results"].copy()
        df_totals = st.session_state["df_totals"].copy()

        if df.empty and df_totals.empty:
            st.warning("No se encontraron eventos que cumplan con los criterios de búsqueda.")
        else:
            # Ensure both "Revisado" and "Notas" columns exist in the DataFrames
            for temp_df in [df, df_totals]:
                if not temp_df.empty:
                    if "Revisado" not in temp_df.columns:
                        temp_df.insert(0, "Revisado", False)
                    if "Notas" not in temp_df.columns:
                        temp_df.insert(1, "Notas", "")  # Insert blank string column for user notes

            # 2. Define the Spanish display names mapping
            short_names = {
                "time_value": "Hora UTC",
                "publicID": "ID",
                "text": "Región",
                "depth_value": "Prof",
                "magnitude_value": "Mag",
                "magnitude_type": "TipoM",
                "quality_standardError": "RMS",
                "depth_uncertainty": "ErrZ",
                "latitude_uncertainty": "ErrLat",
                "longitude_uncertainty": "ErrLon",
                "quality_associatedPhaseCount": "Fases",
                "creationInfo_author": "Autor",
                "event_type": "Tipo Evento",
                "creationInfo_agencyID": "Agencia",
                "Observations": "Observaciones"
            }

            # 3. Create the dynamic column configuration for the UI
            col_cfg = {
                "Revisado": st.column_config.CheckboxColumn("Revisado", help="Marque si el evento ha sido revisado."),
                "Notas": st.column_config.TextColumn("Notas", help="Agregue un comentario relevante.")
            }

            # Append the short names to the config so they render in Spanish
            for col_orig, col_short in short_names.items():
                col_cfg[col_orig] = st.column_config.Column(label=col_short)

            # 4. Determine the exact display order (only showing these specific columns on screen)
            display_order_df = ["Revisado", "Notas"] + [c for c in short_names.keys() if c in df.columns]
            display_order_tot = ["Revisado", "Notas"] + [c for c in short_names.keys() if c in df_totals.columns]

            st.divider()

            # Table 1: Display the results with observations
            st.subheader(f"Resultados de la Revisión ({df.shape[0]} registros)")
            st.write("Marque los eventos que han sido revisados y agregue observaciones si es necesario.")

            # Interactive Data Editor for Observations
            with st.container(border=True):
                edited_df = st.data_editor(
                    df,
                    column_order=display_order_df,
                    column_config=col_cfg,
                    disabled=[col for col in df.columns if col not in ["Revisado", "Notas"]],
                    width="stretch",
                    hide_index=True
                )

            st.divider()

            # Table 2: Display the total results for reference
            st.subheader(f"Todos los eventos obtenidos ({df_totals.shape[0]} registros)")

            with st.container(border=True):
                edited_df_totals = st.data_editor(
                    df_totals,
                    column_order=display_order_tot,
                    column_config=col_cfg,
                    disabled=[col for col in df_totals.columns if col not in ["Revisado", "Notas"]],
                    width="stretch",
                    hide_index=True
                )

            st.divider()

            # Save action button
            col_save, _ = st.columns([1, 2])
            with col_save:
                if st.button("Guardar Eventos Revisados", type="primary", width="stretch"):
                    # Extract checked rows from BOTH tables
                    rev1 = edited_df[edited_df["Revisado"] == True].copy() if "Revisado" in edited_df.columns else pd.DataFrame()
                    rev2 = edited_df_totals[edited_df_totals["Revisado"] == True].copy() if "Revisado" in edited_df_totals.columns else pd.DataFrame()

                    # Combine them into a single DataFrame
                    reviewed = pd.concat([rev1, rev2], ignore_index=True)

                    # Check if the resulting DataFrame is not empty and has the 'publicID' column
                    if not reviewed.empty and "publicID" in reviewed.columns:

                        # Ensure 'Observations' exists even if ONLY Table 2 was checked <---
                        if "Observations" not in reviewed.columns:
                            reviewed["Observations"] = None

                        # Drop duplicates (keeps the first occurrence from rev1 so observations aren't lost)
                        reviewed = reviewed.drop_duplicates(subset=["publicID"])

                        # Add audit columns
                        reviewed["Revisor"] = revisor_name
                        reviewed["Fecha Revisión"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        # Save to CSV
                        save_header = not os.path.exists(LOG_FILE)
                        reviewed.to_csv(LOG_FILE, mode='a', header=save_header, index=False)

                        st.success(f"¡{len(reviewed)} eventos únicos guardados exitosamente en el historial!")
                    else:
                        st.warning("No se ha seleccionado ningún evento para guardar.")


# VIEW 2: HISTORIAL DE REVISIONES
elif view == "Historial de Revisiones":
    st.title("Historial de Revisiones")
    st.caption("Registro histórico de todos los eventos marcados como revisados.")

    df_hist = load_history()

    if df_hist.empty:
        st.info("No hay registros históricos disponibles aún.")
    else:
        with st.container(border=True):
            # 1. Define the priority columns you want on the far left
            front_cols = ["Revisado", "Revisor", "Fecha Revisión", "Notas", "Observations"]

            # Safely check which of those exist to prevent KeyError
            front_cols_present = [c for c in front_cols if c in df_hist.columns]

            # Put the rest of the columns afterward
            back_cols = [c for c in df_hist.columns if c not in front_cols_present]

            # Reorder the dataframe
            df_hist_reordered = df_hist[front_cols_present + back_cols]

            # 2. Display the sorted and reordered DataFrame
            st.dataframe(
                df_hist_reordered.sort_values(by="Fecha Revisión", ascending=False),
                width="stretch",
                hide_index=True
            )