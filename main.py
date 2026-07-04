from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import datetime

# Drivers
import psycopg2
import pymysql
import sqlite3
from pymongo import MongoClient

app = FastAPI(
    title="DB Audit & Monitoring Skill API",
    version="1.0.0",
    description="API REST para administrar, auditar y monitorear bases de datos."
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class ConnectionDetails(BaseModel):
    host: Optional[str] = "localhost"
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: str

class ConnectionRequest(BaseModel):
    engine: str
    connection: ConnectionDetails

class RollbackRequest(BaseModel):
    log_id: str

# Función auxiliar para conectar a la BD
def get_db_connection(engine: str, conn_details: Optional[ConnectionDetails] = None):
    # Si no se pasan detalles, usar variables de entorno (útil para despliegues)
    if not conn_details:
        engine = os.getenv("DB_ENGINE", engine)
        conn_details = ConnectionDetails(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)) if os.getenv("DB_PORT") else None,
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASS", ""),
            database=os.getenv("DB_NAME", "postgres")
        )

    try:
        if engine.lower() in ["postgresql", "postgres"]:
            return psycopg2.connect(
                host=conn_details.host,
                port=conn_details.port or 5432,
                user=conn_details.user,
                password=conn_details.password,
                dbname=conn_details.database
            )
        elif engine.lower() == "mysql":
            return pymysql.connect(
                host=conn_details.host,
                port=conn_details.port or 3306,
                user=conn_details.user,
                password=conn_details.password,
                database=conn_details.database,
                cursorclass=pymysql.cursors.DictCursor
            )
        elif engine.lower() == "sqlite":
            # Para SQLite, 'database' es la ruta al archivo
            conn = sqlite3.connect(conn_details.database)
            conn.row_factory = sqlite3.Row
            return conn
        elif engine.lower() == "mongodb":
            if conn_details.host and conn_details.host.startswith(("mongodb://", "mongodb+srv://")):
                uri = conn_details.host
            else:
                uri = f"mongodb://{conn_details.user}:{conn_details.password}@{conn_details.host}:{conn_details.port or 27017}/"
                if not conn_details.user:
                    uri = f"mongodb://{conn_details.host}:{conn_details.port or 27017}/"
            client = MongoClient(uri)
            return client[conn_details.database]
        else:
            raise ValueError(f"Motor no soportado: {engine}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error conectando a la BD: {str(e)}")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "db-audit-skill", "version": "1.0.0"}

@app.post("/api/v1/connections")
def configure_connection(req: ConnectionRequest):
    # Intentar conectar
    conn = get_db_connection(req.engine, req.connection)
    
    # Aquí se inyectarían los triggers (simplificado para la API)
    # Ejemplo: leer sql_scripts/core_auditoria.sql y ejecutarlo
    
    if req.engine.lower() != "mongodb":
        conn.close()
        
    return {
        "success": True, 
        "message": f"Conexión exitosa a {req.engine} y lista para auditar."
    }

@app.get("/api/v1/logs")
def get_logs(
    engine: str = "postgresql", 
    operation: Optional[str] = None, 
    limit: int = 50,
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None
):
    try:
        if host or database:
            conn_details = ConnectionDetails(
                host=host or "localhost",
                port=port,
                user=user,
                password=password,
                database=database or ""
            )
        else:
            conn_details = None
            
        conn = get_db_connection(engine, conn_details)
        logs = []
        
        # Mapear operacion de la API a la BD
        db_operation = None
        if operation:
            op_map = {"INSERT": "I", "UPDATE": "U", "DELETE": "D"}
            db_operation = op_map.get(operation.upper(), operation)
        
        if engine.lower() == "mongodb":
            col = conn["AUDITORIA_LOGS"]
            query = {}
            if db_operation:
                query["operacion"] = db_operation
            cursor = col.find(query).sort("fecha_hora", -1).limit(limit)
            for doc in cursor:
                doc["id"] = str(doc.pop("_id", ""))
                logs.append(doc)
        else:
            cursor = conn.cursor()
            query = "SELECT * FROM AUDITORIA_LOGS"
            params = []
            if db_operation:
                query += " WHERE operacion = %s" if engine.lower() != "sqlite" else " WHERE operacion = ?"
                params.append(db_operation)
            
            query += " ORDER BY fecha_hora DESC LIMIT %s" if engine.lower() != "sqlite" else " ORDER BY fecha_hora DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            
            # Obtener nombres de columnas
            if engine.lower() == "postgresql":
                colnames = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                for row in rows:
                    logs.append(dict(zip(colnames, row)))
            elif engine.lower() == "sqlite":
                rows = cursor.fetchall()
                for row in rows:
                    logs.append(dict(row))
            elif engine.lower() == "mysql":
                logs = cursor.fetchall() # Ya es un dict por el DictCursor
                
            cursor.close()
            if engine.lower() != "mongodb":
                conn.close()
            
        # Estandarizar la respuesta de la BD a la API
        mapped_logs = []
        reverse_op_map = {"I": "INSERT", "U": "UPDATE", "D": "DELETE"}
        
        for row in logs:
            mapped_logs.append({
                "id": str(row.get("id", row.get("log_id"))),
                "timestamp": row.get("fecha_hora"),
                "engine": engine,
                "table": row.get("tabla_nombre"),
                "operation": reverse_op_map.get(row.get("operacion"), row.get("operacion")),
                "old_data": row.get("valores_old"),
                "new_data": row.get("valores_new"),
                "user": row.get("usuario_bd")
            })
            
        return {"success": True, "count": len(mapped_logs), "logs": mapped_logs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/rollback")
def generate_rollback(req: RollbackRequest):
    # Lógica simplificada de generación de rollback
    return {
        "success": True,
        "rollback_script": f"-- Script de reversión generado para log {req.log_id}\n-- (Implementación dependiente del log exacto)"
    }

@app.get("/api/v1/metrics")
def get_metrics():
    # Retorna métricas globales (ejemplo)
    return {
        "success": True,
        "total_operations": 150,
        "operations_by_engine": {
            "postgresql": 100,
            "mysql": 20,
            "sqlite": 10,
            "mongodb": 20
        }
    }
