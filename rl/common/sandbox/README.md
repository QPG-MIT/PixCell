# Candidate execution image

Track A keeps the networked Tinker process outside this image. Each sampled
program runs in a new container made from this image with:

- no network namespace;
- a read-only root filesystem;
- no capabilities in the candidate process and `no-new-privileges`;
- fixed memory, CPU, process, open-file, and output-size limits;
- a read-only input mount containing `device.py`, the runner, and Docker's
  candidate-ID control file;
- size-bounded tmpfs mounts for `/work` and `/tmp`;
- forced removal after every evaluation.

A small immutable supervisor starts as root with only `SETUID`, `SETGID`, and
`KILL`, launches the candidate under a candidate-specific non-root UID, and
writes the real child wait status to a root-only tmpfs. This prevents the
program from forging successful completion. Runner and supervisor sources
are both included in the image-spec digest checked at launch.

Build the image locally:

```bash
python rl/common/sandbox/build.py
```

The command prints an immutable image-ID export. Set it in the launch shell
before RL or checkpoint evaluation. Mutable image tags are rejected. The exact
resolved image ID is checked by preflight and recorded in evaluation
provenance.

The Dockerfile base is pinned by repository digest. Package requirements pin
the geometry stack used by the public dataset. The resulting image ID, rather
than the local tag, is the runtime identity.
