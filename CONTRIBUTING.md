# Cómo hacer tu copia de Google Chat

<!-- doc-type: layered-how-to -->
<!-- doc-check: timeless -->

Esta guía es para quien hace la copia con su propia cuenta. Preparas el equipo una vez, entras
con tu cuenta de Google del trabajo en el navegador y el script guarda en tu disco todos los
chats en los que participas: espacios, grupos y conversaciones 1 a 1, con sus adjuntos. No
necesitas Google Cloud, ni `gcloud`, ni Terraform, ni permisos de administrador: eso lo prepara
una sola vez quien mantiene el proyecto ([README](README.md#dar-acceso-a-un-compañero)).
Probado en macOS; en Linux los pasos son los mismos salvo el primero (`xcode-select`).

Antes de empezar, pide a quien mantiene el proyecto estas tres cosas:

1. Acceso al repositorio [serverstartup/google-chat-backup](https://github.com/serverstartup/google-chat-backup) con tu usuario de GitHub.
2. Que te dé de alta como usuario de prueba de la aplicación, con tu email del trabajo.
3. El fichero `client_secret_….apps.googleusercontent.com.json`, por un canal privado. No está
   en el repositorio ni debe estarlo.

| Sección | Estás… |
|:--|:--|
| [1. Prepara tu equipo](#1-prepara-tu-equipo) | empezando de cero |
| [2. Configura la copia](#2-configura-la-copia) | con el repositorio descargado y el `client_secret` recibido |
| [3. Entra con tu cuenta y mira qué se va a copiar](#3-entra-con-tu-cuenta-y-mira-qué-se-va-a-copiar) | listo para el primer arranque |
| [4. Haz la copia](#4-haz-la-copia) | con la lista de chats a la vista |
| [5. Entrega la copia y borra tus credenciales](#5-entrega-la-copia-y-borra-tus-credenciales) | con la copia terminada |
| [Appendix](#appendix) | con un error, o queriendo saber qué hace cada variable |

---

## 1. Prepara tu equipo

Instalas tres herramientas, descargas el código y creas un entorno de Python solo para él.

### `TL;DR`

1. Instala las herramientas de línea de comandos de Apple, que incluyen `git`.
   ```bash
   xcode-select --install
   ```
   Expect: se abre un instalador, o el aviso de que ya están instaladas.
2. Instala `uv` y la CLI de GitHub. → [Instala uv y la CLI de GitHub](#instala-uv-y-la-cli-de-github)
   ```bash
   brew install uv gh
   ```
   Expect: `uv --version` y `gh --version` responden.
3. Entra en GitHub desde la terminal.
   ```bash
   gh auth login
   ```
   Expect: `Logged in to github.com as <tu-usuario>`.
4. Descarga el repositorio en tu carpeta personal. → [Descarga el repositorio](#descarga-el-repositorio)
   ```bash
   cd ~ && gh repo clone serverstartup/google-chat-backup
   ```
   Expect: existe la carpeta `~/google-chat-backup`.
5. Crea el entorno de Python e instala las dependencias. → [Crea el entorno de Python](#crea-el-entorno-de-python)
   ```bash
   cd ~/google-chat-backup/scripts && uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
   ```
   Expect: termina con `Installed N packages`.

### Instala uv y la CLI de GitHub

Con [Homebrew](https://brew.sh), las dos de una vez:

```bash
brew install uv gh
```

**Prerequisites:** Homebrew. Si no lo tienes, instálalo antes siguiendo [brew.sh](https://brew.sh).
[uv](https://docs.astral.sh/uv/) gestiona Python y sus paquetes (descarga él mismo el Python que
haga falta) y la [CLI de GitHub](https://cli.github.com) te deja descargar repositorios privados
sin configurar claves SSH.

### Descarga el repositorio

Una copia del código en `~/google-chat-backup`:

```bash
cd ~ && gh repo clone serverstartup/google-chat-backup
```

**If it fails:** `Could not resolve to a Repository` significa que tu usuario de GitHub aún no
tiene acceso: pídeselo a quien mantiene el proyecto. Todos los comandos de esta guía asumen esta
carpeta; si lo descargas en otra, cambia `~/google-chat-backup` por tu ruta.

### Crea el entorno de Python

Un Python 3.12 aislado dentro de `scripts/.venv`, con las dos librerías de Google:

```bash
cd ~/google-chat-backup/scripts && uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
```

**Verification:** no hace falta tener Python instalado; si no hay un 3.12, `uv` lo descarga. Nada
de esto toca el Python de tu sistema, y `.venv/` no se sube al repositorio.

---

## 2. Configura la copia

Dejas el `client_secret` donde el script lo busca y, si quieres, eliges dónde se guarda la copia.

### `TL;DR`

1. Mueve a `scripts/` el `client_secret` que te han pasado.
   ```bash
   mv ~/Downloads/client_secret_*.apps.googleusercontent.com.json ~/google-chat-backup/scripts/
   ```
   Expect: `ls ~/google-chat-backup/scripts/client_secret_*` muestra un fichero.
2. Crea tu fichero de configuración a partir del ejemplo. → [Ajusta tu configuración](#ajusta-tu-configuración)
   ```bash
   cd ~/google-chat-backup/scripts && cp .env.example .env
   ```
   Expect: existe `scripts/.env`, con `GCHAT_WORKERS=4`.

### Ajusta tu configuración

Un `scripts/.env` con lo que quieras cambiar de los valores por defecto:

```bash
cd ~/google-chat-backup/scripts && cp .env.example .env
```

Con el ejemplo tal cual ya funciona: exporta 4 chats a la vez y guarda la copia en
`scripts/gchat-backup/`. Lo único que quizá quieras cambiar es `GCHAT_OUT_DIR`, para guardarla en
otra carpeta (por ejemplo una de Dropbox, que la va subiendo según se descarga); ábrelo con
`open -e .env`, quita el `#` de esa línea y pon tu ruta. Lo que significa cada variable está en
[Reference: variables de configuración](#reference-variables-de-configuración). `scripts/.env` y
el `client_secret` están en `.gitignore`: no se suben nunca.

---

## 3. Entra con tu cuenta y mira qué se va a copiar

El primer arranque solo lista los chats: te identifica con Google y comprueba que todo funciona,
sin descargar nada.

### `TL;DR`

1. Lanza el script en modo prueba y entra en el navegador con tu cuenta del trabajo. → [Entra con tu cuenta](#entra-con-tu-cuenta)
   ```bash
   cd ~/google-chat-backup/scripts && GCHAT_DRY_RUN=true .venv/bin/python gchat_backup.py
   ```
   Expect: `Exportando como <tu email del trabajo>`, `N espacios visibles` y la lista de chats.

### Entra con tu cuenta

Google te pregunta en el navegador quién eres y qué permites leer:

```bash
cd ~/google-chat-backup/scripts && GCHAT_DRY_RUN=true .venv/bin/python gchat_backup.py
```

**Procedure:**

1. Se abre el navegador. Elige tu cuenta **del trabajo**, la que usas en Google Chat, no una
   personal.
2. Si aparece *"Google no ha verificado esta aplicación"*, pulsa **Configuración avanzada** →
   **Ir a …**. Es la aplicación del proyecto, en modo de pruebas.
3. Acepta los permisos: son de solo lectura (ver espacios, miembros y mensajes).
4. El navegador dice que ya puedes cerrar la pestaña; vuelve a la terminal.

**Verification:** la línea `Exportando como …` tiene que mostrar tu email del trabajo. Así es como
el script sabe quién eres: no conoce tu contraseña ni la guarda; Google le da un permiso de
lectura para la cuenta con la que entraste, que se queda en `scripts/token.json`, y el script le
pregunta a Google de quién es. Tu copia se guarda en una carpeta con tu nombre de usuario (la parte
de tu email antes de la `@`). En los siguientes arranques ya no se abre el navegador. Por qué no
hace falta nada más: [Explanation: por qué basta con entrar en el navegador](#explanation-por-qué-basta-con-entrar-en-el-navegador).

---

## 4. Haz la copia

### `TL;DR`

1. Lanza la copia real. → [Lanza la copia](#lanza-la-copia)
   ```bash
   cd ~/google-chat-backup/scripts && .venv/bin/python gchat_backup.py
   ```
   Expect: una línea por chat y, al final, `Hecho: N espacios, M mensajes, 0 con error`.
2. Si se corta o lo paras, vuelve a lanzar el mismo comando: sigue donde iba.
   ```bash
   cd ~/google-chat-backup/scripts && .venv/bin/python gchat_backup.py
   ```
   Expect: los chats ya copiados dicen `0 nuevos / N ya estaban`.

### Lanza la copia

Descarga los mensajes y adjuntos de todos tus chats a la carpeta de salida:

```bash
cd ~/google-chat-backup/scripts && .venv/bin/python gchat_backup.py
```

Déjalo en una terminal abierta y con el portátil enchufado: con cientos de chats tarda horas, y
los que tienen miles de adjuntos son los más lentos. Puedes pararlo con Ctrl-C cuando quieras: lo
que estaba bajando se termina y lo demás se retoma al relanzar.

**Verification:** cada línea `adjuntos X nuevos / Y ya estaban / Z error / W en Drive` resume un
chat. Los adjuntos que viven en Google Drive no se descargan: queda el enlace en el JSON. Si el
disco baja de 20 GB libres, el script se para solo con `DETENIDO`
([Troubleshooting: el script se para con DETENIDO](#troubleshooting-el-script-se-para-con-detenido)).
El resultado, una carpeta por chat:

```text
gchat-backup/<tu-usuario>/
  index.json  manifest.json
  2021-03-04_nombre-del-espacio/
    space.json  members.json  messages.json
    attachments/
```

---

## 5. Entrega la copia y borra tus credenciales

### `TL;DR`

1. Comprueba el resumen de la copia.
   ```bash
   cd ~/google-chat-backup/scripts && grep -E '"(spaces|messages|stoppedEarly)"' gchat-backup/*/manifest.json
   ```
   Expect: `"stoppedEarly": null` y el número de espacios y mensajes.
2. Entrega la carpeta `gchat-backup/<tu-usuario>/` a quien mantiene el proyecto, por el medio que
   acordéis (una carpeta compartida de Dropbox, por ejemplo). Contiene conversaciones privadas: no
   la subas a ningún sitio público.
3. Borra tus credenciales del equipo.
   ```bash
   cd ~/google-chat-backup/scripts && rm -f token.json client_secret_*.json
   ```
   Expect: `ls token.json` dice que no existe.
4. Optional: retira el permiso en tu cuenta de Google, en
   [myaccount.google.com/connections](https://myaccount.google.com/connections).

---

## Appendix

### Reference: variables de configuración

Se ponen en `scripts/.env` o delante del comando (`GCHAT_DRY_RUN=true .venv/bin/python …`). Las
rutas relativas cuentan desde `scripts/`.

| Variable | Para qué | Por defecto |
|:--|:--|:--|
| `GCHAT_WORKERS` | chats que se copian a la vez (1-16) | `1` (el ejemplo pone `4`) |
| `GCHAT_OUT_DIR` | carpeta donde se guarda la copia | `gchat-backup` |
| `GCHAT_DRY_RUN` | `true`: solo lista los chats, no descarga | `false` |
| `GCHAT_MIN_FREE_GB` | se para si quedan menos GB libres | `20` |
| `GCHAT_CLIENT_SECRET` | ruta del `client_secret` | el único `client_secret_*.json` de `scripts/` |
| `GCHAT_TOKEN_FILE` | dónde se guarda el permiso de Google | `token.json` |
| `GCHAT_SPACE_TYPES` | tipos de chat: `SPACE`, `GROUP_CHAT`, `DIRECT_MESSAGE` | los tres |
| `GCHAT_SPACE_FILTER` | expresión regular sobre el nombre del espacio | todos |
| `GCHAT_SINCE` | solo mensajes desde esta fecha (`AAAA-MM-DD`) | todos |
| `GCHAT_DOWNLOAD_ATTACHMENTS` | `false`: no descarga adjuntos | `true` |

Used by: [Ajusta tu configuración](#ajusta-tu-configuración).

### Explanation: por qué basta con entrar en el navegador

El script usa la autenticación de usuario de Google: actúa como tú y solo ve lo que verías en
Google Chat desde el navegador. Por eso no necesita una cuenta de servicio, ni `gcloud`, ni
permisos de administrador del dominio. El `client_secret` no identifica a nadie: identifica a la
aplicación (la que quien mantiene el proyecto dio de alta en Google Cloud), y es el mismo para
todo el equipo. Quién eres lo decide el inicio de sesión en el navegador; por eso cada persona
genera su propio `token.json` y no hay que compartirlo nunca.

Used by: [Entra con tu cuenta](#entra-con-tu-cuenta).

### Troubleshooting: "Acceso bloqueado" o "access_denied" al entrar

This issue occurs when tu email no está dado de alta como usuario de prueba de la aplicación,
cuando eliges una cuenta personal en vez de la del trabajo, o cuando cancelas la pantalla de
permisos. To resolve it, pide a quien mantiene el proyecto que añada tu email del trabajo como
usuario de prueba, borra `scripts/token.json` si existe y repite la
[sección 3](#3-entra-con-tu-cuenta-y-mira-qué-se-va-a-copiar) eligiendo la cuenta del trabajo.

Used by: [Entra con tu cuenta](#entra-con-tu-cuenta).

### Troubleshooting: "No encuentro el fichero client_secret"

This issue occurs when el `client_secret_….json` no está en `scripts/` (sigue en Descargas, por
ejemplo) o hay más de uno. To resolve it, repite el paso 1 de
[2. Configura la copia](#2-configura-la-copia) y deja un único fichero.

Used by: [Entra con tu cuenta](#entra-con-tu-cuenta).

### Troubleshooting: el script se para con DETENIDO

This issue occurs when el disco baja del mínimo libre (`GCHAT_MIN_FREE_GB`, 20 GB por defecto):
el script se para limpio antes de llenarlo. To resolve it, libera espacio (si la copia está en
Dropbox, clic derecho sobre la carpeta → **Hacer disponible solo en línea** cuando ya se haya
subido) y relanza el mismo comando; no repite lo ya descargado.

Used by: [Lanza la copia](#lanza-la-copia).
