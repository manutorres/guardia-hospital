from os import environ
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv(".env")

client = MongoClient(
    environ["MONGODB_HOSTNAME"], 
    int(environ["MONGODB_PORT"])
)

db = client.guardia_hospital

# Índice creado sobre el DNI del paciente para beneficiar la búsqueda de todas las consultas por paciente
db.consultas_historial.create_index("paciente.dni")

# Índice creado sobre el fecha-hora de admición para beneficiar el ordenamiento del listado histórico de consultas
db.consultas_historial.create_index("fecha_hora_admision")

# Índice creado sobre la prioridad y el tiempo de admisión para beneficiar la consulta sobre la lista de espera
db.consultas_activas.create_index([
    ("prioridad.nivel", DESCENDING), 
    ("fecha_hora_admision", DESCENDING)
])