from datetime import datetime
from os import environ
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, OperationFailure
from bson.errors import InvalidId
from dotenv import load_dotenv
from models import ConsultaModel, DatosMedicosModel, EstadoAtendidoModel, DatosMedicosModel


load_dotenv(".env")

client = MongoClient(
    environ["MONGODB_HOSTNAME"], 
    int(environ["MONGODB_PORT"])
)
db = client.guardia_hospital
print("Database connection established.")


def get_consultas():
    consultas = list(db.consultas.find())
    return consultas


def get_consulta(id: str):
    consulta = db.consultas.find_one({"_id": id})
    return consulta


def create_consulta(consulta: dict):    
    resultado = db.consultas.insert_one(consulta)
    consulta_creada = db.consultas.find_one({"_id": resultado.inserted_id})
    return consulta_creada


def update_datos_paciente(id: str, datos_paciente: dict):
    resultado = db.consultas.update_one({"_id": id}, {"$set": {"datos_paciente": datos_paciente}})
    if (resultado.matched_count == 0):
        return False    
    consulta_actualizada = db.consultas.find_one({"_id": id})
    return consulta_actualizada


def update_estado_atendido(id: str, estado_atendido: dict):
    resultado = db.consultas.update_one({"_id": id}, {"$set": {"estado_atendido": estado_atendido}})    
    if (resultado.matched_count == 0):
        return False    
    consulta_actualizada = db.consultas.find_one({"_id": id})
    return consulta_actualizada


def update_prioridad(id: str, prioridad: dict):
    resultado = db.consultas.update_one(
        { "_id": id }, 
        [{
            "$set": {
                "prioridad.nivel": prioridad["nivel"],
                "prioridad.hora": {
                    "$cond": {
                        "if": {
                            "$eq": ["$prioridad.hora", None]
                        },
                        "then": prioridad["hora"],
                        "else": "$prioridad.hora" # existing value
                    }
                }
            }
        }]
    )
    if (resultado.matched_count == 0):
        return False    
    consulta_actualizada = db.consultas.find_one({"_id": id})
    return consulta_actualizada


def update_datos_medicos(id: str, datos_medicos: dict):

    examen_fisico = datos_medicos["examen_fisico"] 
    
    resultado = db.consultas.update_one(
        {"_id": id}, 
        [{
            "$set": {
                "datos_medicos.signos_vitales": datos_medicos["signos_vitales"],
                "datos_medicos.anamnesis_enfermeria": datos_medicos["anamnesis_enfermeria"],
                "datos_medicos.examen_fisico.examen": examen_fisico["examen"],
                "datos_medicos.examen_fisico.hora": {
                    "$cond": {
                        "if": {
                            "$ne": ["$datos_medicos.examen_fisico.examen", examen_fisico["examen"]]
                        },
                        "then": examen_fisico["hora"],
                        "else": "$datos_medicos.examen_fisico.hora" # existing value
                    }
                },
                "datos_medicos.medicacion": datos_medicos["medicacion"],
            }
        }]
    )
    if (resultado.matched_count == 0):
        return False    
    consulta_actualizada = db.consultas.find_one({"_id": id})
    return consulta_actualizada