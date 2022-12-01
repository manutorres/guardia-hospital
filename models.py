import json
from pydantic import BaseModel, ValidationError, validator, Field
from fastapi.encoders import jsonable_encoder
from datetime import date, time, datetime
from typing import Optional, List, Literal
from bson import ObjectId


with open("triage.json") as triage_file:
    triage_json = json.load(triage_file)

niveles_prioridad = [int(prioridad["nivel"]) for prioridad in triage_json["triage"]]

NIVEL_PRIORIDAD_INGRESO = sorted(niveles_prioridad)[0]


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

    def set_hora(self):
        # self.hora = datetime.today().strftime("%H:%M") if self.atendido else None
        self.hora = now() if self.atendido else None

    class Config:
        schema_extra = {
            "example": {
                "atendido": True
            }
        }


class PrioridadModel(BaseModel):
    nivel: int = NIVEL_PRIORIDAD_INGRESO
    hora: datetime | None = None

    def set_hora(self):
        self.hora = now() if self.nivel > NIVEL_PRIORIDAD_INGRESO else None

    @validator('nivel')
    def nivel_valido(cls, nivel):
        if nivel not in niveles_prioridad:
            raise ValueError('Nivel de prioridad asignado no válido')
        return nivel

    class Config:
        schema_extra = {
            "example": {
                "nivel": 3
            }
        }
        

class SignosVitalesModel(BaseModel):
    ta_s: int = Field(...)
    ta_d: int = Field(...)
    fc: int = Field(...)
    fr: int = Field(...)
    t: float = Field(...)
    sat: int = Field(...)
    normal: bool = True  # Analisis de normalidad/alteración de los signos vitales. True = OK

    @validator("normal", always=True)
    def check_signos_vitales(cls, value, values):
        return ((100 <= values["ta_s"] <= 140) and (60 <= values["ta_d"] <= 90) and 
            (60 <= values["fc"] <= 100) and (8 <= values["fr"] <= 16) and 
            (values["t"] <= 38.0) and (values["sat"] >= 95)
        )

class ExamenFisicoModel(BaseModel):
    examen: str | None = None
    hora: datetime | None = None

    def set_hora(self):
        self.hora = now() if (self.examen and not self.examen.isspace()) else None


class DatosMedicosModel(BaseModel):
    signos_vitales: SignosVitalesModel | None = None
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

    # def __init__(self, datos_paciente):
    #     dia_hora_actual = datetime.today()
    #     data = {}
    #     data["datos_paciente"] = datos_paciente        
    #     data["dia_admision"] = dia_hora_actual.strftime("%Y-%m-%d")
    #     data["hora_admision"] = dia_hora_actual.strftime("%H:%M")
    #     data["fecha_hora_admision"] = datetime.utcnow()
    #     data["estado_atendido"] = EstadoAtendidoModel()
    #     data["prioridad"] = PrioridadModel()
    #     data["datos_medicos"] = DatosMedicosModel(examen_fisico=ExamenFisicoModel())
    #     super().__init__(**data)

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

