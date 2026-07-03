# DB Audit & Monitoring Skill

## Descripción

Skill reutilizable para administrar, auditar, monitorear y generar scripts de reversión (rollback) para bases de datos relacionales y no relacionales desde sistemas externos mediante una API REST pública.

Esta Skill expone el núcleo (core) del sistema de auditoría del proyecto como una capacidad consumible por otros microservicios, extensiones de IDE, bots de alertas, paneles externos y aplicaciones, sin depender de la interfaz web principal de Streamlit.

## Objetivo

Permitir que otros proyectos o agentes se conecten dinámicamente a diferentes motores de bases de datos, inyecten la lógica de auditoría (triggers o listeners) y consulten los logs de operaciones (Insert, Update, Delete) de forma estandarizada y segura.

## Casos de uso

- Alertas en tiempo real mediante bots (ej. Slack, Discord) cuando ocurre una operación de `DELETE` crítica.
- Paneles de monitoreo externos que consolidan logs de múltiples sistemas.
- Extensiones de editores (VS Code) o IDEs para ver el impacto de las consultas SQL y deshacer cambios rápidamente (Rollback).
- Integración con otras Skills académicas (ej. validador de sintaxis puede enviar una consulta y usar esta Skill para ver qué tablas fueron afectadas realmente).
- Servicios web que requieren un historial de auditoría centralizado.

## Entradas Principales

Para configurar y auditar una base de datos, se usa JSON:

```json
{
  "engine": "postgresql",
  "connection": {
    "host": "localhost",
    "port": 5432,
    "user": "admin",
    "password": "password",
    "database": "tienda_db"
  }
}
```

Para obtener logs de auditoría, se usa una petición GET con parámetros:

```http
GET /api/v1/logs?engine=postgresql&operation=DELETE&limit=10
```

## Salidas

La salida de los logs de auditoría tiene este formato:

```json
{
  "success": true,
  "count": 1,
  "logs": [
    {
      "id": "1001",
      "timestamp": "2026-07-03T10:15:30Z",
      "engine": "postgresql",
      "table": "empleados",
      "operation": "DELETE",
      "old_data": { "id": 5, "nombre": "Juan", "cargo": "Ventas" },
      "new_data": null,
      "user": "app_user"
    }
  ]
}
```

Para la generación de Rollback:

```json
{
  "success": true,
  "rollback_script": "INSERT INTO empleados (id, nombre, cargo) VALUES (5, 'Juan', 'Ventas');"
}
```

## Motores soportados

- PostgreSQL
- MySQL
- SQLite
- MongoDB (vía Change Streams)

## Endpoints de la API

- `POST /api/v1/connections`: Configura una base de datos y despliega el núcleo de auditoría (triggers).
- `GET /api/v1/logs`: Recupera los registros de auditoría recientes.
- `POST /api/v1/rollback`: Genera un script SQL o comando NoSQL para revertir una transacción específica basada en su log.
- `GET /api/v1/metrics`: Devuelve estadísticas de uso (cantidad de operaciones por motor).

## Ejemplos de integración

### Conexión e Inyección de Auditoría HTTP

```bash
curl -X POST http://TU_API_URL/api/v1/connections \
  -H "Content-Type: application/json" \
  -d '{
    "engine": "mysql",
    "connection": {
      "host": "db.ejemplo.com",
      "user": "root",
      "password": "pwd",
      "database": "produccion"
    }
  }'
```

### Consultar Logs Recientes desde JavaScript

```js
async function getRecentDeletes() {
  const response = await fetch('https://TU_API_URL/api/v1/logs?operation=DELETE&limit=5', {
    method: 'GET'
  });
  return response.json();
}
```

## Limitaciones y Consideraciones para Streamlit Cloud

- **Importante:** Streamlit Cloud está diseñado exclusivamente para servir interfaces web con Streamlit. No permite exponer una API REST tradicional (Express, FastAPI, Flask) en puertos paralelos de manera persistente o escalable.
- Para habilitar esta API REST, deberás desplegar el núcleo (`utils/database.py` y `sql_scripts`) en un servicio Backend separado, como **Render, Railway o AWS**, utilizando un framework como **FastAPI** o **Flask**.
- Tu aplicación Streamlit luego puede actuar como un cliente más de esta API, o bien mantener el acceso directo a la base de datos mientras los sistemas externos consumen la API.

## Versionado

La API está versionada bajo `/api/v1`.
Cualquier cambio estructural en la respuesta de logs o configuración de conexión debe publicarse como `/api/v2`.

## Seguridad

- Todas las solicitudes de configuración de base de datos (`/api/v1/connections`) deben enviar un Token de Autorización o API Key, dependiendo de la implementación.
- Nunca devolver las contraseñas de las bases de datos en las respuestas GET.
- Los logs pueden contener información sensible (PII) en los campos `old_data` y `new_data`. Manejar con cuidado y asegurar los endpoints.
