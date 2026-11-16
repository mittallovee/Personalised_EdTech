# Off-machine backups (K-16)

> Requirement **K-16** · Decision: [ADR-0021](../architecture/adr/0021-offsite-backups-restic-to-cloudflare-r2.md) (builds on
> [ADR-0017](../architecture/adr/0017-backups-and-restore.md); the dump and restore tools are described in
> [backup-and-restore.md](./backup-and-restore.md)).

## What it does, in plain words

Once a day, a script on your PC:

1. takes a **database backup** (the same `backup-db.sh` as before, with its row-level-security safety check);
2. adds the **uploaded pictures** (the Docker volume `assetdata`, which the database backup does not contain);
3. **encrypts** both on your PC with **restic** (a free, widely used backup tool) and uploads them to a private
   **Cloudflare R2 bucket** (R2 is Cloudflare's cloud file storage; it speaks the same protocol as Amazon S3);
4. throws away copies past the retention (14 daily, 8 weekly, 6 monthly), and reads part of the stored data
   back to check it is not damaged;
5. tells a **monitoring address** it worked. If a day passes without that message, you get an email.

Only encrypted data leaves the PC. Cloudflare never sees a readable question, name or picture. restic stores
only what changed since the last run, so a daily copy of a bank that rarely changes stays small.

## Set it up once (you; about 30 minutes)

I cannot create accounts or keys for you, and the keys must not pass through chat. Everything below you do yourself.

### 1. Cloudflare R2

1. In the [Cloudflare dashboard](https://dash.cloudflare.com/), open **R2 object storage** and enable it. Cloudflare
   may ask for a payment method even though the first 10 GB a month are free; at this size the cost should be zero or cents.
2. **Create bucket**, for example `qbank-backups`. Leave it private (never connect a public domain to it).
3. **Manage R2 API tokens** → **Create API token**. Permission **Object Read & Write**, **Apply to specific buckets
   only** → your bucket. Copy the **Access Key ID** and **Secret Access Key** now (the secret is shown once).
4. Note your **account ID** (shown on the R2 overview page).

### 2. The settings file

In the repository folder, copy the example and fill it in. The file `.env.offsite` is ignored by Git:

```bash
cp infra/backup/offsite.env.example .env.offsite
openssl rand -base64 32      # prints a random password: use it as RESTIC_PASSWORD
```

Put these in your **password manager** as well: the restic password, and the R2 keys. **If the restic password is
lost, the backups cannot be opened by anyone, including you.** Never paste these values into chat, an issue or a PR.

### 3. Monitoring (recommended)

Create a free account at [healthchecks.io](https://healthchecks.io), add a check with **period 1 day** and **grace
6 hours**, and copy its ping address into `HEALTHCHECK_URL`. Any similar "dead man's switch" service works.

### 4. Create the store, then take the first backup

With the app running (`docker compose up -d`):

```bash
infra/scripts/backup-offsite.sh --init     # once: creates the encrypted store in the bucket
infra/scripts/backup-offsite.sh            # the first real backup
infra/scripts/restore-offsite.sh list      # shows the snapshot you just made
```

### 5. Make it run every day

In **PowerShell**, adjust the folder name if yours differs. `StartWhenAvailable` means a run missed because the PC
was off happens as soon as it is on again:

```powershell
$bash     = "C:\Program Files\Git\bin\bash.exe"
$action   = New-ScheduledTaskAction -Execute $bash -Argument '-lc "cd /d/Persolanised_EdTech_local && infra/scripts/backup-offsite.sh"'
$trigger  = New-ScheduledTaskTrigger -Daily -At 2:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName "qbank offsite backup" -Action $action -Trigger $trigger -Settings $settings
```

The task runs while you are signed in, and **Docker Desktop must be running** (set Docker Desktop to start when you
sign in). If either is not true the run fails and the monitoring address emails you. Check it once by hand:
right-click the task in *Task Scheduler* → **Run**, then look at the end of `backups/offsite-backup.log`.

## Every day: nothing. Sometimes: look

- `backups/offsite-backup.log` records each run (it never contains passwords or keys).
- `infra/scripts/restore-offsite.sh list` lists the snapshots in the bucket.
- An email from the monitoring service means a run did not finish. Read the end of the log; run the script by hand.

## Restore (and the real restore test K-16 asks for)

A restore always goes into a **new folder**, then into a **new database and volume**. It never overwrites live data.

```bash
infra/scripts/restore-offsite.sh latest backups/restored-test     # or an id from "list"
```

It downloads, decrypts, reads every file back to check it, and checks the database dump against its checksum. Then
it prints the two commands that put the data into use: `restore-db.sh` for the database (see
[backup-and-restore.md](./backup-and-restore.md) for switching to the restored copy) and a copy into a new Docker
volume for the pictures.

**Do this once with real data, before real questions matter, and record it:**

| Date | Snapshot | Size | Time to restore | Checked (sign in to the restored copy, open a picture) | By |
|---|---|---|---|---|---|
| _to be filled in by the owner_ | | | | | |

If you lose the PC, the steps are the same on a new one: install Docker Desktop and Git, clone the repository,
write `.env.offsite` again from your password manager, and run `restore-offsite.sh`.

## The checks that keep this honest

`infra/scripts/offsite-drill.sh` runs the whole chain with a throwaway PostgreSQL, throwaway pictures and a local S3
server instead of R2, and CI runs it on every change ("Off-site backup drill"). It checks that: a backup before the
store exists is refused; a second backup works; a wrong password cannot open the store; a wrong volume name is
refused (Docker would otherwise create an empty one and "back up" nothing); a restore refuses a non-empty folder;
restored pictures are byte-identical; the restored database has every row, including those added between backups;
and the plain dump is not left on disk. Run it yourself any time: `bash infra/scripts/offsite-drill.sh`.

It cannot test Cloudflare itself. Step 4 above (`--init`, a backup, `list`) and your restore test are what prove R2.

## What this does not protect against

- **The PC and its keys.** `.env.offsite` holds the R2 key and restic password in plain text on your PC, and the
  token can delete backups. Someone who controls your Windows account can ruin the backups too. Protect the account
  (strong password, disk encryption such as BitLocker). R2 can lock objects against deletion, but restic must delete
  and rewrite files when it tidies, so locks are not used; a periodic second copy to an external disk kept elsewhere
  is the extra safety if you want it.
- **Up to 24 hours of changes** (one backup a day). That is the agreed target until M7 (point-in-time recovery).
- **A PC that is off for days.** Nothing runs; the monitoring email is how you find out.
- **Secrets other than these.** `.env` and any other key file are yours to keep in the password manager.

## Rotating a key

Create a new R2 token for the bucket, put it in `.env.offsite`, run `backup-offsite.sh` once to prove it works, then
delete the old token in Cloudflare. The restic password is changed with `restic key` (ask me first; it is
rarely needed and easy to get wrong).

## Cost

R2's free allowance is 10 GB of storage a month, and downloading (egress) is free, so a restore costs nothing.
Beyond 10 GB the rate at the time of writing is about US$0.015 per GB a month; check
[R2 pricing](https://developers.cloudflare.com/r2/pricing/) for the current figure.
