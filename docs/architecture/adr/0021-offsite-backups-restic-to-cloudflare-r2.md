# ADR-0021: Off-machine backups with restic to a Cloudflare R2 bucket
- Status: Accepted (owner approved 2026-11-16) · Date: 2026-11-16 · Requirements: K-16, N-06
## Context
ADR-0017 gave us a tested dump and restore, but nothing runs them and the copies stay on the owner's PC. K-16
requires, before real questions are typed (M4): a daily copy of the database **and the uploaded pictures** (the
`assetdata` volume, which the dump does not contain) to a place outside the PC and outside the same account, and
a real restore tested. The copies hold personal data and real coaching content. The owner is a single person on a
Windows PC (Docker Desktop, Git Bash); nothing may depend on someone remembering to run it.
## Decision
- **Destination:** a private **Cloudflare R2** bucket, reached through its S3-compatible API with an API token limited
  to that one bucket (Object Read & Write). Free for the first 10 GB a month, no download fees.
- **Tool:** **restic**, run from a pinned Docker image (`restic/restic:0.18.1`), so nothing is installed on the PC.
  It encrypts on the PC before upload, stores only changed data, and applies the retention from ADR-0017's targets
  (14 daily, 8 weekly, 6 monthly) with `forget --prune`.
- **What is in a snapshot:** the database dump from `backup-db.sh` (unchanged: it still refuses a role that cannot
  bypass row-level security) and the `assetdata` volume, mounted read-only. The plain dump exists only in an ignored
  folder for the duration of the run and is removed on exit, success or failure.
- **Safety rules in the script:** the backup store is created only by an explicit `--init` (a typo cannot create a
  fresh empty store); the pictures volume must already exist (Docker would otherwise create an empty one and the
  backup would "succeed" without pictures); every run lists the new snapshot to confirm the dump is in it and then
  reads a 2% sample of the stored data back (`check --read-data-subset`).
- **Restore** goes only into a new folder, reads every file back (`restore --verify`), checks the dump's checksum,
  and leaves switching to the restored copy to the existing, deliberate steps of ADR-0017.
- **Schedule and alerting:** Windows Task Scheduler runs the script daily (`StartWhenAvailable` catches a missed day);
  an optional healthchecks.io-style address is pinged on start, success and failure and emails the owner when a day
  passes with no success.
- **Proof:** `infra/scripts/offsite-drill.sh` runs the real scripts against throwaway PostgreSQL, a throwaway volume
  and a local S3 server in place of R2, and compares what comes back; CI runs it on every change.
- **Secrets:** the R2 key, the restic password and the monitoring address live in `.env.offsite` (ignored by Git) and
  in the owner's password manager. They are never committed, logged or sent anywhere but their own service.
## Consequences
+ Daily, off-machine, encrypted, deduplicated, retention-managed, and restored by the same tool; cost is zero at current size.
+ The cloud provider and anyone who gets the bucket see only ciphertext.
+ The whole chain is tested in CI except the provider itself; R2 is proven by the owner's first `--init` and real restore.
− The R2 token and restic password sit in plain text on the PC; whoever controls the PC can also delete the backups
  (no bucket lock, because restic must delete and rewrite files when it tidies).
− The PC must be on, signed in and running Docker at the scheduled time; missed days are caught only by the monitoring email.
− Losing the restic password loses every backup. It must be in the password manager.
− RPO stays at 24 hours until M7 (ADR-0017).
## Alternatives considered
- **Backblaze B2 + restic:** equally suitable (about US$7/TB/month, object lock available); R2 chosen by the owner.
- **Google Drive / OneDrive via rclone:** free tiers are small, sign-in tokens expire and silently stop the job, and a
  sync can copy damage across.
- **External disk kept elsewhere:** cannot run itself. Stays useful as an occasional extra copy.
- **AWS S3 (Mumbai):** most mature, but billing and permissions are heavier than this needs; restore downloads cost money.
- **Our own script around `pg_dump` + `aws s3 cp`:** no encryption, deduplication or retention without rebuilding what restic already does well.
