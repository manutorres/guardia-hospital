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
    return JSONResponse(status_code=status.HTTP_200_OK, content=consultas)


@app.post("/", response_description="Crea una nueva consulta", response_model=ConsultaModel)
def create_consulta(datos_paciente: DatosPacienteModel):
    consulta_model = ConsultaModel(datos_paciente)
    consulta = jsonable_encoder(consulta_model)
    nueva_consulta = db.create_consulta(consulta)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=nueva_consulta)


@app.put("/paciente/{consulta_id}", response_description="Edita los datos de ingreso a consulta del paciente", response_model=DatosPacienteModel)
def update_datos_paciente(consulta_id: str, datos_paciente: DatosPacienteModel):
    datos_paciente = jsonable_encoder(datos_paciente) 
    consulta_actualizada = db.update_datos_paciente(consulta_id, datos_paciente)
    if not consulta_actualizada:
        raise HTTPException(status_code=404, detail=f"Consulta {consulta_id} no encontrada")

    return JSONResponse(status_code=status.HTTP_200_OK, content=consulta_actualizada)


@app.put("/atendido/{consulta_id}", response_description="Edita el estado de atendido del paciente", response_model=EstadoAtendidoModel)
def update_estado_atendido(consulta_id: str, estado_atendido_model: EstadoAtendidoModel):
    if estado_atendido_model.atendido:
        estado_atendido_model.set_hora()
    estado_atendido = jsonable_encoder(estado_atendido_model)
    consulta_actualizada = db.update_estado_atendido(consulta_id, estado_atendido)
    if not consulta_actualizada:
        raise HTTPException(status_code=404, detail=f"Consulta {consulta_id} no encontrada")

    return JSONResponse(status_code=status.HTTP_200_OK, content=consulta_actualizada)


@app.put("/prioridad/{consulta_id}", response_description="Edita la prioridad triage asociada a la consulta", response_model=PrioridadModel)
def update_prioridad(consulta_id: str, prioridad_model: PrioridadModel):   
    if prioridad_model.nivel > NIVEL_PRIORIDAD_INICIAL:
        prioridad_model.set_hora()
    prioridad = jsonable_encoder(prioridad_model)
    consulta_actualizada = db.update_prioridad(consulta_id, prioridad)
    if not consulta_actualizada:
        raise HTTPException(status_code=404, detail=f"Consulta {consulta_id} no encontrada")

    return JSONResponse(status_code=status.HTTP_200_OK, content=consulta_actualizada)


@app.put("/datosmedicos/{consulta_id}", response_description="Edita los datos medicos del paciente", response_model=DatosMedicosModel)
def update_datos_medicos(consulta_id: str, datos_medicos: DatosMedicosModel):    
    examen = datos_medicos.examen_fisico.examen
    if (examen and not examen.isspace()):
        datos_medicos.examen_fisico.set_hora()    
    
    datos_medicos = jsonable_encoder(datos_medicos)
    consulta_actualizada = db.update_datos_medicos(consulta_id, datos_medicos)
    if not consulta_actualizada:
        raise HTTPException(status_code=404, detail=f"Consulta {consulta_id} no encontrada")

    return JSONResponse(status_code=status.HTTP_200_OK, content=consulta_actualizada)