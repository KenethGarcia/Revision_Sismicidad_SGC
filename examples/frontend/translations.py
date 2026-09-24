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