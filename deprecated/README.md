![Logo](docs/images/SGC_logo.png)

# Rutina de revisión de sismicidad - Red Sismológica Nacional de Colombia (RSNC)

Como parte del procesamiento diario de sismicidad de la Red Sismológica Nacional de Colombia (RSNC), es primordial garantizar la calidad de la información sísmica presentada a la comunidad. Para ello, la información procesada es revisada diariamente por el grupo de analistas, quienes realizan un análisis detallado de los eventos sísmicos reportados del día subsecuentemente anterior.

En este proceso de revisión, se busca identificar eventos sísmicos que no cumplan con los estándares de calidad establecidos por la RSNC, como errores de localización alto o modelos incorrectos de propagación, entre otros. Una parte importante de este proceso es realizado por la rutina automática presentada en este repositorio, la cual permite realizar una inspección de los parámetros de cada uno de los eventos sísmicos procesados.

## Requisitos

- Python 3.12 o superior
- Los siguientes paquetes de Python (lista detallada disponible en el archivo `requirements.txt`):
  - `pandas` 
  - `numpy`
  - `colorama`
  - `shapely`
  - `pymysql`
  - `utils`
  - `tqdm`
  - `matplotlib`
  - `requests`
  - `pillow`
  - `haversine`

## Instalación

Para instalar los requisitos, puedes utilizar el siguiente comando:

```bash
pip install -r requirements.txt
```

## Testing

Esta rutina dispone de una serie de tests que permiten verificar el correcto funcionamiento de la misma. Para ejecutar los tests, sitúese en la carpeta donde esté guardado el directorio de tests y ejecute los siguientes comandos:

```bash
python -m unittest tests.test_revision.TestRevision
python -m unittest tests.test_utils.TestUtils
```

Esto ejecutará los tests de la rutina de revisión y de las funciones auxiliares. Si todos los tests se ejecutan sin errores, significa que la rutina está funcionando correctamente. En otro caso, contacte al desarrollador para reportar el error.

## Cómo usar la rutina

>[!NOTE]
> Si se encuentra trabajando en los servidores .11 y .8 de la RSNC, no es necesario especificar el comando `python` al ejecutar la rutina, ya que el entorno de Python ya está configurado por defecto. En este caso, puede ejecutar directamente el comando `revision` siguiendo el formato:
>```
>$ revision +s <fecha_inicio> +e <fecha_final> <opciones>
>```
>Por ejemplo:
>```
>$ revision +s 20250301T000000 +e 20250331T235959 +u kgarcia +n 6 +f +o
>```

Para utilizar la rutina de revisión de sismicidad, el formato de entrada debe seguir:

```bash
python <ruta al archivo>src/revision_revision.py +s <fecha_inicio> +e <fecha_final> <opciones>
```

Donde:
- `<ruta al archivo>` especifica la ruta donde esté almacenada la rutina (incluir la carpeta src si es necesario).
- `<fecha_inicio/final>` especifica el rango de fechas a revisar. El formato debe ser `aaaammddTHHMMSS` (ejemplo: `20231001T053045`).
- `<opciones>` son aquellos parámetros adicionales que se pueden incluir para personalizar la revisión. Las opciones disponibles son:
  - `+f` o `++flag` para inhabilitar la búsqueda de eventos con 7 o menos fases picadas (recomendado para revisiones con intervalos de tiempo extensos).
  - `+n` o `++n_processes` para especificar el número de procesos (threads) para ejecutar la rutina (recomendado para revisiones con intervalos de tiempo extensos).
  - `+u` o `++user` para realizar la revisión de eventos de un usuario en específico de la base de datos (p. ej., `+u kgarcia` o `+u bdrsn`).
  - `+o` o `++output` para especificar si se desea guardar la salida de la revisión en un archivo CSV. Por defecto, se guarda en la ruta actual donde se ejecuta la rutina.
  - `+p` o `++printer` para cambiar el estilo de impresión de la tabla. Por defecto, se imprime en formato de la librería pandas, pero se puede cambiar a un estilo más amigable con la vista (si se usa esta opción, se recomienda poner full screen en la terminal).

>[!NOTE]
> Como ejemplo, si se desea revisar los eventos sísmicos procesados por el usuario `kgarcia` para el mes de Marzo del 2025, con 6 procesos paralelos, guardando los resultados y sin tener en cuenta los eventos con 7 o menos fases, se puede ejecutar el siguiente comando:
>```
>$ python revision_revision.py +s 20250301T000000 +e 20250331T235959 +u kgarcia +n 6 +f +o
>```

## Revisiones implementadas en la rutina

La rutina de revisión de sismicidad incluye las siguientes inspecciones:

1. Eventos sísmicos con media cuadrática (RMS) superior a $1.51$.
2. Eventos sísmicos con errores de localización altos (latitud, longitud o profundidad superiores a 12 km).
3. Eventos localizables con etiqueta en la base de datos incorrecta (p. ej., "not locatable").
4. Eventos sísmicos con magnitudes fijadas NO correspondientes a su zona de localización.
5. Eventos sísmicos con localizaciones realizadas usando modelos de velocidad incorrectos.
6. Eventos sísmicos no localizables con 7 o menos fases picadas (desactivable con la opción `+f`).
7. Eventos sísmicos sin ninguna etiqueta disponible en la base de datos, o aquellos con etiquetas no válidas (p. ej., `nuclear explosion`).
8. Eventos sísmicos que no fueron procesados por un analista (aquellos que tienen origen automático).
9. Eventos sísmicos internacionales sin agencia asociada (aquellos con M > 5.0).
10. Eventos sísmicos destacados sin su etiqueta respectiva (aquellos que tienen magnitud superior a 4.0).
11. Eventos sísmicos ubicados en áreas de influencia volcánica sin la etiqueta `not locatable`.
12. Eventos sísmicos ubicados en las regiones del Océano Pacífico y Mar Caribe con alta profundidad (superior a 30 km).
13. Eventos sísmicos duplicados (aquellos que tienen latitud, longitud similar y están dentro de un rango de 4 segundos).
14. Eventos sísmicos con profundidades negativas.
15. Eventos sísmicos con etiqueta `earthquake` pero con menos de 6 fases procesadas.
16. Eventos sísmicos con etiqueta `earthquake` pero ubicados fuera del área de interés de la RSNC y eventos sísmicos de tipo `outside of network interest` ubicados dentro del área de interés.
17. Eventos sísmicos destacados dentro de la zona de NonLinLoc sin el modelo de velocidad de Poveda_et_al_2018 fijado.

## Contribuciones

Las contribuciones son bienvenidas. Si deseas contribuir a este proyecto, por favor abre un issue o una pull request.


## Atribución

Este proyecto fue desarrollado por el grupo de trabajo, evaluación, monitoreo y diagnóstico de dinámicas geológicas de la RSNC. El código fue escrito por el analista Keneth Garcia, bajo supervisión del sismólogo Angel Agudelo. El uso de este código es exclusivo para fines internos de la RSNC y no debe ser compartido sin autorización previa. La propiedad intelectual de este código pertenece a la RSNC y su uso está sujeto a las políticas y regulaciones internas de la institución.
