# Feature Specification: Parallel chat export compatible with Dropbox "online-only"

**Feature Branch**: `001-parallel-chat-export`
**Created**: 2026-10-21
**Status**: Draft
**Input**: Export several chats in parallel, with the degree of parallelism as a parameter and
without exceeding the Google Chat quotas, and make relaunching the backup over Dropbox
"online-only" folders download nothing again.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Faster backup with configurable parallelism (Priority: P1)

Whoever runs the backup sets how many chats are exported at once. With several at once, the
complete backup of hundreds of chats finishes in a fraction of the time it takes one by one,
without Google blocking the account for too many requests.

**Why this priority**: it is what the user asked for. At the current pace (about 15 chats in 40
minutes) the 433 chats would take almost a day, and the export has to be done before the
Workspace shutdown, for three people.

**Independent Test**: launch the backup with parallelism 1 and with parallelism 4 over the same
subset of chats; compare duration, number of errors and resulting content.

**Acceptance Scenarios**:

1. **Given** the parallelism parameter is undefined, **When** the backup is launched, **Then** it
   behaves exactly as today (one chat at a time).
2. **Given** parallelism N > 1, **When** the backup is launched, **Then** there are never more than
   N chats being exported at once and the result (folders, messages, attachments) is the same as
   with parallelism 1.
3. **Given** Google answers "too many requests", **When** it happens during the export,
   **Then** the backup waits and retries without losing the chat or aborting the rest.
4. **Given** an invalid parallelism value (non-numeric, 0 or negative), **When** the backup is
   launched, **Then** it stops before starting with a message that says which value is valid.

---

### User Story 2 - Relaunch over Dropbox "online-only" without downloading again (Priority: P1)

The backup lives in a folder synced with Dropbox. The user marks what has already been uploaded
as "online-only" to free up disk. If they later relaunch the backup (after an interruption or to
complete it), the attachments already exported are not downloaded again from Google, nor does
Dropbox bring them back down to the disk.

**Why this priority**: without this, marking "online-only" to save disk would make the next
relaunch fill the disk again and repeat hours of downloading.

**Independent Test**: with a chat already exported, mark its attachments folder as "online-only"
in the Finder, relaunch the backup and check that the attachments still have no local content
and that the backup counts them as already existing.

**Acceptance Scenarios**:

1. **Given** an attachment already exported and marked "online-only", **When** the backup is
   relaunched, **Then** it is considered existing, is not downloaded from Google and stays
   "online-only".
2. **Given** an attachment half-downloaded from an earlier interruption, **When** it is relaunched,
   **Then** it is downloaded again, in full.

---

### User Story 3 - Disk brake and resumption with several chats at once (Priority: P2)

With several chats being exported at once, the disk brake still stops everything cleanly before
the disk fills up, and an interruption in the middle of several chats is recovered by
relaunching, the same as today.

**Why this priority**: parallelism must not break the two guarantees that already exist.

**Independent Test**: launch with parallelism 4 and an impossible disk minimum; check that it
stops without downloading anything and leaves the summary marked as stopped. Interrupt with
Ctrl-C midway and relaunch; check that there are no duplicates nor half-written files taken as
good.

**Acceptance Scenarios**:

1. **Given** parallelism N and the disk below the minimum, **When** any chat is about to write,
   **Then** all chats in progress stop, the index and the summary are saved with the reason, and
   no new chat is started.
2. **Given** an interruption with several chats half done, **When** it is relaunched, **Then** each
   chat ends up in a single folder and no incomplete attachment is left as complete.

### Edge Cases

- Two different chats that would get the same folder name being exported at once: each one ends
  up in its own folder, never mixed.
- A very large chat (thousands of attachments) alongside many small ones: the small ones do not
  wait for the large one to finish.
- The session token expires during the parallel export: it is renewed without the chats in
  progress failing.
- On-screen progress with several chats at once stays readable: each line says which chat it
  refers to and the global counter advances.
- Parallelism greater than the number of chats: not an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backup MUST accept a parallelism parameter (number of chats exported at once),
  with default value 1, configurable the same way as the other parameters. *Amended 2026-10-21 by
  spec 002 FR-011: the default is 4, measured with 0 quota retries.*
- **FR-002**: The backup MUST reject an invalid parallelism value before starting, with a
  message that states the valid range.
- **FR-003**: The backup MUST NOT at any moment have more chats being exported than the
  configured parallelism.
- **FR-004**: On rate-limit responses or temporary server errors, the backup MUST retry with
  increasing waits and MUST NOT mark the chat as failed while retries remain.
- **FR-005**: The result of the backup (folders, message files, attachments, index) MUST be the
  same with any parallelism value, except for the order of the progress lines.
- **FR-006**: To decide whether an attachment already exists, the backup MUST use only the
  file's metadata (existence and size), without reading its content, so that a Dropbox
  "online-only" file is not downloaded.
- **FR-007**: An attachment interrupted midway MUST NOT count as existing on relaunch.
- **FR-008**: The disk brake MUST stop all chats in progress and start no new one; the index and
  the summary MUST be saved with the reason.
- **FR-009**: Two chats that produce the same folder name MUST end up in different folders even
  if they are exported at once.
- **FR-010**: The final summary MUST record the parallelism used, alongside the other
  parameters.
- **FR-011**: The documentation MUST explain how to choose the parallelism and how to mark
  "online-only" in Dropbox, including that there is no automatic way to do it from the terminal.

### Key Entities

- **Chat**: space, group or 1:1 conversation; it is identified by its id and saved in its own
  folder `<date>_<name>`.
- **Attachment**: file uploaded to a chat; it exists on disk complete, half-written (`.part`) or
  "online-only" (a local placeholder with the content in Dropbox).
- **Parallelism parameter**: integer ≥ 1 of simultaneous chats.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With parallelism 4, exporting the same set of chats takes at most half as long as
  with parallelism 1.
- **SC-002**: A complete backup with parallelism 4 finishes with 0 chats failed due to the rate
  limit.
- **SC-003**: Relaunching the backup over chats already exported and marked "online-only"
  downloads 0 attachments and does not increase the disk space taken by those chats.
- **SC-004**: With the disk below the minimum, the backup stops without writing any new
  attachment, with any parallelism.
- **SC-005**: After interrupting and relaunching with parallelism 4, the number of chat folders
  equals the number of chats exported (0 duplicates).

## Assumptions

- The quotas published by Google (read on 2026-10-21) are 3000 reads per minute per project for
  messages, members, spaces and attachments, and 15 reads per second per space. With one chat per
  worker thread and few chats at once, the per-space limit is not shared between threads; the
  one that matters is the project's.
- A parallelism of 4 is a reasonable starting point; the default value stays 1 so as not to
  change the behaviour for anyone who does not touch it.
- On macOS 15 there is no terminal command to mark Dropbox files as "online-only"; it is done
  from the Finder, or the system does it when disk runs low. The backup does not try to force it.
- That querying the existence and size of an "online-only" file does not download it is the
  expected behaviour of files without local content on macOS; it will be verified with a real
  file marked from the Finder (none is marked today).
- Out of scope: uploading to Dropbox from the script, compressing, converting formats, merging
  the exports of several people.
