# Pasos manuales (sin API)

Estos tres pasos **no tienen API ni soporte en `gcloud`/Terraform**. Hay que hacerlos
una vez, a mano, en la consola de Google Cloud, con el proyecto correcto seleccionado
en el selector de arriba. Son rápidos.

> Requisito previo: haber aplicado `terraform/` (APIs habilitadas).

## 1. Configuración de la Chat app

`APIs y servicios` → `Google Chat API` → pestaña **Configuración**.

- **App name:** cualquiera (p. ej. `Backup Chat`).
- **Description:** obligatoria, cualquier texto.
- **HTTP endpoint URL:** `https://localhost` (no se usará nunca; es solo un requisito del formulario).
- No hace falta marcar "Join spaces", "App Home", comandos ni visibilidad: no vamos a
  usar ningún bot, solo leer con tu cuenta.

Guarda. Sin este paso, la API devuelve error aunque esté habilitada.

## 2. Pantalla de consentimiento OAuth

`APIs y servicios` → **Pantalla de consentimiento de OAuth**.

- **Tipo de usuario:**
  - Si el proyecto pertenece a la organización de Workspace y puedes elegir **Internal**,
    es lo más cómodo (sin aviso de app sin verificar ni límite de usuarios).
  - Si no, **External** en modo **Testing**, y añade en "Usuarios de prueba" las cuentas
    que vayan a ejecutar el backup.
- **Scopes:** añade exactamente estos tres (de solo lectura):
  ```
  https://www.googleapis.com/auth/chat.spaces.readonly
  https://www.googleapis.com/auth/chat.messages.readonly
  https://www.googleapis.com/auth/chat.memberships.readonly
  ```
  (La People API usa `.../auth/directory.readonly`, que el script pide aparte solo si
  `GCHAT_RESOLVE_NAMES=true`.)

## 3. Cliente OAuth de escritorio

`APIs y servicios` → `Credenciales` → **Crear credenciales** → **ID de cliente de OAuth**
→ tipo **Aplicación de escritorio**.

- Crea y **descarga el JSON**.
- Guárdalo en la carpeta `scripts/` del repo con su nombre tal cual
  (`client_secret_...apps.googleusercontent.com.json`). El `.gitignore` ya lo excluye.

> Este tipo de cliente **no se puede crear por API ni por `gcloud`**: es obligatoriamente
> manual. Es el motivo principal por el que este paso no está en Terraform.

## Comprobación

Desde `scripts/`, con `GCHAT_DRY_RUN=true`, el script debe listar tus espacios. Si en el
login sale "Acceso bloqueado por política del administrador", la organización bloquea el
consentimiento OAuth de apps no aprobadas y esta vía no es viable para esa cuenta.
