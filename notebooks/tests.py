import pymysql

conn = pymysql.connect(
    host="10.100.100.12",
    port=3306,
    user="consulta",
    password="HbiAEse5rz",
    db="seiscomp",
    connect_timeout=5
)