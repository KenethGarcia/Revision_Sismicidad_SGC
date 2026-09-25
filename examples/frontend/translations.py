# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# ----------------------------------------------------------------------------------------------------------------------
# This file contains a dictionary to translate the observations returned by the frontend into Spanish.
# The keys are the original English observations, and the values are their corresponding Spanish translations.
# ----------------------------------------------------------------------------------------------------------------------

CHECK_TRANSLATIONS = {
    # ── Duplicados ──
    "General duplicate search": "Posible duplicado",

    # ── Calidad e Incertidumbre ──
    "High RMS": "RMS Alto",
    "High Lat Err": "Error Lat Alto",
    "High Lon Err": "Error Lon Alto",
    "High Depth Err": "Error Prof Alto",
    "Negative Depth": "Profundidad negativa",
    "Noncommon High Depth": "Profundidad >200km",
    "Earthquake with 3 or fewer stations (sc6)": "Sismo con menos de 3 estaciones",
    "Hypo71 events with more than 101 associated phases?": "Hypo71 con > 101 fases",

    # ── Etiquetas y Comentarios ──
    "Locatable event": "Evento localizable",
    "Invalid label": "Etiqueta inválida",
    "Unprocessed or unassociated event": "Evento no procesado/asociado",
    "Event without DESTACADO comment": "Falta comentario DESTACADO",
    "Event with comment different from DESTACADO": "Comentario diferente a DESTACADO",

    # ── Reglas Especiales de Zona ──
    "Event inside local zone with outside label": "En zona local con etiqueta 'outside'",
    "Event outside local zone with wrong label": "Fuera de zona local con etiqueta errónea",
    "Pacific/Caribbean event with high depth": "Evento Pacífico/Caribe profundo",
    "DESTACADO event with M < 3 outside network interest zone": "DESTACADO M<3 fuera de zona local",
    "Potentially locatable event": "Evento potencialmente localizable",

    # ── Modelos de Velocidad ──
    "DESTACADO event without NLL earth model": "DESTACADO sin modelo NLL",
    "Event outside NLL zone with NLL earth model": "Modelo NLL usado fuera de zonaNLL",
    "Wrong model for CARMA zone": "Relocalizar con CARMA",
    "Wrong model for Cesar zone": "Relocalizar con Cesar",
    "Wrong model for PtoGtn zone": "Relocalizar con PtoGtn",
    "Wrong model for VMM zone": "Relocalizar con VMM",

    # ── Magnitudes por Zona ──
    "Wrong mag type for zone1": "Tipo magnitud erróneo (Zona 1)",
    "Wrong mag type for zone2": "Tipo magnitud erróneo (Zona 2)",
    "Wrong mag type for zone3": "Tipo magnitud erróneo (Zona 3)",
    "Wrong mag type for zone4": "Tipo magnitud erróneo (Zona 4)",
    "Wrong mag type for zone5": "Tipo magnitud erróneo (Zona 5)",
    "Wrong mag type for VMM zone": "Tipo magnitud erróneo (VMM)",
    "Wrong mag type for PtoGtn zone": "Tipo magnitud erróneo (PtoGtn)",
}

# CENTRALIZED TRANSLATION DICTIONARY
TEXTS = {
    "nav_header": {"ES": "NAVEGACIÓN", "EN": "NAVIGATION"},
    "view_1": {"ES": "Revisión Actual", "EN": "Current Review"},
    "view_2": {"ES": "Historial de Revisiones", "EN": "Revision History"},
    "v1_title": {"ES": "Rutina de Revisión de Sismicidad", "EN": "Seismicity Review Routine"},
    "v1_subtitle": {"ES": "Filtre, ejecute y marque los eventos revisados.", "EN": "Filter, execute, and mark reviewed events."},
    "search_params": {"ES": "Parámetros de Búsqueda", "EN": "Search Parameters"},
    "reviewer_name": {"ES": "Nombre del Revisor", "EN": "Reviewer Name"},
    "author_search": {"ES": "Búsqueda por autor", "EN": "Search by author"},
    "all_authors": {"ES": "Todos", "EN": "All"},
    "start_date": {"ES": "Fecha Inicio*", "EN": "Start Date*"},
    "start_time": {"ES": "Hora Inicio", "EN": "Start Time"},
    "end_date": {"ES": "Fecha Fin", "EN": "End Date"},
    "end_time": {"ES": "Hora Fin", "EN": "End Time"},
    "eval": {"ES": "Evaluar", "EN": "Evaluate"},
    "ignore": {"ES": "Ignorar", "EN": "Ignore"},
    "locatable_help": {
        "ES": "Seleccione si desea evaluar o ignorar la regla de 'Eventos Potencialmente Localizables'.",
        "EN": "Select whether to evaluate or ignore the 'Potentially Locatable Events' rule."
    },
    "config_checks": {"ES": "⚙️ Configurar Chequeos", "EN": "⚙️ Configure Checks"},
    "uncheck_msg": {"ES": "**Desmarque los chequeos que desea descartar:**", "EN": "**Uncheck the rules you want to ignore:**"},
    "btn_run": {"ES": "Ejecutar Revisión", "EN": "Run Review"},
    "err_no_date": {
        "ES": "Debe proporcionar al menos una fecha de inicio o seleccionar un autor específico.",
        "EN": "You must provide at least a start date or select a specific author."
    },
    "err_dates": {"ES": "La fecha de inicio no puede ser posterior a la fecha de fin.", "EN": "Start date cannot be after end date."},
    "spin_run": {
        "ES": "Conectando a la base de datos de SeisComP y ejecutando la rutina de revisión...",
        "EN": "Connecting to SeisComP database and executing review routine..."
    },
    "succ_run": {"ES": "Revisión completada con éxito. Los resultados se muestran a continuación.", "EN": "Review completed successfully. Results are shown below."},
    "warn_no_events": {"ES": "No se encontraron eventos que cumplan con los criterios de búsqueda.", "EN": "No events found matching the search criteria."},
    "revisado": {"ES": "Revisado", "EN": "Reviewed"},
    "notas": {"ES": "Notas", "EN": "Notes"},
    "rev_help": {"ES": "Marque si el evento ha sido revisado.", "EN": "Mark if the event has been reviewed."},
    "not_help": {"ES": "Agregue un comentario relevante.", "EN": "Add a relevant comment."},
    "res_rev": {"ES": "Resultados de la Revisión", "EN": "Review Results"},
    "res_msg": {
        "ES": "Marque los eventos que han sido revisados y agregue observaciones si es necesario.",
        "EN": "Mark the events that have been reviewed and add observations if necessary."
    },
    "locatable_count": {
        "ES": "📌 Se detectaron **{}** eventos potencialmente localizables.",
        "EN": "📌 **{}** potentially locatable events were detected."
    },
    "all_ev": {"ES": "Todos los eventos obtenidos", "EN": "All Retrieved Events"},
    "records": {"ES": "registros", "EN": "records"},
    "btn_save": {"ES": "Guardar Eventos Revisados", "EN": "Save Reviewed Events"},
    "succ_save": {"ES": "¡{} eventos únicos guardados exitosamente en el historial!", "EN": "{} unique events successfully saved to history!"},
    "warn_save": {"ES": "No se ha seleccionado ningún evento para guardar.", "EN": "No events selected to save."},
    "v2_title": {"ES": "Historial de Revisiones", "EN": "Revision History"},
    "v2_subtitle": {"ES": "Registro histórico de todos los eventos marcados como revisados.", "EN": "Historical log of all events marked as reviewed."},
    "v2_empty": {"ES": "No hay registros históricos disponibles aún.", "EN": "No historical records available yet."}
}