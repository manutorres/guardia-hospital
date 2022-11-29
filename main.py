import os
import uvicorn
import db
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import List
from pydantic import ValidationError
from models import *


app = FastAPI(title="Guardia Hospital App")


@app.get("/", response_description="Lista todas las consultas", response_model=List[ConsultaModel])
def get_consultas():
    consultas = db.get_consultas()
    respuesta_json = json_dict(consultas)
    return JSONResponse(status_code=status.HTTP_200_OK, content=respuesta_json)



@app.get("/activas", response_description="Lista las consultas pendientes de atención", response_model=List[ConsultaModel])
def get_consultas_activas():
    consultas = db.get_consultas_activas()
    respuesta_json = json_dict(consultas)
    return JSONResponse(status_code=status.HTTP_200_OK, content=respuesta_json)



@app.get("/{consulta_id}", response_description="Muestra la consulta de ID {consulta_id}", response_model=ConsultaModel)
def get_consulta(consulta_id: str):
    if (consulta := db.get_consulta(consulta_id)) is None:
        raise HTTPException(status_code=404, detail=f"La consulta {consulta_id} no fue encontrada")

    respuesta_json = json_dict(consulta)
    return JSONResponse(status_code=status.HTTP_200_OK, content=respuesta_json)



@app.get("/historial/{dni}", response_description="Muestra todas las consultas registradas con DNI {dni}", response_model=List[ConsultaModel])
def get_consulta(dni: str):
    consultas = db.get_consultas_por_dni(dni)
    respuesta_json = json_dict(consultas)
    return JSONResponse(status_code=status.HTTP_200_OK, content=respuesta_json)



@app.post("/", response_description="Crea una nueva consulta", response_model=ConsultaModel)
def create_consulta(datos_paciente: DatosPacienteModel):
    consulta_model = ConsultaModel(datos_paciente=datos_paciente)
    # Envío diccionario sin encoding para poder almacenar datetime como MongoDB Date
    consulta_dict = consulta_model.dict(by_alias=True)
    nueva_consulta = db.create_consulta(consulta_dict)
    # Encoding aplicado para onvertir los campos aún no "json" del diccionario (ObjectID y datetime)
    respuesta_json = json_dict(nueva_consulta)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=respuesta_json)



@app.put("/{consulta_id}/paciente", response_description="Edita los datos de ingreso a consulta del paciente", response_model=DatosPacienteModel)
def update_datos_paciente(consulta_id: str, datos_paciente: DatosPacienteModel):
    datos_paciente = jsonable_encoder(datos_paciente) 
    consulta_actualizada = db.update_datos_paciente(consulta_id, datos_paciente)
    if not consulta_actualizada:
        raise HTTPException(status_code=404, detail=f"La consulta {consulta_id} no fue encontrada o los datos del paciente no pudieron ser actualizados")

    respuesta_json = json_dict(consulta_actualizada)
    return JSONResponse(status_code=status.HTTP_200_OK, content=respuesta_json)



@app.put("/{consulta_id}/atendida", response_description="Marca la consulta como atendida", response_model=EstadoAtendidoModel)
def set_consulta_atendida(consulta_id: str):    
    consulta_actualizada = db.set_consulta_atendida(consulta_id, datetime.now())
    if not consulta_actualizada:
        raise HTTPException(status_code=404, detail=f"La consulta {consulta_id} no fue encontrada o no pudo ser marcada como atendida")

    respuesta_json = json_dict(consulta_actualizada)
    return JSONResponse(status_code=status.HTTP_200_OK, content=respuesta_json)



@app.put("/{consulta_id}/noatendida", response_description="Devuelve la consulta a la lista de espera", response_model=EstadoAtendidoModel)
def unset_consulta_atendida(consulta_id: str):
    consulta_actualizada = db.unset_consulta_atendida(consulta_id)
    if not consulta_actualizada:
        raise HTTPException(status_code=404, detail=f"La consulta {consulta_id} no fue encontrada o no pudo ser devuelta a lista de espera")

    respuesta_json = json_dict(consulta_actualizada)
    return JSONResponse(status_code=status.HTTP_200_OK, content=respuesta_json)



@app.put("/{consulta_id}/prioridad", response_description="Edita la prioridad triage asociada a la consulta", response_model=PrioridadModel)
def update_prioridad(consulta_id: str, prioridad_model: PrioridadModel):   
    if prioridad_model.nivel > NIVEL_PRIORIDAD_INGRESO:
        prioridad_model.set_hora()
    prioridad_dict = prioridad_model.dict()
    consulta_actualizada = db.update_prioridad(consulta_id, prioridad_dict)
    if not consulta_actualizada:
        raise HTTPException(status_code=404, detail=f"La consulta {consulta_id} no fue encontrada o su prioridad no pudo ser actualizada")

    respuesta_json = json_dict(consulta_actualizada)
    return JSONResponse(status_code=status.HTTP_200_OK, content=respuesta_json)



@app.put("/{consulta_id}/datosmedicos", response_description="Edita los datos medicos del paciente", response_model=DatosMedicosModel)
def update_datos_medicos(consulta_id: str, datos_medicos: DatosMedicosModel):    
    examen = datos_medicos.examen_fisico.examen
    if (examen and not examen.isspace()):
        datos_medicos.examen_fisico.set_hora()    
    datos_medicos = jsonable_encoder(datos_medicos)
    consulta_actualizada = db.update_datos_medicos(consulta_id, datos_medicos)
    if not consulta_actualizada:
        raise HTTPException(status_code=404, detail=f"La consulta {consulta_id} no fue encontrada o sus datos médicos no pudieron ser actualizados")

    return JSONResponse(status_code=status.HTTP_200_OK, content=consulta_actualizada)