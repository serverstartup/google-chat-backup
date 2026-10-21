# Feature Specification: Configurable chat folder layout

**Feature Branch**: `003-folder-template`
**Created**: 2026-10-21
**Status**: Draft
**Input**: Each chat folder is named `<YYYY-MM-DD>_<chat>` after its FIRST message, so finding a
chat by typing its name means knowing its date first. The maintainer wants the layout to come
from a template in the backup settings, defaulting to the year and month of the LAST message and
then the chat name, in two folder levels. Existing backups must move to the layout by themselves,
without downloading anything again. Dates in names are written `yyyymmdd`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find a chat by month of its last message, then by name (Priority: P1)

A teammate opens their backup and finds a chat by browsing to the year and month it was last
active, then typing the first letters of its name.

**Why this priority**: it is the reason for the change; the first-message date at the front of
every name makes type-to-find useless.

**Independent Test**: back up a few chats with the default settings; each lands in
`<year>/<month>/<chat name>` of its last message, and typing the name inside that month finds it.

**Acceptance Scenarios**:

1. **Given** default settings, **When** a chat whose last message is from March 2024 is backed
   up, **Then** its folder is `2024/03/<chat name>`.
2. **Given** two chats with the same name whose last messages fall in the same month, **When**
   both are backed up, **Then** one keeps the plain name and the other gets its short id appended,
   and the next run moves neither.
3. **Given** a chat with no messages, **When** it is backed up, **Then** the date of its creation
   stands in for the last message; with neither, the date parts read `undated`.

---

### User Story 2 - Choose another layout with a template (Priority: P2)

The maintainer, or any teammate, sets a template in the backup settings and the folders follow it.

**Why this priority**: people search their files differently; one fixed layout will not suit all
of them.

**Independent Test**: set a template such as `{name}_{last:%Y%m%d}` and back up a few chats; each
folder follows it.

**Acceptance Scenarios**:

1. **Given** the template `{name}_{last:%Y%m%d}`, **When** a chat last active on 12 March 2024 is
   backed up, **Then** its folder is `<chat name>_20240312`.
2. **Given** a template naming an unknown placeholder, an absolute path, `..` or an empty folder
   level, **When** the backup starts, **Then** it stops before signing in with an `Error:` line
   naming the template and a `Hint:` listing the valid placeholders, and exits 1.

---

### User Story 3 - An existing backup follows the layout by itself (Priority: P1)

A teammate who already has a backup in the old layout, or in another template, runs the backup
again and every chat folder ends up where the current template puts it, without re-downloading
attachments.

**Why this priority**: three people have or will have backups of hundreds of chats, partly
"online-only" in Dropbox; downloading them again is not acceptable.

**Independent Test**: run over a backup in the old `<date>_<name>` layout; every chat folder is
moved, none is duplicated, and no attachment is downloaded again.

**Acceptance Scenarios**:

1. **Given** chat folders in the old layout, **When** the backup runs, **Then** each folder is
   moved, not copied, to its new place, and only its `space.json` is read to recognise it.
2. **Given** a chat whose last message is newer than its folder's month, **When** the backup
   runs, **Then** the folder moves to the new month and the empty month and year folders left
   behind are removed.
3. **Given** a folder whose `space.json` cannot be read, **When** the backup runs, **Then** it
   stops before exporting anything, names the folder and says how to fix it, and creates no
   folder: without that file nothing tells which chat the folder belongs to, so a new folder
   could duplicate it.

---

### Edge Cases

- A template whose rendered path is the same for two chats: the second gets `_<short id>` on its
  last level, as today.
- A chat name that renders empty: `unnamed`, as today.
- A template with no date placeholder: folders never move between runs.
- Interrupting the run while a folder is moving: the move is a single rename, so the folder is
  either in the old place or the new one, never in both.
- Folders inside the user's backup that hold no `space.json` (and are not on the way to one) are
  left alone.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The folder of each chat MUST come from a template setting, `GCHAT_FOLDER_TEMPLATE`,
  defaulting to `{last:%Y}/{last:%m}/{name}`.
- **FR-002**: The template MUST offer `{name}` (the chat's name, as folders are named today),
  `{last}` (date of the last message), `{first}` (date of the first message), `{type}` (`space`,
  `group-chat` or `direct-message`) and `{id}` (the chat's short id). Date placeholders MUST take
  strftime codes (`{last:%Y%m%d}`), and a bare `{last}` MUST render as `yyyymmdd`.
- **FR-003**: `{last}` MUST come from the date of the chat's last message as Google reports it
  for the chat, falling back to the last message read, then to the chat's creation date, then to
  `undated`. `{first}` MUST come from the first message read, then the creation date, then
  `undated`. Dates are in UTC, as Google reports them.
- **FR-004**: A `/` in the template MUST create a folder level. A template that renders an
  absolute path, a `..` level or an empty level, or that names an unknown placeholder, MUST stop
  the run before signing in with `Error:` + `Hint:` and exit 1.
- **FR-005**: The backup MUST recognise an existing chat folder by its `space.json` at any depth
  under the user's backup, and MUST move it to the rendered path when the two differ, with a
  single rename, removing the folders left empty.
- **FR-006**: Recognising folders MUST read nothing but `space.json`; attachments MUST NOT be
  opened or copied.
- **FR-007**: A `space.json` that still cannot be read after a short retry MUST stop the run
  before exporting, with `Error:` naming the folder and `Hint:` saying how to fix it, exit 1.
  The run MUST never create a folder for a chat it might already hold.
- **FR-008**: The index of exported chats MUST record each chat's folder as a path relative to
  the user's backup.
- **FR-009**: The run summary MUST count the folders moved, as it counts chats and messages.

### Key Entities

- **Folder template**: a pattern of literal text, placeholders and `/`, set once per backup.
- **Chat folder**: one per chat, recognised by the `space.json` it holds, placed where the
  template renders it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With default settings, 100% of chat folders sit at `<year>/<month>/<name>` of their
  last message after one run.
- **SC-002**: A run over an existing backup in the old layout downloads 0 attachments again and
  leaves 0 duplicate chat folders.
- **SC-003**: A second run with nothing new moves 0 folders.
- **SC-004**: Every invalid template is rejected before signing in, with exit status 1.

## Assumptions

- Google reports, for every chat it lists, the date of the chat's last message; the maintainer's
  backup shows it for 433 of 433 chats.
- The maintainer's existing backup was already moved to the default layout by a one-off script
  that applies the same rules (last-message month, same name, same short-id suffix), so the first
  run of this feature finds it in place.
- Changing the template is rare; when it changes, the next run moves every folder once.
- The backup lives on one volume, so a move is a rename that reads no file content.
