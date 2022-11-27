from os import environ
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(".env")

client = MongoClient(
    environ["MONGODB_HOSTNAME"], 
    int(environ["MONGODB_PORT"])
)

db = client.guardia_hospital

# Índice creado sobre el DNI del paciente para beneficiar la búsqueda de todas las consultas por paciente
db.consultas.create_index("paciente.dni")
