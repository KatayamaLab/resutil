# Review fixes and compatibility

- Transfers validate experiment names and directories before any destructive operation.
  Local symlinks and archive traversal are rejected. Downloads are staged before publication.
- Legacy dependency paths are normalized on read; new metadata stores experiment identifiers.
  The coordinator visits cyclic graphs once and observes worker exceptions.
- Successful transfers save a content receipt in results/.resutil-sync.json for each destination.
  Missing receipts and modified data are treated as unsynced, including final results after a checkpoint.
  Old experiments without receipts are conservatively uploaded once.
  This tracks local changes; edits made by another client to the remote archive are not detected.
- Explicit push can overwrite an existing remote experiment. Bulk push and the TUI skip
  experiments whose local content matches the last successful transfer.
- rm requires confirmation unless --yes is passed. --local works without storage credentials.
- comment retains directory renaming. It updates local metadata and remote archive references.
  Because the remote API has no dependency index, this reads remote archives before renaming.
  The original remote target remains available until updated references have been saved.
  Other clients' existing local copies keep their previous names and metadata.
- User exceptions, interrupts and SystemExit retain their exit semantics after best-effort
  result upload. Successful computation with failed final upload raises an error.
  Checkpoint failure returns False and does not abort computation.
- NO_REMOTE and DEBUG skip storage authentication and all uploads. Debug output is held
  in a unique temporary directory and removed when the wrapped call finishes.
- Configuration paths resolve relative to the config file; the process cwd is unchanged.
- Metadata, configuration and text files use UTF-8. Comments are limited to 200 UTF-8 bytes.
- RESUTIL_TIMEZONE accepts an IANA zone, such as Asia/Tokyo. The default is the local zone.
  started_at includes the UTC offset; the alphabetical identifier uses UTC elapsed minutes.
- Git snapshots include untracked files and deletion records; a first commit is optional.
- Google Drive operations are serialized, lists are paginated and project folders are scoped
  to the configured parent. Existing archives are updated in place rather than deleted first.
- Server credentials are bound to their originating URL. Expiring tokens are refreshed on
  requests; a 401 triggers one refresh/retry. URL path components are encoded.
- Login callbacks require an unpredictable state and ignore unrelated requests until timeout.
  The server must preserve the state parameter from /auth/login to /auth/signin and /callback.
  Apply server-login-state.patch in the resutil-server checkout and deploy the updated server
  before using the new login command. Older servers fail safely rather than accepting an
  unbound callback. Existing matching credentials can still be used and refreshed.
- Tests use temporary directories, in-memory storage, mocked Google clients and HTTP transports.
  Real cloud storage is not contacted.

Related issues: #20, #28, #29, #31, #33, #34, #37, #39, #41, #45.
The architecture-only request #15 is intentionally outside this bug-fix scope.
Windows readline dependency (#36), keyless server authentication (#44) and the TUI (#27)
already exist; their surrounding error handling and documentation are covered here.
