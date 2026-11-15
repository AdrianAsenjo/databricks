# Despliegue del bundle de Databricks en DEV

## Estado actual

GitHub Actions valida y despliega el bundle al hacer `push` a `main` (por ejemplo, después de integrar una PR). También se puede iniciar manualmente con `workflow_dispatch`.

El despliegue ya se verificó en el workspace. El job de CI creó estos dos jobs:

- `dim_sanps` — job ID `956372568357097`.
- `snapshots append` — job ID `724545435981457`.

Los jobs aparecen en **Jobs & Pipelines** con un prefijo del entorno y del service principal. El despliegue crea/actualiza la definición del job; no lo ejecuta. Para ejecutar el notebook, abrir el job en Databricks y pulsar **Run now**.

## Configuración del workflow

Archivo: `.github/workflows/deploy-databricks-dev.yml`.

- Acción de instalación: `databricks/setup-cli@v1.25.0`.
- Host: `https://adb-7405608924183594.14.azuredatabricks.net`.
- Autenticación: OAuth M2M mediante el service principal `github-actions-databricks-dev`.
- GitHub Actions secrets requeridos: `DATABRICKS_CLIENT_ID` y `DATABRICKS_CLIENT_SECRET`.
- Pasos: `databricks bundle validate --target dev` y `databricks bundle deploy --target dev`.

No hay trigger `pull_request`: una actualización de rama de PR no lanza este workflow. Se ejecuta al llegar un `push` a `main`, o manualmente desde Actions.

## Service principal y credenciales

Para CI se usa un service principal **Databricks managed**, no una identidad personal.

Permisos recomendados en **Settings → Identity and access → Service principals**:

- Workspace access: **On**.
- Admin access: **Off**.
- Consumer access: **Off**, salvo que se necesite consumir dashboards/apps compartidos.
- Databricks SQL access: **Off**, salvo que el job use funciones de Databricks SQL/SQL warehouses que lo requieran.

El job también necesita los permisos de datos pertinentes en Unity Catalog. Para el job de snapshots, comprobar `USE CATALOG` en `datafact`, `USE SCHEMA` en `data_model`, y permisos para crear e insertar en la tabla. Los toggles de entitlements no conceden por sí solos permisos sobre tablas y esquemas.

### OAuth M2M y scopes

El Databricks CLI solicita `all-apis` por defecto al usar OAuth M2M. Un secreto limitado a los scopes `jobs` y `workspace` falló con `access_denied`, porque el token solicitado excedía esos scopes. Para mantener el CLI estándar se generó un OAuth secret con **All APIs**. Esto no da Admin access: el token solo puede ejecutar las operaciones para las que el service principal tenga permisos en Databricks.

Los valores `DATABRICKS_CLIENT_ID` y `DATABRICKS_CLIENT_SECRET` de GitHub deben formar un par de la misma identidad. Si se elimina y recrea el service principal, cambia el Application ID: hay que actualizar ambos secrets con las credenciales nuevas. `invalid_client` indica que Databricks no acepta ese par; no es un error de scopes.

El secreto OAuth se compartió accidentalmente en el chat durante la configuración. No se incluye aquí; debe estar revocado y no debe usarse. GitHub oculta los valores guardados, así que si hay dudas se debe generar un secreto nuevo y reemplazar ambos secrets en GitHub. No pegues credenciales en el chat ni en el repositorio.

Para guardarlos en GitHub: `AdrianAsenjo/databricks` → **Settings → Secrets and variables → Actions → New repository secret**. El secreto OAuth se guarda como `DATABRICKS_CLIENT_SECRET`; el Application ID correspondiente, como `DATABRICKS_CLIENT_ID`. El host no es secreto y está definido en el workflow.

## Configuración del bundle

`databricks.yml` incluye `resources/*.yml`, por lo que todos esos YAML se cargan como recursos del bundle.

- `resources/snapshots_job.yml` define el job con la clave `snapshots_job` y usa `src/snapshots.py`.
- `resources/dim_sanps.yml` define el job con la clave única `dim_sanps_job` y usa `src/dim_sanps.ipynb`.

Las claves bajo `resources.jobs` deben ser únicas. El `notebook_path` debe coincidir con el archivo existente.

## Errores encontrados y resolución

1. `databricks/setup-cli@v0.9.0` no era una etiqueta válida de la acción. Se cambió a `@v1.25.0`.
2. La primera PR/run aún tenía el workflow antiguo porque el cambio local no se había subido. Se creó y subió una rama con el workflow actualizado.
3. `bundle validate` detectó dos recursos con la clave `snapshots_job`, definida en ambos YAML. Se renombró la clave del job de dimensión a `dim_sanps_job`.
4. Después, la validación detectó `src/dim_sanps.py` inexistente. El archivo real era `src/dim_sanps.ipynb`; se actualizó el `notebook_path`.
5. OAuth devolvió `access_denied` para `all-apis` cuando el secreto solo tenía scopes `jobs` y `workspace`. Se generó el secreto con All APIs, que es lo que solicita el CLI por defecto.
6. OAuth devolvió `invalid_client` cuando el Client ID y el secreto no coincidían o no eran de la misma identidad. Se actualizaron las credenciales de GitHub para la identidad activa; el run posterior autenticó y desplegó los jobs.
7. Al comprobar el bundle con el perfil local del usuario, `bundle summary` mostró el estado de su propio directorio `.bundle`, no el estado desplegado por CI. `databricks jobs list` confirmó los jobs creados por el service principal.

## Comandos de consola ejecutados

Se ejecutaron en PowerShell desde la raíz local del repositorio. Las credenciales y datos personales de las salidas se omiten.

### Inspección del repositorio y workflow

```powershell
Get-Content -Raw .github/workflows/deploy-databricks-dev.yml
Get-ChildItem -Force
rg -n "setup-cli|DATABRICKS_(HOST|TOKEN)|service.principal|run_as|targets:|bundle:" .github databricks.yml databricks
Get-Content -Raw databricks.yml
Get-Content -Raw README.md
Get-Content -Raw .gitignore
Get-Content -Raw resources/snapshots_job.yml
Get-Content -Raw resources/dim_sanps.yml
Get-ChildItem -Force .github/workflows | Select-Object Name,Length
Get-ChildItem resources -File | Select-Object Name,Length
Get-ChildItem src -File | Select-Object Name,Length
Get-Command databricks -ErrorAction SilentlyContinue
Get-Command gh -ErrorAction SilentlyContinue
rg --files -g AGENTS.md -g '!**/.git/**' C:\Users\asenj\Documents\git
```

**Motivo:** inspeccionar bundle, workflows, recursos, ficheros fuente, herramientas disponibles e instrucciones del repositorio.

### Autenticación y comprobaciones de OIDC

```powershell
databricks auth profiles
databricks auth login --help
databricks auth login --host https://accounts.azuredatabricks.net --skip-workspace --profile github-oidc-setup
databricks auth login --host https://accounts.azuredatabricks.net --account-id 7405608924183594 --skip-workspace --profile github-account-setup
databricks auth login --skip-workspace --profile github-oidc-setup
databricks auth login --host https://adb-7405608924183594.14.azuredatabricks.net --profile github-oidc-setup
databricks current-user me --profile github-oidc-setup
databricks account service-principal-federation-policy --help
databricks service-principal-federation-policy --help
databricks account service-principal-federation-policy list --help
databricks account service-principal-federation-policy list 141629894670056 --profile github-oidc-setup
```

El login de workspace se completó y el perfil `github-oidc-setup` quedó válido. No se creó política OIDC: el dato `7405608924183594` era `workspaceId`, no el Account ID. El comando workspace para `service-principal-federation-policy` no existe; la política es de cuenta.

También se ejecutó la comprobación con variables de entorno y con flags de cuenta; falló porque el `Account ID` no estaba disponible y el subcomando `list` no acepta `--host`:

```powershell
$env:DATABRICKS_HOST='https://accounts.azuredatabricks.net'
$env:DATABRICKS_ACCOUNT_ID='7405608924183594'
$env:DATABRICKS_CONFIG_PROFILE='github-oidc-setup'
databricks account service-principal-federation-policy list 141629894670056
databricks account service-principal-federation-policy list 141629894670056 --host https://accounts.azuredatabricks.net --account-id 7405608924183594 --profile github-oidc-setup
```

### Bundle y jobs

```powershell
databricks bundle validate --target dev
databricks bundle summary --target dev --profile github-oidc-setup
databricks jobs list --name dim_sanps --profile github-oidc-setup --output json
databricks jobs list --name snapshots --profile github-oidc-setup --output json
databricks jobs list --profile github-oidc-setup --output json
```

Los intentos de `bundle validate` mostraron primero la clave duplicada y luego la ruta `.py` inexistente. Tras corregirlas, Actions desplegó los dos jobs. `bundle summary` con el perfil personal consultaba el estado de ese usuario; el listado completo de jobs mostró los dos creados por CI bajo el service principal.

### Git y publicación de la PR

```powershell
git status --short --branch
git fetch origin
git -c http.sslBackend=schannel fetch origin
git log --oneline --decorate -4 origin/main
git switch -c fix/databricks-dev-deploy origin/main
git add .github/workflows/deploy-databricks-dev.yml GITHUB_ACTIONS_SETUP.md
git diff --cached --stat
git diff --cached -- .github/workflows/deploy-databricks-dev.yml
git commit -m "Fix Databricks dev deployment workflow"
git -c http.sslBackend=schannel push -u origin fix/databricks-dev-deploy
git commit -m "Document deployment PR commands"
git -c http.sslBackend=schannel push
```

El primer `git fetch origin` falló por la configuración local de certificados. Se reintentó con `schannel`, el backend de certificados de Windows, manteniendo validación TLS, y funcionó. La rama `fix/databricks-dev-deploy` se publicó y la PR #6 se integró en `main`.

## Operación después del deploy

1. Revisa Actions y confirma que terminaron los pasos `Validate bundle` y `Deploy bundle`.
2. En Databricks, abre **Jobs & Pipelines** y busca `dim_sanps` o `snapshots append`. Los nombres desplegados incluyen un prefijo del target y del service principal.
3. Para ejecutar el notebook y crear/escribir datos, abre el job y pulsa **Run now**. `bundle deploy` no ejecuta los jobs. También se puede ejecutar desde la raíz del repo con `databricks bundle run --target dev snapshots_job` o `databricks bundle run --target dev dim_sanps_job`.
4. Si un error OAuth vuelve a ocurrir, comprueba que `DATABRICKS_CLIENT_ID` y `DATABRICKS_CLIENT_SECRET` se generaron juntos para el service principal actualmente asignado al workspace. Nunca imprimas el secreto en los logs.

## Referencias oficiales

- [OAuth M2M, scopes y diagnóstico](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/oauth-m2m)
- [Entitlements del workspace](https://learn.microsoft.com/en-us/azure/databricks/security/auth/entitlements)
- [Scopes de API de Databricks](https://docs.databricks.com/api/workspace/scopes)
- [Acción `databricks/setup-cli`](https://github.com/databricks/setup-cli)
- [Federación OIDC para GitHub Actions](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/provider-github)
