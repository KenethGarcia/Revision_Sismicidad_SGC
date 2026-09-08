# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# ----------------------------------------------------------------------------------------------------------------------
# This file contains a Command Line Interface (CLI) example for the package.
# It demonstrates how to use the CLI to perform various tasks related to read, process and analyze SeisComP data.
# The CLI is built using the click library and provides a complete advanced example of how strong is the package in
# terms of usability and functionality.
# NOTE: THE CLI IS NOT INTENDED FOR PRODUCTION USE. IT IS PROVIDED AS AN EXAMPLE OF HOW TO USE THE PACKAGE.

# To run it, go to the root directory of the package and execute the following command:
# python -m examples.cli.revision_cli --config examples/data/configs/seismic_revision_routine.toml <other options>
# ----------------------------------------------------------------------------------------------------------------------
import sys
import ftfy
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
@click.option(
    "-f", "--skip-locatable",
    is_flag=True,
    help="Omitir eventos con observación 'Potentially locatable event'."
)
@click.option(
    "--output", "-o",
    is_flag=True,
    help="Guardar los resultados limpios en un archivo CSV en el directorio actual."
)
def cli(config: Path, start: str, end: str, author: str, skip_locatable: bool, output: bool):
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
            execution_plan.append(("SeisComP3", start_dt, end_dt))
        elif start_dt >= RSNC_CUTOFF:
            execution_plan.append(("SeisComP6", start_dt, end_dt))
        else:
            # Time window spans both SC3 and SC6, split the execution plan
            click.echo(f"[*] La ventana de tiempo proporcionada abarca eventos en SeisComP3 y SeisComP6. Se solicitará la información de ambos sistemas separado por {RSNC_CUTOFF}.")
            execution_plan.append(("SeisComP3", start_dt, RSNC_CUTOFF))
            execution_plan.append(("SeisComP6", RSNC_CUTOFF, end_dt))
    else:
        # If no time filter is provided (author only), force strict cutoffs to avoid SC6 mirror data
        click.echo("[*] Búsqueda por autor solamente detectada. Se aplicarán cortes estrictos entre SeisComP3 y SeisComP6 para evitar datos duplicados de espejo...")
        execution_plan.append(("SeisComP3", None, RSNC_CUTOFF))
        execution_plan.append(("SeisComP6", RSNC_CUTOFF, None))

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
            sql_params["start_time"] = q_start.strftime('%Y-%m-%d %H:%M:%S')
            where_clauses.append(f"base_query.{time_col} >= %(start_time)s")

        if q_end:
            sql_params["end_time"] = q_end.strftime('%Y-%m-%d %H:%M:%S')
            where_clauses.append(f"base_query.{time_col} < %(end_time)s")

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
        wrapped_sql = f"""SELECT * FROM ({base_sql}) AS base_query WHERE {where_sql} ORDER BY base_query.{time_col} ASC"""

        # Fetch the events (skipping checks for now)
        if q_name == "SeisComP3":
            click.echo(f"[*] Ejecutando consulta para SeisComP3...")
        elif q_name == "SeisComP6":
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
    combined_events = pd.concat(frames, axis=0, ignore_index=True)
    if len(combined_events) == 0:
        click.echo("[!] No se encontraron eventos que coincidan con los criterios proporcionados.")
        return

    click.echo(f"[*] Encontrados un total de {len(combined_events)} eventos que coinciden con los criterios proporcionados. Ejecutando la rutina de revisión...")

    # 6. Remove the specific check from memory if the flag -f is provided
    if skip_locatable:
        click.echo("[*] Omitiendo eventos con observación 'Potentially locatable event'...")
        original_checks = runner._cm.config_data.get("checks", [])
        filtered_checks = [check for check in original_checks if check.get("name") != "Potentially locatable event"]
        runner._cm.config_data["checks"] = filtered_checks

    # 7. Run the engine on the combined dataset
    final_result = runner.update_from_cache(events_df=combined_events, reload_config=False)

    # 8. Pretty print the final result
    if len(final_result.output) == 0:
        click.secho("[!] No hay eventos por revisar después de aplicar la rutina.", fg="green")
        return
    else:
        try:
            mask = final_result.output['text'].notna()
        except KeyError:
            click.secho("[!] La columna 'text' no está presente en el resultado final. Imprimiendo el resultado completo...", fg="red")
            click.echo(final_result.output)
            return

        # Apply ftfy to fix text encoding issues in the 'text' column
        final_result.output.loc[mask, 'text'] = final_result.output.loc[mask, 'text'].astype(str).apply(ftfy.fix_text)

        # Remove ', Colombia' from the text column to keep the table compact
        final_result.output.loc[mask, 'text'] = final_result.output.loc[mask, 'text'].str.replace(", Colombia", "", regex=False)

        # NEW LOGIC: Save the cleaned data to CSV in the Current Working Directory
        if output:
            # Generate a dynamic filename based on the current time to avoid overwriting previous runs
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"revision_RSNC_{timestamp}.csv"

            # Save without the pandas index column
            final_result.output.to_csv(filename, index=False)
            click.secho(f"[*] Archivo guardado exitosamente en: {Path.cwd() / filename}", fg="green")

        # Create a copy of the output DataFrame
        display_df = final_result.output.copy()

        # Format magnitude and error columns to exactly 2 decimal places
        cols_to_round = [
            "magnitude_value",
            "quality_standardError",
            "depth_uncertainty",
            "latitude_uncertainty",
            "longitude_uncertainty"
        ]

        for col in cols_to_round:
            if col in display_df.columns:
                # Format the numbers as strings with 2 decimals, keeping NaNs intact for the next step
                display_df[col] = display_df[col].map(lambda x: f"{x:.2f}" if pd.notna(x) else x)


        # Replace all NaN/None values across the entire table with '--'
        # Explicitly cast columns to 'object' first to prevent Pandas dtype FutureWarnings
        for col in display_df.columns:
            display_df[col] = display_df[col].astype(object)
        display_df.fillna("--", inplace=True)

        # 4. Map the long SeisComP names to short Spanish display names
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

        display_df.rename(columns=short_names, inplace=True)

        # 5. Print the beautifully formatted and shortened table
        click.secho("[*] Resultado de la revisión:", fg="blue", bold=True)
        click.echo(display_df)

        # 6. Print Execution Summary
        click.echo("")  # Add an empty line
        click.secho("[*] Resumen de Ejecución:", fg="blue", bold=True)

        # Extract the Observations column, dropping NaNs to avoid string errors
        obs_series = final_result.output["Observations"].dropna().astype(str)

        # Count flagged events (excluding the locatable flag)
        # We temporarily remove the locatable text and semicolons to see if any other flags remain
        cleaned_obs = (
            obs_series
            .str.replace("Potentially locatable event", "", regex=False)
            .str.replace(";", "", regex=False)
            .str.strip()
        )
        flagged_count = (cleaned_obs != "").sum()

        if flagged_count != 0:
            click.echo(f"    • Eventos marcados (con otras observaciones): {flagged_count}")

        # Count locatable events only if the user didn't hide them
        if not skip_locatable:
            locatable_count = obs_series.str.contains("Potentially locatable event", regex=False).sum()
            click.echo(f"    • Eventos potencialmente localizables:        {locatable_count}")

        click.echo("")  # Add a final empty line for terminal cleanliness


if __name__ == "__main__":
    cli()



