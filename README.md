# smart-db-migrator

Serwis do zarzadzania migracjami SQLAlchemy/Alembic dla `smart_common` z dwoma oddzielnymi srodowiskami:
- `dev` (`migrations/dev`)
- `prod` (`migrations/prod`)

## Co robi
- korzysta z `smart_common` jako submodulu
- wykrywa zmiany w modelach SQLAlchemy (`smart_common/models`)
- tworzy migracje osobno dla `dev` i `prod`
- aplikuje migracje osobno dla `dev` i `prod`
- umozliwia promocje rewizji z `dev` do `prod`
- pokazuje diff zmian w `smart_common/models` wzgledem np. `origin/develop`

## Szybki start

1. Zainicjalizuj submodul:
```bash
git submodule update --init --recursive
```

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

Przyklad w `.env.example`.

## Komendy

### Tworzenie migracji
```bash
python scripts/manage_migrations.py create --env dev -m "add provider column"
python scripts/manage_migrations.py create --env prod -m "manual prod migration"
```

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

## Docker

Podglad pomocy:
```bash
docker compose run --rm db-migrator
```

Przyklad utworzenia migracji:
```bash
docker compose run --rm db-migrator create --env dev -m "new migration"
```

