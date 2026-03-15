# smart-db-migrator

Serwis do zarzadzania migracjami SQLAlchemy/Alembic dla `smart_common` z dwoma oddzielnymi srodowiskami:

- `dev` (`migrations/dev`)
- `prod` (`migrations/prod`)

Modele SQLAlchemy sa ladowane z checkoutu `smart-common`. Migrator szuka ich kolejno w:
- `./smart_common`
- `../smart-common`
- `../smart_common`

Mozesz tez jawnie ustawic `SMART_COMMON_PATH` w `.env`.

## Co robi

- korzysta z `smart_common` jako submodulu
- wykrywa zmiany w modelach SQLAlchemy (`smart_common/models`)
- tworzy migracje osobno dla `dev` i `prod`
- aplikuje migracje osobno dla `dev` i `prod`
- umozliwia promocje rewizji z `dev` do `prod`
- pokazuje diff zmian w `smart_common/models` wzgledem np. `origin/develop`

## Szybki start

1. Jesli naprawde chcesz uzyc submodulu, zainicjalizuj tylko `smart_common`:

```bash
git submodule update --init smart_common
```

Rekomendowany wariant:

```bash
export SMART_COMMON_PATH=/home/mpielak/Pulpit/home/smart-common
```

To omija lokalny submodule i zawsze bierze modele z glownego checkoutu `smart-common`.

2. Przygotuj env:

```bash
cp .env.example .env
```

3. Zainstaluj zaleznosci:

```bash
pip install -r requirements.txt
```

## Zmienne srodowiskowe

Minimalnie wymagane:

- `DB_URL_DEV`
- `DB_URL_PROD`
- opcjonalnie `SMART_COMMON_PATH`

Przyklad w `.env.example`.

## Komendy

### Tworzenie migracji

```bash
python scripts/manage_migrations.py create --env dev -m "add provider column"
python scripts/manage_migrations.py create --env prod -m "manual prod migration"
```

Domyslnie `create` nie kopiuje plikow do `versions_archive`.
Jesli chcesz archiwum, dodaj `--archive`.

### Aplikowanie migracji

```bash
python scripts/manage_migrations.py apply --env dev
python scripts/manage_migrations.py apply --env prod
```

### Podglad stanu

```bash
python scripts/manage_migrations.py current --env dev
python scripts/manage_migrations.py heads --env dev
python scripts/manage_migrations.py history --env dev --rev-range base:head
```

### Promocja migracji dev -> prod

```bash
# domyslnie bierze najnowsza rewizje z dev
python scripts/manage_migrations.py promote

# albo konkretna rewizje (prefix id)
python scripts/manage_migrations.py promote --revision 633c213f079c
```

Po promocji odpal:

```bash
python scripts/manage_migrations.py apply --env prod
```

### Sledzenie zmian modeli

```bash
python scripts/manage_migrations.py models-diff --base origin/develop
```

## Podstawowe operacje (najprosciej przez Makefile)

```bash
make migration-dev MESSAGE="add provider power source"
make migration-prod MESSAGE="add provider power source"
make apply-dev
make apply-prod
make current-dev
make current-prod
make heads-dev
make heads-prod
make history-dev
make history-prod
make doctor-dev
make doctor-prod
make repair-dev TO=c91b4d3a7e10 FROM=70c809c27c09
make repair-prod TO=<revision> FROM=<broken_revision>
make promote
make check-db
make migrate-create-dev MSG="add provider power source"
make migrate-create-prod MSG="add provider power source"
make migrate-current-dev
make migrate-current-prod
make migrate-heads-dev
make migrate-heads-prod
make migrate-apply-dev   ####TODZIAŁA
make migrate-apply-prod
make migrate-create-apply-dev MSG="add provider power source"
make migrate-create-apply-prod MSG="add provider power source"
make backup-all
make backup-dev
make backup-prod
make restore-dev FILE=/abs/path/to/backup.dump
make restore-prod FILE=/abs/path/to/backup.dump
```

## Backup i restore

Skrypt:

```bash
python scripts/db_ops.py backup --env all
```

Co robi:

- laduje `.env`
- robi dump `dev` i `prod` do `backups/YYYY/MM/*.dump`
- opcjonalnie weryfikuje dump (`pg_restore --list`)
- opcjonalnie wysyla backup na Google Drive przez `rclone`
- usuwa stare backupy wg retencji

Konfiguracja przez `.env`:

- `BACKUP_ROOT` (domyslnie `./backups`)
- `BACKUP_RETENTION_DAYS` (domyslnie `14`)
- `BACKUP_VERIFY` (`1` lub `0`, domyslnie `1`)
- `RCLONE_REMOTE` (np. `gdrive:smart-db-migrator`)

Restore:

```bash
# restore z dump custom
python scripts/db_ops.py restore --env dev --file /abs/path/to/backup.dump

# restore z SQL plain
python scripts/db_ops.py restore --env dev --file /abs/path/to/backup.sql
```

Szybki test polaczen:

```bash
python scripts/db_ops.py check --env all
```

## Nocny backup w schedulerze

Przyklad crona (codziennie 02:30):

```bash
30 2 * * * cd /home/mpielak/Pulpit/Projekty_Django/smart_energy/smart-db-migrator && /bin/bash ./scripts/nightly_backup.sh >> /tmp/smart-db-backup.log 2>&1
```

Albo systemd timer (rekomendowane):

```bash
sudo cp deploy/systemd/smart-db-backup.service /etc/systemd/system/
sudo cp deploy/systemd/smart-db-backup.timer /etc/systemd/system/

# Zmien WorkingDirectory/EnvironmentFile/ExecStart w pliku .service na swoja sciezke.

sudo systemctl daemon-reload
sudo systemctl enable --now smart-db-backup.timer
sudo systemctl status smart-db-backup.timer
```

## Docker

Podglad pomocy:

```bash
docker compose run --rm db-migrator
```

Przyklad utworzenia migracji:

```bash
docker compose run --rm db-migrator create --env dev -m "new migration"
```

## Naprawa zerwanej historii Alembica

Jesli baza ma w `alembic_version` rewizje, ktorej nie ma juz w lokalnym repo, uzyj:

```bash
make doctor-dev
make repair-dev TO=c91b4d3a7e10 FROM=70c809c27c09
make apply-dev
```

`repair-dev` robi swiadoma naprawe wpisu `alembic_version` bez recznego SQL.
