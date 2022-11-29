from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, OperationFailure
from bson.errors import InvalidId
from dotenv import load_dotenv
from os import environ


load_dotenv(".env")

client = MongoClient(
    environ["MONGODB_HOSTNAME"], 
    int(environ["MONGODB_PORT"])
)
db = client.guardia_hospital
print("Conexión con base de datos establecida.")

CONSULTAS_ACTIVAS = "consultas_activas"
CONSULTAS_HISTORIAL = "consultas_historial"



def get_consultas(coleccion: str = CONSULTAS_ACTIVAS):
    consultas = list(db[coleccion].find())
    return consultas



def get_consulta(id: str, coleccion: str = CONSULTAS_ACTIVAS):
    try:
        id = ObjectId(id)
        consulta = db[coleccion].find_one({"_id": id})
    except Exception as _:
        return None
    return consulta



def get_consultas_activas():
    no_atendidas = db[CONSULTAS_ACTIVAS].find().sort([
        ("prioridad.nivel", DESCENDING), 
        ("fecha_hora_admision", DESCENDING)
    ])
    return list(no_atendidas)



def get_consultas_por_dni(dni: str):
    consulta_activa = db[CONSULTAS_ACTIVAS].find_one({"dni": dni})
    consultas_previas = list(db[CONSULTAS_HISTORIAL].find({"dni": dni})).sort({"fecha_hora_admision"})
    return [consulta_activa].extend(consultas_previas)



def create_consulta(consulta: dict):    
    resultado = db[CONSULTAS_ACTIVAS].insert_one(consulta)
    consulta_creada = get_consulta(resultado.inserted_id)
    return consulta_creada



def update_consulta(id: str, coleccion: str = CONSULTAS_ACTIVAS, update = {}):
    try:
        id = ObjectId(id)
        consulta = db[coleccion].update_one({"_id": id}, update)
    except Exception as _:
        return None
    return consulta



def update_datos_paciente(id: str, datos_paciente: dict):    
    resultado = update_consulta(id, CONSULTAS_ACTIVAS, {"$set": {"datos_paciente": datos_paciente}})
    if (not resultado or resultado.matched_count == 0):
        return None    
    consulta_actualizada = get_consulta(id)
    return consulta_actualizada



def set_consulta_atendida(id: str, fecha_hora_atencion: datetime):
    try:
        id = ObjectId(id)
        db[CONSULTAS_ACTIVAS].aggregate([
            {"$match": {"_id": id}},
            {"$set": {"fecha_hora_atencion": fecha_hora_atencion}},
            {"$merge": {"into": CONSULTAS_HISTORIAL}}
        ])
        resultado = db[CONSULTAS_ACTIVAS].delete_one({"_id": id})
        if (resultado.deleted_count != 1):
            return None
         
        consulta_archivada = get_consulta(id, CONSULTAS_HISTORIAL)    

    except Exception as _:
        return None
    return consulta_archivada



def unset_consulta_atendida(id: str):
    try:
        id = ObjectId(id)
        db[CONSULTAS_HISTORIAL].aggregate([
            {"$match": {"_id": id}},
            {"$set": {"fecha_hora_atencion": None}},
            {"$merge": {"into": CONSULTAS_ACTIVAS}}
        ])
        resultado = db[CONSULTAS_HISTORIAL].delete_one({"_id": id})
        if (resultado.deleted_count != 1):
            return None
         
        consulta_activa = get_consulta(id)

    except Exception as _:
        return None
    return consulta_activa



def update_prioridad(id: str, prioridad: dict):
    update = [{
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
    resultado = update_consulta(id, CONSULTAS_ACTIVAS, update)

    if (not resultado or resultado.matched_count == 0):
        return None
    consulta_actualizada = get_consulta(id)
    return consulta_actualizada



def update_datos_medicos(id: str, datos_medicos: dict):

    examen_fisico = datos_medicos["examen_fisico"]    
    update = [{
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
    resultado = update_consulta(id, CONSULTAS_ACTIVAS, update)

    if (not resultado or resultado.matched_count == 0):
        return None
    consulta_actualizada = get_consulta(id)
    return consulta_actualizada