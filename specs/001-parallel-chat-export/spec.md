# Feature Specification: Exportación de chats en paralelo compatible con Dropbox "solo en línea"

**Feature Branch**: `001-parallel-chat-export`
**Created**: 2026-10-21
**Status**: Draft
**Input**: Exportar varios chats en paralelo, con el grado de paralelismo como parámetro y
sin superar las cuotas de Google Chat, y que relanzar el backup sobre carpetas de Dropbox
"solo en línea" no vuelva a descargar nada.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backup más rápido con paralelismo configurable (Priority: P1)

Quien ejecuta el backup indica cuántos chats se exportan a la vez. Con varios a la vez, el
backup completo de cientos de chats termina en una fracción del tiempo que tarda de uno en
uno, sin que Google bloquee la cuenta por exceso de peticiones.

**Why this priority**: es lo que ha pedido el usuario. Al ritmo actual (unos 15 chats en 40
minutos) los 433 chats tardarían casi un día, y la exportación tiene que estar hecha antes
del apagón de Workspace, para tres personas.

**Independent Test**: lanzar el backup con paralelismo 1 y con paralelismo 4 sobre el mismo
subconjunto de chats; comparar duración, número de errores y contenido resultante.

**Acceptance Scenarios**:

1. **Given** el parámetro de paralelismo sin definir, **When** se lanza el backup, **Then** se
   comporta exactamente como hoy (un chat a la vez).
2. **Given** paralelismo N > 1, **When** se lanza el backup, **Then** nunca hay más de N chats
   exportándose a la vez y el resultado (carpetas, mensajes, adjuntos) es el mismo que con
   paralelismo 1.
3. **Given** que Google responde "demasiadas peticiones", **When** ocurre durante la
   exportación, **Then** el backup espera y reintenta sin perder el chat ni abortar el resto.
4. **Given** un valor de paralelismo no válido (no numérico, 0 o negativo), **When** se lanza
   el backup, **Then** se detiene antes de empezar con un mensaje que dice qué valor es válido.

---

### User Story 2 - Relanzar sobre Dropbox "solo en línea" sin volver a descargar (Priority: P1)

El backup vive en una carpeta sincronizada con Dropbox. El usuario marca como "solo en línea"
lo ya subido para liberar disco. Si después relanza el backup (por un corte o para completar),
los adjuntos ya exportados no se vuelven a descargar de Google ni Dropbox los vuelve a bajar
al disco.

**Why this priority**: sin esto, marcar "solo en línea" para ahorrar disco haría que el
siguiente relanzamiento volviera a llenar el disco y repitiera horas de descarga.

**Independent Test**: con un chat ya exportado, marcar su carpeta de adjuntos como "solo en
línea" en el Finder, relanzar el backup y comprobar que los adjuntos siguen sin contenido local
y que el backup los cuenta como ya existentes.

**Acceptance Scenarios**:

1. **Given** un adjunto ya exportado y marcado "solo en línea", **When** se relanza el backup,
   **Then** se considera existente, no se descarga de Google y sigue "solo en línea".
2. **Given** un adjunto a medio descargar de un corte anterior, **When** se relanza, **Then** se
   descarga de nuevo y entero.

---

### User Story 3 - Freno de disco y reanudación con varios chats a la vez (Priority: P2)

Con varios chats exportándose a la vez, el freno de disco sigue deteniendo todo limpio antes
de llenar el disco, y un corte en mitad de varios chats se recupera relanzando, igual que hoy.

**Why this priority**: el paralelismo no puede romper las dos garantías que ya existen.

**Independent Test**: lanzar con paralelismo 4 y un mínimo de disco imposible; comprobar que
se detiene sin descargar nada y deja el resumen marcado como detenido. Interrumpir con Ctrl-C
a mitad y relanzar; comprobar que no hay duplicados ni ficheros a medias tomados por buenos.

**Acceptance Scenarios**:

1. **Given** paralelismo N y el disco por debajo del mínimo, **When** cualquier chat va a
   escribir, **Then** todos los chats en curso se detienen, se guarda el índice y el resumen con
   el motivo, y no se empieza ningún chat nuevo.
2. **Given** una interrupción con varios chats a medias, **When** se relanza, **Then** cada chat
   termina en una sola carpeta y ningún adjunto incompleto queda como completo.

### Edge Cases

- Dos chats distintos que darían el mismo nombre de carpeta exportándose a la vez: cada uno
  termina en su propia carpeta, nunca mezclados.
- Un chat muy grande (miles de adjuntos) junto a muchos pequeños: los pequeños no esperan a
  que termine el grande.
- El token de sesión caduca durante la exportación en paralelo: se renueva sin que fallen los
  chats en curso.
- El progreso por pantalla con varios chats a la vez sigue siendo legible: cada línea dice a
  qué chat se refiere y el contador global avanza.
- Paralelismo mayor que el número de chats: no es un error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El backup MUST aceptar un parámetro de paralelismo (número de chats exportados a
  la vez), con valor por defecto 1, configurable igual que el resto de parámetros.
- **FR-002**: El backup MUST rechazar antes de empezar un valor de paralelismo no válido, con
  un mensaje que diga el rango válido.
- **FR-003**: El backup MUST NOT tener en ningún momento más chats en exportación que el
  paralelismo configurado.
- **FR-004**: Ante respuestas de límite de peticiones o errores temporales del servidor, el
  backup MUST reintentar con esperas crecientes y MUST NOT dar el chat por fallido mientras
  queden reintentos.
- **FR-005**: El resultado del backup (carpetas, ficheros de mensajes, adjuntos, índice) MUST
  ser el mismo con cualquier valor de paralelismo, salvo el orden de las líneas de progreso.
- **FR-006**: Para decidir si un adjunto ya existe, el backup MUST usar solo la información de
  metadatos del fichero (existencia y tamaño), sin leer su contenido, de modo que un fichero
  "solo en línea" de Dropbox no se descargue.
- **FR-007**: Un adjunto interrumpido a mitad MUST NOT contar como existente al relanzar.
- **FR-008**: El freno de disco MUST detener todos los chats en curso y no empezar ninguno
  nuevo; el índice y el resumen MUST guardarse con el motivo.
- **FR-009**: Dos chats que den el mismo nombre de carpeta MUST acabar en carpetas distintas
  aunque se exporten a la vez.
- **FR-010**: El resumen final MUST registrar el paralelismo usado, junto al resto de
  parámetros.
- **FR-011**: La documentación MUST explicar cómo elegir el paralelismo y cómo marcar "solo en
  línea" en Dropbox, incluido que no hay forma automática desde la terminal.

### Key Entities

- **Chat**: espacio, grupo o conversación 1 a 1; se identifica por su id y se guarda en una
  carpeta propia `<fecha>_<nombre>`.
- **Adjunto**: fichero subido a un chat; existe en disco completo, a medias (`.part`) o "solo
  en línea" (marcador local con el contenido en Dropbox).
- **Parámetro de paralelismo**: número entero ≥ 1 de chats simultáneos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con paralelismo 4, exportar el mismo conjunto de chats tarda como máximo la
  mitad que con paralelismo 1.
- **SC-002**: Un backup completo con paralelismo 4 termina con 0 chats fallidos por límite de
  peticiones.
- **SC-003**: Relanzar el backup sobre chats ya exportados y marcados "solo en línea" descarga
  0 adjuntos y no aumenta el espacio ocupado en disco por esos chats.
- **SC-004**: Con el disco por debajo del mínimo, el backup se detiene sin escribir ningún
  adjunto nuevo, con cualquier paralelismo.
- **SC-005**: Tras interrumpir y relanzar con paralelismo 4, el número de carpetas de chat es
  igual al número de chats exportados (0 duplicados).

## Assumptions

- Las cuotas publicadas por Google (leídas el 2026-10-21) son 3000 lecturas por minuto por
  proyecto para mensajes, miembros, espacios y adjuntos, y 15 lecturas por segundo por espacio.
  Con un chat por hilo de trabajo y pocos chats a la vez, el límite por espacio no se comparte
  entre hilos; el que importa es el del proyecto.
- Un paralelismo de 4 es un punto de partida razonable; el valor por defecto sigue siendo 1
  para no cambiar el comportamiento de quien no lo toque.
- En macOS 15 no existe una orden de terminal para marcar ficheros de Dropbox como "solo en
  línea"; se hace desde el Finder o lo hace el sistema cuando falta disco. El backup no intenta
  forzarlo.
- Que consultar existencia y tamaño de un fichero "solo en línea" no lo descarga es el
  comportamiento esperado de los ficheros sin contenido local en macOS; se verificará con un
  fichero real marcado desde el Finder (no hay ninguno marcado hoy).
- Fuera de alcance: subir a Dropbox desde el script, comprimir, convertir formatos, unir las
  exportaciones de varias personas.
