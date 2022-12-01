import json
from pydantic import BaseModel, ValidationError, validator, Field
from fastapi.encoders import jsonable_encoder
from datetime import date, time, datetime
from typing import Optional, List, Literal
from bson import ObjectId


with open("triage.json") as triage_json:
    triage = json.load(triage_json)["triage"]

niveles_prioridad = [int(nivel) for nivel in triage.keys()]

NIVEL_PRIORIDAD_ADMISION = sorted(niveles_prioridad)[0]


def now() -> str:
    return datetime.now().strftime("%H:%M")


def json_dict(obj: dict | list[dict]) -> dict | list[dict]:
    return jsonable_encoder(obj, custom_encoder=ConsultaModel.Config.json_encoders)


"""
convierte ObjectIds antes de ser almacenado como _id.
"""
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid Objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class DatosPacienteModel(BaseModel):
    dni: int = Field(...)
    nombre: str = Field(...)
    apellido: str = Field(...)
    edad: int = Field(...)
    domicilio: str = Field(...)
    obra_social: str | None = None
    numero_afiliado: str | None = None
    motivo_consulta: str = Field(...)

    class Config:
        schema_extra = {
            "example": {
                "dni": 12345678,
                "nombre": "Juan",
                "apellido": "Perez",
                "edad": 30,
                "domicilio": "San Martin 550",
                "obra_social": "IPROSS",
                "numero_afiliado": 12345,
                "motivo_consulta": "Dolor de cabeza"                
            }
        }


class EstadoAtendidoModel(BaseModel):
    atendido: bool = False
    hora: datetime | None = None

    @validator("hora", always=True)
    def set_hora(cls, value, values):    
        return now() if values["atendido"] else None

    class Config:
        schema_extra = {
            "example": {
                "atendido": True
            }
        }


class PrioridadModel(BaseModel):
    nivel: int = NIVEL_PRIORIDAD_ADMISION
    tiempo_espera: str = triage[str(NIVEL_PRIORIDAD_ADMISION)]["tiempo_espera"]
    hora: datetime | None = None

    @validator("nivel")
    def nivel_valido(cls, nivel):
        if nivel not in niveles_prioridad:
            raise ValueError('Nivel de prioridad asignado no válido')
        return nivel

    @validator("tiempo_espera", always=True)
    def set_tiempo_espera(cls, value, values):
        return triage[str(values["nivel"])]["tiempo_espera"]

    @validator("hora", always=True)
    def set_hora(cls, value, values):
        return now() if values["nivel"] > NIVEL_PRIORIDAD_ADMISION else None

    class Config:
        schema_extra = {
            "example": {
                "nivel": 3
            }
        }
        

class SignosVitalesModel(BaseModel):
    ta_s: int | None = None
    ta_d: int | None = None
    fc: int | None = None
    fr: int | None = None
    t: float | None = None
    sat: int | None = None
    normal: bool = False  # Analisis de normalidad/alteración de los signos vitales. True = OK

    @validator("normal", always=True)
    def check_signos_vitales(cls, value, values):
        return (not None in values.values() and
            (100 <= values["ta_s"] <= 140) and 
            (60 <= values["ta_d"] <= 90) and 
            (60 <= values["fc"] <= 100) and 
            (8 <= values["fr"] <= 16) and 
            (values["t"] <= 38.0) and 
            (values["sat"] >= 95)
        )

class ExamenFisicoModel(BaseModel):
    examen: str | None = None
    hora: datetime | None = None

    @validator("hora", always=True)
    def set_hora(cls, value, values):
        return now() if (values["examen"] is not None and not values["examen"].isspace()) else None


class DatosMedicosModel(BaseModel):
    signos_vitales: SignosVitalesModel = Field(default_factory=SignosVitalesModel)
    anamnesis_enfermeria: str | None = None
    examen_fisico: ExamenFisicoModel = Field(default_factory=ExamenFisicoModel)
    medicacion: str | None = None

    class Config:
        schema_extra = {
            "example": {
                "signos_vitales": {
                    "ta_s": 120,
                    "ta_d": 80,
                    "fc": 70,
                    "fr": 12,
                    "t": 37,
                    "sat": 100
                },
                "examen_fisico": {
                    "examen": "Examen fisico"
                },
                "anamnesis_enfermeria": "Anamnesis de enfermeria",
                "medicacion": "Medicacion"
            }
        }


class ConsultaModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    datos_paciente: DatosPacienteModel = Field(...)
    fecha_hora_admision: datetime = Field(default_factory=datetime.now)
    fecha_hora_atencion: datetime | None = None
    prioridad: PrioridadModel = Field(default_factory=PrioridadModel)
    datos_medicos: DatosMedicosModel = Field(default_factory=DatosMedicosModel)
 
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "datos_paciente": {
                    "dni": 12345678,
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "edad": 30,
                    "domicilio": "San Martin 550",
                    "obra_social": "IPROSS",
                    "numero_afiliado": 12345,
                    "motivo_consulta": "Dolor de cabeza"
                }
            }
        }

