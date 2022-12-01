from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, OperationFailure
from pymongo.results import UpdateResult
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



def get_consultas(coleccion: str = CONSULTAS_ACTIVAS, filtro: dict = {}, proyeccion: list = [], orden: tuple | list[tuple] = {}):
    orden = [orden] if isinstance(orden, tuple) else orden
    cursor = db[coleccion].find(filtro, proyeccion).sort(orden)
    consultas = list(cursor)
    return consultas



def get_consulta(id: str, coleccion: str = CONSULTAS_ACTIVAS, proyeccion: list = []):
    try:
        id = ObjectId(id)
        consulta = db[coleccion].find_one({"_id": id}, proyeccion)
    except Exception:
        return None
    return consulta



def get_consultas_activas():
    activas = get_consultas(
        coleccion=CONSULTAS_ACTIVAS,
        filtro={},
        proyeccion=["fecha_hora_admision", "prioridad"],
        orden=[
            ("prioridad.nivel", DESCENDING), 
            ("fecha_hora_admision", DESCENDING)
        ]
    )
    return activas



def get_consultas_historial():
    activas = get_consultas(
        coleccion=CONSULTAS_HISTORIAL, 
        filtro={}, 
        proyeccion=["datos_paciente.dni", "fecha_hora_admision", "fecha_hora_atencion"],
        orden=("fecha_hora_admision", DESCENDING)
    )
    return activas



def get_consultas_por_dni(dni: int):
    consulta_activa = db[CONSULTAS_ACTIVAS].find_one({"datos_paciente.dni": dni}) # Consulta o None
    consultas = [consulta_activa] if consulta_activa else []
    consultas_previas = get_consultas(
        coleccion=CONSULTAS_HISTORIAL, 
        filtro={"datos_paciente.dni": dni}, 
        proyeccion=["datos_paciente.dni", "datos_paciente.domicilio", "fecha_hora_admision", "fecha_hora_atencion"],
        orden=("fecha_hora_admision", DESCENDING)
    )
    consultas.extend(consultas_previas)
    return consultas



def get_horarios(id: str, activa: bool = True):
    
    horarios = get_consulta(
        id = id,
        coleccion = CONSULTAS_ACTIVAS if activa else CONSULTAS_HISTORIAL,
        proyeccion = {
            "_id": { "$toString": "$_id"},
            "fecha_admision": { "$dateToString": { "format": "%d-%m-%Y", "date": "$fecha_hora_admision" } },
            "hora_admision": { "$dateToString": { "format": "%H-%M", "date": "$fecha_hora_admision" } },
            "hora_triage": "$prioridad.hora",
            "hora_examen_fisico": "$datos_medicos.examen_fisico.hora",
            "hora_atencion": { "$dateToString": { "format": "%H-%M", "date": "$fecha_hora_atencion" } }
        }
    )    
    
    return horarios



def create_consulta(consulta: dict):    
    resultado = db[CONSULTAS_ACTIVAS].insert_one(consulta)
    consulta_creada = get_consulta(resultado.inserted_id)
    return consulta_creada



def update_consulta(id: str, coleccion: str = CONSULTAS_ACTIVAS, update = {}) -> UpdateResult:
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
            "prioridad.tiempo_espera": prioridad["tiempo_espera"],
            "prioridad.hora": {
                "$cond": {
                    "if": {
                        "$eq": ["$prioridad.hora", None] # No recalcular hora si ya tiene prioridad asignada
                    },
                    "then": prioridad["hora"],
                    "else": "$prioridad.hora" # valor existente
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