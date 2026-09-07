# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# ----------------------------------------------------------------------------------------------------------------------
# This file contains a Command Line Interface (CLI) example for the package.
# It demonstrates how to use the CLI to perform various tasks related to read, process and analyze SeisComP data.
# The CLI is built using the click library and provides a complete advanced example of how strong is the package in
# terms of usability and functionality.
# NOTE: THE CLI IS NOT INTENDED FOR PRODUCTION USE. IT IS PROVIDED AS AN EXAMPLE OF HOW TO USE THE PACKAGE.
# ----------------------------------------------------------------------------------------------------------------------
import sys
import click
import pandas as pd
from pathlib import Path
from src.io.sql import load_sql
from src.core.runner import Runner

# Ensure the root directory of the package is in the system path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Define a cutoff date for the RSNC data. This date is used to filter events between SeisComP3 and SeisComP6 databases.
RSNC_CUTOFF = pd.to_datetime("2026-03-17 00:00:00", utc=True)


@click.command(help="Ejecutar la Rutina de Revisión de Sismicidad en la Red Sismológica Nacional (RSNC) de Colombia.")
@click.option(
    "-c", "--config",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="Ruta al archivo de configuración para la rutina.",
)
@click.option(
    "-s", "--start",
    type=str,
    help="Fecha de inicio de la revisión.",
)
@click.option(
    "-e", "--end",
    type=str,
    help="Fecha de fin de la revisión.",
)
@click.option(
    "-a", "--author",
    type=str,
    help="Filtrado por autor de evento.",
)

def cli(config: Path, start: str, end: str, author: str):
    """
    Command Line Interface (CLI) for executing the Seismicity Review Routine in the National Seismological Network (RSNC) of Colombia.
    This CLI allows users to run the routine with a specified configuration file and optional filters for date range and author.
    """
    # 1. Validate inputs: Require author (-a) or start date (-s) to be provided, or both.
    if not author and not start:
        raise click.UsageError(
            "Debe proporcionar un autor (-a), una fecha de inicio (-s) o ambos para ejecutar la rutina."
        )
    #   1.1. If end date is provided without start date, raise an error.
    if end and not start:
        raise click.UsageError(
            "Si proporciona una fecha de fin (-e), también debe proporcionar una fecha de inicio (-s)."
        )
    #   1.2. If only start date is provided without end date, set end date to current UTC date.
    if start and not end:
        end = pd.Timestamp.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        click.echo(f"[*] Fecha de fin no proporcionada. Se establecerá automáticamente a la fecha actual UTC: {end}")

    # 2. Parse times (if provided) and determine the RSNC execution plan
    execution_plan = []

    if start and end:
        try:
            start_dt = pd.to_datetime(start, format="mixed", utc=True, errors="raise")
            end_dt = pd.to_datetime(end, format="mixed", utc=True, errors="raise")
        except ValueError as exc:
            raise click.BadParameter(f"Error al analizar las fechas proporcionadas: {exc}")

        if start_dt >= end_dt:
            raise click.BadParameter("La fecha de inicio debe ser anterior a la fecha de fin.")

        # Determine SC3 vs SC6 routing based on the cutoff date
        if end_dt <= RSNC_CUTOFF:
            execution_plan.append(("events_sc3", start_dt, end_dt))
        elif start_dt >= RSNC_CUTOFF:
            execution_plan.append(("events_sc6", start_dt, end_dt))
        else:
            # Time window spans both SC3 and SC6, split the execution plan
            click.echo(f"[*] La ventana de tiempo proporcionada abarca eventos en SeisComP3 y SeisComP6. Se solicitará la información de ambos sistemas separado por {RSNC_CUTOFF}.")
            execution_plan.append(("events_sc3", start_dt, RSNC_CUTOFF))
            execution_plan.append(("events_sc6", RSNC_CUTOFF, end_dt))
    else:
        # If no time filter is provided (author only), force strict cutoffs to avoid SC6 mirror data
        click.echo("[*] Búsqueda por autor solamente detectada. Se aplicarán cortes estrictos entre SeisComP3 y SeisComP6 para evitar datos duplicados de espejo...")
        execution_plan.append(("events_sc3", None, RSNC_CUTOFF))
        execution_plan.append(("events_sc6", RSNC_CUTOFF, None))

    # 3. Initialize the Runner
    runner = Runner(config_path=config)
    time_col = runner._cm.get_time_column()

    available_queries = runner.list_queries()
    frames = []

    # 4. Process the execution plan
    for q_name, q_start, q_end in execution_plan:
        if q_name not in available_queries:
            click.echo(f"[!] La consulta '{q_name}' no está disponible en la configuración proporcionada. Se omitirá esta parte del plan de ejecución.")
            continue

        sql_params = {}
        where_clauses = []

        # Add dynamic time bounds independently to handle one-sided queries safely
        if q_start:
            sql_params["start_time"] = q_start.strftime('%Y-%m-%d %H:%M:%SZ')
            where_clauses.append(f"base_query.{time_col} >= :%(start_time)s")

        if q_end:
            sql_params["end_time"] = q_end.strftime('%Y-%m-%d %H:%M:%SZ')
            where_clauses.append(f"base_query.{time_col} < :%(end_time)s")

        # Add dynamic author filter if provided
        if author:
            sql_params["author_pattern"] = f"%{author}%"
            where_clauses.append("base_query.creationInfo_author LIKE %(author_pattern)s")

        where_sql = " AND ".join(where_clauses)

        # Load the base SQL text
        query_cfg = runner._cm.select_query(name=q_name)
        base_sql = load_sql(
            query_cfg=query_cfg,
            base_dir=runner._cm.base_dir,
            config_name=runner._cm.config_path.name
        )

        # Wrap the query
        wrapped_sql = f"""
                    SELECT * 
                    FROM ({base_sql}) AS base_query
                    WHERE {where_sql}
                    ORDER BY base_query.{time_col} ASC
                """

        # Fetch the events (skipping checks for now)
        if q_name == "events_sc3":
            click.echo(f"[*] Ejecutando consulta para SeisComP3...")
        elif q_name == "events_sc6":
            click.echo(f"[*] Ejecutando consulta para SeisComP6...")
        result = runner.run(
            query_name=q_name,
            multi_query=False,
            perform_duplicates=False,
            perform_checks=False,
            sql_text_override=wrapped_sql,
            sql_params=sql_params
        )
        frames.append(result.total_events)

    # 5. Concatenate results and apply the engine across the entire dataset
    if not frames:
        click.echo("[!] No se encontraron eventos que coincidan con los criterios proporcionados.")
        return

    combined_events = pd.concat(frames, axis=0, ignore_index=True)

    # 6. Run the engine on the combined dataset
    click.echo(f"[*] Encontrados un total de {len(combined_events)} eventos que coinciden con los criterios proporcionados. Ejecutando la rutina de revisión...")
    final_result = runner.update_from_cache(events_df=combined_events, reload_config=False)
    click.echo(f"[*] Resultado de la revisión:")
    click.echo(final_result)


if __name__ == "__main__":
    cli()



