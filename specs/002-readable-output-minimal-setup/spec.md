# Feature Specification: Readable output and minimal setup

**Feature Branch**: `001-parallel-chat-export` (shipped together, before v1.0.0)
**Created**: 2026-10-21
**Status**: Draft
**Input**: The maintainer rejected the first release: the terminal output is hard to read (a
timestamp on every line, long sentences, library warnings) and the setup asks for tools nobody
needs (Homebrew, uv, the GitHub CLI). Make the output follow the house CLI output rules and cut
the setup to the minimum a teammate needs to run a backup alone.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read the progress at a glance (Priority: P1)

A teammate runs the backup and, without reading the docs, understands from the terminal what is
happening, how far along it is, what each chat produced, and how it ended.

**Why this priority**: the output is the only interface; the maintainer will not release until
it is right.

**Independent Test**: run a preview and a real backup over a few chats; every line can be read
without knowing the code, and the last line is the verdict.

**Acceptance Scenarios**:

1. **Given** a run, **When** it starts, **Then** it says once who is signed in, where the backup
   goes and how many chats will be backed up, as numbered steps.
2. **Given** a chat finishes, **When** its line prints, **Then** it is one line with a done or
   failed mark, the progress counter, the chat name and its counts (messages, attachments, how
   many new), aligned with the other chat lines.
3. **Given** the run ends, **When** the last line prints, **Then** it is the verdict: done with
   totals, stopped (disk) with how to continue, or failed with how many chats and what to do.
4. **Given** an error the user can fix (no client secret, bad setting), **When** it happens,
   **Then** it prints `Error: <what happened>` and a `Hint: <what to do>` line, and exits 1.
5. **Given** an older Python or the macOS system SSL, **When** the script runs, **Then** no
   library warning appears on the terminal.

---

### User Story 2 - Set up with what the machine already has (Priority: P1)

A teammate on any operating system with Git and Python 3.9+ goes from nothing to a running
backup with the repository, the client secret and one command.

**Why this priority**: every extra tool is a question to the maintainer.

**Independent Test**: from a fresh clone, with only the system `python3`, one command prepares
the environment on first use and runs the backup.

**Acceptance Scenarios**:

1. **Given** a fresh clone and the system `python3`, **When** the user runs the backup command,
   **Then** the first run creates the Python environment and installs the dependencies by
   itself, and later runs skip that.
2. **Given** no settings file, **When** the backup runs, **Then** the defaults back up 4 chats at
   a time into the repository's `scripts/gchat-backup/`.

### Edge Cases

- Output redirected to a file or a pipe: no control characters, same lines.
- A chat name longer than the column: truncated with `…`, never wrapping the line.
- `--preview` (list only) prints the list of chats on stdout so it can be piped; progress goes
  to stderr.
- Dependency installation fails (no network): the command stops with the pip error and a hint.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Progress and messages MUST go to stderr; the chat list of a preview MUST go to stdout.
- **FR-002**: The terminal output MUST NOT carry timestamps or level labels (`INFO`, `ERROR`…).
- **FR-003**: The run MUST be shown as numbered steps `[k/m] Verb…`: sign in, list chats, back up.
- **FR-004**: Each chat MUST be one line: `✓` or `✗`, `[n/total]`, the chat name in a fixed-width
  column, then its counts with nouns; marks are limited to `✓ ✗ ⚠ → …`.
- **FR-005**: The last line MUST be the verdict, with totals; a stop or failures MUST say how to
  continue.
- **FR-006**: User-fixable errors MUST print `Error: <fact>` (capital first, no trailing period)
  and `Hint: <action>`, and exit 1; usage errors exit 2.
- **FR-007**: Known library warnings about the Python version and the system SSL library MUST
  NOT reach the terminal.
- **FR-008**: A `--preview` flag MUST do what `GCHAT_DRY_RUN=true` does; the variable keeps
  working.
- **FR-009**: One command at the repository root MUST create the Python environment on first use,
  install the dependencies and run the backup, passing its arguments through, on Windows, Linux
  and macOS alike: a Python launcher (`python3 backup.py`, `py backup.py` on Windows), not a shell
  script. *Amended 2026-10-21: it was `backup.sh`, which assumed a POSIX shell.*
- **FR-010**: The dependencies MUST install on Python 3.9 (the macOS system Python) and newer.
- **FR-011**: The default for parallel chats MUST be 4 (amends 001 FR-001, which said 1).
- **FR-012**: The README MUST assume only Git and Python 3.9+, on any operating system, and MUST
  say where the client secret comes from (the maintainer) and who can read what (the client
  secret identifies the app; the user's own sign-in decides whose chats are read).
  *Amended 2026-10-21: it assumed macOS and installed Apple's command line tools.*
- **FR-013**: Output MUST NOT crash on a console or file that is not UTF-8 (`✓`, `…` are replaced).

### Key Entities

- **Run summary line**: the verdict; the only line a user must read when everything went well.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A successful run prints at most 3 lines plus one line per chat plus the verdict.
- **SC-002**: 0 lines with a timestamp, a level label or a library warning in a run on Python 3.9.
- **SC-003**: From a fresh clone with only the system `python3`, a preview works with 1 command
  after placing the client secret.
- **SC-004**: The README setup has at most 3 steps before the first run.

## Assumptions

- `rich` is not added: one dependency less, and the output stays plain text, so colour is out of
  scope (the house rule allows plain output; it only requires that colour never carries meaning).
- The macOS system Python is 3.9.6 (measured 2026-10-21); `google-api-python-client` 2.198.0 and
  `google-auth-oauthlib` 1.3.1 are the newest that install there.
- The repository is private: `git clone` needs the teammate's usual GitHub access; downloading the
  ZIP from GitHub is the fallback.
