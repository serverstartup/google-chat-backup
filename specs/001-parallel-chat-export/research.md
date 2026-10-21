# Research: parallel export and Dropbox "online-only"

## 1. Unit of parallelism: the chat

- **Decision**: one thread exports a whole chat (members, messages, attachments); N threads at
  once.
- **Rationale**: the per-space quota (15 reads/s, shared between apps) is respected on its own
  because within a chat the requests remain sequential; the one shared between threads is the
  project's (3000/min per type = 50/s), far from what a few sequential threads reach. Also, each
  chat still writes only to its own folder.
- **Alternatives considered**: parallelising attachments within a chat (would speed up large
  chats, but concentrates requests on one space and collides with the 15/s); processes instead
  of threads (the work is network-bound, not CPU-bound; processes complicate sharing state).

## 2. One API client per thread

- **Decision**: each thread builds its own `build("chat", "v1", credentials=creds)`; the
  credentials are shared.
- **Rationale**: `httplib2`, the transport of `googleapiclient`, is not thread-safe; one client
  per thread is what the library itself recommends. `google_auth_httplib2` refreshes the token
  per request when it expires; a simultaneous refresh in two threads is harmless.
- **Alternatives considered**: one shared client with a lock (would serialise the requests and
  cancel out the parallelism).

## 3. Retries on 429 and 5xx

- **Decision**: keep using `execute(num_retries=RETRIES)` and `next_chunk(num_retries=...)`,
  with `RETRIES = 6`.
- **Rationale**: verified in the installed code (`googleapiclient/http.py`,
  `_should_retry_response` and `_retry_request`): it retries 5xx, 429 and 403 of type
  `rateLimitExceeded`, waiting `rand() * 2**n`. With 6 retries the maximum wait reaches 64 s,
  the ceiling Google recommends on its limits page.
- **Alternatives considered**: a custom request limiter (more code for a limit that is not
  reached with N ≤ 16).

## 4. Value of `GCHAT_WORKERS`

- **Decision**: integer, default 1, range 1–16; 4 recommended in the documentation.
- **Rationale**: 1 keeps the current behaviour (constitution V). The ceiling of 16 prevents a
  typo (`40`) from firing hundreds of requests per second.
- **Alternatives considered**: no ceiling (risk of the account being blocked); detecting the
  number of CPUs (irrelevant: the bottleneck is the network and the quota).

## 5. Common stop: disk brake and Ctrl-C

- **Decision**: a stop `threading.Event`. `check_free_space()` sets it when the brake trips;
  Ctrl-C in the main thread does too. Each thread checks it before starting a chat and before
  each attachment, and exits with its own exception. The executor is shut down with
  `cancel_futures=True` (Python 3.9+) so as not to start pending chats.
- **Rationale**: in Python only the main thread receives `KeyboardInterrupt`; without a common
  signal the threads would keep downloading after Ctrl-C or after the brake.
- **Alternatives considered**: daemon threads killed on exit (would leave half-written `.part`
  files, acceptable, but also unwritten JSON and no index).

## 6. Folders with the same name in parallel

- **Decision**: resolving the folder name and creating it (`mkdir`) happen inside a lock; the
  shared id → folder map is updated there.
- **Rationale**: the "this folder already exists" check and its creation have to be atomic, or
  two threads with same-named chats would pick the same one.

## 7. Dropbox "online-only"

- **Decision**: do not automate switching to "online-only"; document the Finder gesture. Keep
  the attachment existence check on `exists()` + `stat().st_size`.
- **Rationale**: on macOS 15.6, `fileproviderctl help` does not offer `evict` (measured
  2026-10-21), and Dropbox has no terminal command for it (its forums and its help only describe
  the Finder menu). Querying the metadata of a file without local content does not download it;
  reading it does. The script never reads an existing attachment.
- **Pending verification**: today there is no "online-only" file in Julio's Dropbox (0 of 59,893
  with the `dataless` flag, measured 2026-10-21), so the check with a real file stays in the
  quickstart.
- **Accepted trade-off**: on relaunch, the script reads each folder's `space.json` to recognise
  chats already exported and rewrites `messages.json`; those small JSON files get local content
  again. The attachments, which are 98% of the size, do not.

## 8. Measurement (2026-10-21)

- 20 spaces without attachments: 59 s with 1 thread, 19 s with 4 (×3.1), 0 retries.
- 4 spaces with attachments, one dominant (18 attachments): 44 s with 1 thread, 85 s with 4. The
  time is set by the slowest chat and its download latency varies between passes; there were no
  retries. Parallelism does not speed up a large chat internally; parallelising attachments
  within a chat stays outside this feature (it collides with the 15 reads/s per space if
  overused).

## 9. Readable progress with several threads

- **Decision**: `log()` under a lock; each line carries the global counter `[n/total]` and the
  chat name when starting and when finishing.
