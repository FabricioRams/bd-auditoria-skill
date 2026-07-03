# Automated DB Rollback Action

Esta es una **GitHub Action personalizada** desarrollada como parte del sistema de *Auditoría de Bases de Datos*. Permite a cualquier equipo de desarrollo revertir operaciones peligrosas (como un `DELETE` accidental) directamente desde GitHub, sin tocar código.

## ¿Cómo funciona?

1. Un desarrollador ejecuta esta Action desde la pestaña "Actions" de su repositorio, ingresando el **Log ID** del error.
2. La Action se comunica con la API de auditoría alojada en Railway (`/api/v1/rollback`).
3. La API genera el script SQL exacto para deshacer el error (ej: el `INSERT` de los datos borrados).
4. La Action crea un nuevo archivo `.sql` y abre automáticamente un **Pull Request** para que el equipo lo revise antes de ejecutarlo.

## ¿Cómo instalarlo en tu repositorio?

Si eres de otro grupo y quieres usar esta automatización en tu proyecto, solo debes crear un archivo llamado `.github/workflows/db_rollback.yml` en tu repositorio y pegar el siguiente código:

```yaml
name: "Reversión de Base de Datos"

# Esto permite que la Action se ejecute manualmente con un botón
on:
  workflow_dispatch:
    inputs:
      log_id:
        description: 'Ingresa el ID del log a revertir (ej. 1001)'
        required: true
        type: string

jobs:
  generar-rollback:
    runs-on: ubuntu-latest
    
    # Necesitamos permisos para crear el Pull Request
    permissions:
      contents: write
      pull-requests: write

    steps:
      - name: Descargar el código del repositorio
        uses: actions/checkout@v4

      - name: Ejecutar BD Auditoria Rollback Skill
        uses: tu-usuario/bd-auditoria-skill/github_action_rollback@main
        with:
          log_id: ${{ github.event.inputs.log_id }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          # api_url: 'Opcional si cambiaste la URL de Railway'
```

*Nota: Asegúrate de cambiar `tu-usuario` por el usuario real de GitHub donde subas este repositorio.*
