# GitHub Actions: despliegue del bundle de Databricks en DEV

## Objetivo

Al hacer merge a `main` (que genera un `push` a esa rama), GitHub Actions debe ejecutar:

```sh
databricks bundle validate --target dev
databricks bundle deploy --target dev
```

El workflow también conserva `workflow_dispatch` para lanzarlo manualmente.

## Qué se revisó y por qué

1. Se leyó `.github/workflows/deploy-databricks-dev.yml`, la configuración `databricks.yml`, `resources/snapshots_job.yml`, `README.md` y `.gitignore`.
2. El primer error era que `databricks/setup-cli@v0.9.0` no corresponde a una versión publicada de esa GitHub Action. Se actualizó a `databricks/setup-cli@v1.25.0`.
3. El workflow original referenciaba `DATABRICKS_HOST` y `DATABRICKS_TOKEN`, pero no existían en GitHub. Además, no se sabía quién creó ese token ni a qué identidad pertenecía. Se creó el service principal dedicado `github-actions-databricks-dev` y se eligió OAuth M2M para automatización.
4. Se indicó generar un OAuth secret con los scopes `jobs` y `workspace`: el primero cubre las operaciones de jobs y el segundo las operaciones del workspace que usa el bundle para subir notebooks. No se recomendó `all-apis`. El primer secreto se compartió por error en el chat; se indicó revocarlo y generar otro, pero no se pudo verificar la rotación.
5. Se intentó configurar GitHub OIDC, que evitaría almacenar un secreto, pero requiere una política a nivel de cuenta. El ID que se obtuvo de Azure (`7405608924183594`) es el ID del workspace, no el Account ID de Databricks. La operación account-level no pudo completarse, así que se continuó con OAuth M2M.
6. En GitHub se añadieron los repository secrets `DATABRICKS_CLIENT_ID` y `DATABRICKS_CLIENT_SECRET`.
7. Tras el error de Actions se comprobó que el cambio de workflow seguía solo en la copia local; los refs remotos todavía tenían `v0.9.0`. Se creó la rama `fix/databricks-dev-deploy` basada en el `origin/main` actualizado para preparar una PR con el workflow y este documento.

> **Credenciales:** este documento no contiene secretos ni tokens. Un secreto OAuth se compartió accidentalmente en el chat durante la configuración; se indicó revocarlo y generar uno nuevo. No se pudo verificar desde esta sesión que el anterior se haya revocado ni inspeccionar los valores guardados en GitHub. El secreto compartido no debe usarse.

## Configuración actual del workflow

En `.github/workflows/deploy-databricks-dev.yml`:

- `DATABRICKS_HOST` apunta al workspace DEV: `https://adb-7405608924183594.14.azuredatabricks.net`.
- `DATABRICKS_AUTH_TYPE` es `oauth-m2m`.
- `DATABRICKS_CLIENT_ID` y `DATABRICKS_CLIENT_SECRET` se leen desde GitHub Actions secrets.
- La CLI se instala con `databricks/setup-cli@v1.25.0`.
- Se ejecutan `bundle validate` y luego `bundle deploy` para el target `dev`.

No se modificó el trigger: `push` a `main` ejecuta el workflow después de un merge; `workflow_dispatch` permite iniciarlo manualmente.

## Pasos hechos en las interfaces

### Databricks

1. En Settings → Identity and access → Service principals se creó `github-actions-databricks-dev` como Databricks-managed.
2. Se recomendó habilitar Workspace access y mantener Admin access apagado; Consumer access no era necesario y Databricks SQL access podía quedar apagado para el job descrito. No se pudo verificar después qué toggles quedaron finalmente habilitados.
3. Se indicó generar un OAuth secret con scopes `jobs` y `workspace`, y duración recomendada de 90 días. El primer secreto generado se compartió por error; se indicó revocarlo y reemplazarlo.

El Application ID del service principal es un identificador, no el secreto OAuth. El secreto solo se muestra al generarlo; no debe pegarse en el repositorio ni en el chat.

### GitHub

En `AdrianAsenjo/databricks` → Settings → Secrets and variables → Actions se añadieron estos repository secrets:

- `DATABRICKS_CLIENT_ID`
- `DATABRICKS_CLIENT_SECRET`

La captura compartida confirmó que esos nombres aparecen en GitHub, pero no permite comprobar sus valores. El `DATABRICKS_HOST` se define directamente en el workflow porque no es confidencial.

## Comandos de consola ejecutados

Los comandos se ejecutaron en PowerShell desde la raíz local del repositorio. Se omiten valores de credenciales y datos personales de la salida.

### Inspección del repositorio

```powershell
Get-Content -Raw .github/workflows/deploy-databricks-dev.yml
Get-ChildItem -Force
rg -n "setup-cli|DATABRICKS_(HOST|TOKEN)|service.principal|run_as|targets:|bundle:" .github databricks.yml databricks

Get-Content -Raw databricks.yml
Get-Content -Raw README.md
Get-Content -Raw .gitignore
git status --short --branch

Get-Content -Raw resources/snapshots_job.yml
Get-ChildItem -Force .github/workflows | Select-Object Name,Length

Get-Command databricks -ErrorAction SilentlyContinue
Get-Command gh -ErrorAction SilentlyContinue
rg --files -g AGENTS.md -g '!**/.git/**' C:\Users\asenj\Documents\git
```

**Por qué:** comprobar el workflow, el target `dev`, el job, los triggers, los comandos disponibles y el estado de Git. Se encontró Databricks CLI instalado y GitHub CLI no instalado.

### Diagnóstico y autenticación de Databricks CLI

```powershell
databricks auth profiles
databricks auth login --help
databricks auth login --host https://accounts.azuredatabricks.net --skip-workspace --profile github-oidc-setup
databricks auth login --host https://accounts.azuredatabricks.net --account-id 7405608924183594 --skip-workspace --profile github-account-setup
databricks auth login --skip-workspace --profile github-oidc-setup
databricks auth profiles
databricks auth login --host https://adb-7405608924183594.14.azuredatabricks.net --profile github-oidc-setup
databricks auth profiles
databricks current-user me --profile github-oidc-setup
```

**Por qué y resultado:** al principio no había perfiles CLI válidos. El primer login a nivel de cuenta se detuvo porque faltaba un Account ID. Se intentó otra vez con el valor facilitado; no apareció un perfil de cuenta válido en `auth profiles`. Se inició sesión correctamente en el workspace DEV con el perfil `github-oidc-setup`; `auth profiles` confirmó `Valid: YES`. `current-user me` se usó para confirmar que la CLI autenticaba contra el workspace correcto. Ese perfil local es para diagnóstico y no es la identidad usada por GitHub Actions.

### Comprobación de comandos account-level para OIDC

```powershell
databricks account service-principal-federation-policy --help
databricks service-principal-federation-policy --help
databricks account service-principal-federation-policy list --help
databricks account service-principal-federation-policy list 141629894670056 --profile github-oidc-setup

$env:DATABRICKS_HOST='https://accounts.azuredatabricks.net'
$env:DATABRICKS_ACCOUNT_ID='7405608924183594'
$env:DATABRICKS_CONFIG_PROFILE='github-oidc-setup'
databricks account service-principal-federation-policy list 141629894670056

databricks account service-principal-federation-policy list 141629894670056 --host https://accounts.azuredatabricks.net --account-id 7405608924183594 --profile github-oidc-setup
```

**Por qué y resultado:** verificar si la política OIDC podía administrarse con los datos disponibles. El intento con el valor de `workspaceId` devolvió `Unable to find AccountId from request`; pasar `--host` al subcomando `list` dio `unknown flag`. El service principal numérico de la ruta de Databricks es `141629894670056`. No se creó una política OIDC.

### Preparación de la nueva PR

```powershell
git fetch origin
git -c http.sslBackend=schannel fetch origin
git status --short --branch
git log --oneline --decorate -4 origin/main
git config user.name
git config user.email
git switch -c fix/databricks-dev-deploy origin/main
```

**Por qué y resultado:** el primer `git fetch` falló al validar el certificado SSL de GitHub. Se reintentó con el backend de certificados de Windows (`schannel`), manteniendo la validación TLS; ese fetch funcionó. Se comprobó que la copia local de `main` iba dos commits por detrás y se creó `fix/databricks-dev-deploy` desde el `origin/main` actualizado, conservando el workflow y este documento para preparar la PR.
### Archivo actualizado

Se escribió `.github/workflows/deploy-databricks-dev.yml` con estas variables de autenticación:

```yaml
DATABRICKS_HOST: https://adb-7405608924183594.14.azuredatabricks.net
DATABRICKS_AUTH_TYPE: oauth-m2m
DATABRICKS_CLIENT_ID: ${{ secrets.DATABRICKS_CLIENT_ID }}
DATABRICKS_CLIENT_SECRET: ${{ secrets.DATABRICKS_CLIENT_SECRET }}
```

También se cambió la acción de instalación de CLI a `databricks/setup-cli@v1.25.0`. Se añadió el salto de línea final del archivo. La escritura se hizo con `[System.IO.File]::WriteAllText(...)` usando UTF-8 sin BOM y después `[System.IO.File]::AppendAllText(...)` para el salto de línea.

Después se ejecutó:

```powershell
git diff -- .github/workflows/deploy-databricks-dev.yml
git status --short
```

**Por qué:** revisar el cambio y confirmar que el workflow era el único archivo modificado. En la primera revisión, antes de preparar la PR, el cambio estaba local y sin commit ni push. No se ejecutó `bundle validate`, `bundle deploy` ni otro test desde esta sesión.

## Qué falta para probar

1. Confirmar que el OAuth secret compartido por error quedó revocado y que el valor actual de `DATABRICKS_CLIENT_SECRET` en GitHub es el nuevo secreto.
2. Completar el commit y push de la rama `fix/databricks-dev-deploy`, y crear la PR. Después del merge a `main`, el trigger `push` ejecutará el workflow.
3. Revisar el run en la pestaña Actions. Si falla por autorización, conceder al service principal los permisos de workspace/job y permisos Unity Catalog que requiera el job; los scopes OAuth limitan las APIs disponibles, pero no conceden permisos sobre los recursos de Databricks.

## Referencias oficiales

- [OAuth M2M para service principals](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/oauth-m2m)
- [Scopes de API de Databricks](https://docs.databricks.com/api/workspace/scopes)
- [Acción `databricks/setup-cli`](https://github.com/databricks/setup-cli)
- [Federación OIDC para GitHub Actions](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/provider-github)