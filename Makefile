PYTHON ?= ./env/bin/python
MIG ?= $(PYTHON) scripts/manage_migrations.py
DB ?= $(PYTHON) scripts/db_ops.py

.PHONY: help check-db migrate-create-dev migrate-create-prod migrate-create-apply-dev migrate-create-apply-prod migrate-current-dev migrate-current-prod migrate-heads-dev migrate-heads-prod migrate-apply-dev migrate-apply-prod backup-all backup-dev backup-prod restore-dev restore-prod nightly-backup

help:
	@echo "Targets:"
	@echo "  make check-db"
	@echo "  make migrate-create-dev MSG='migration message'"
	@echo "  make migrate-create-prod MSG='migration message'"
	@echo "  make migrate-create-apply-dev MSG='migration message'"
	@echo "  make migrate-create-apply-prod MSG='migration message'"
	@echo "  make migrate-current-dev | migrate-current-prod"
	@echo "  make migrate-heads-dev   | migrate-heads-prod"
	@echo "  make migrate-apply-dev   | migrate-apply-prod"
	@echo "  make backup-all | backup-dev | backup-prod"
	@echo "  make restore-dev FILE=/abs/path/file.dump"
	@echo "  make restore-prod FILE=/abs/path/file.dump"
	@echo "  make nightly-backup"

check-db:
	$(DB) check --env all

migrate-create-dev:
	@test -n "$(MSG)" || (echo "Use: make migrate-create-dev MSG='migration message'" && exit 1)
	$(MIG) create --env dev -m "$(MSG)"

migrate-create-prod:
	@test -n "$(MSG)" || (echo "Use: make migrate-create-prod MSG='migration message'" && exit 1)
	$(MIG) create --env prod -m "$(MSG)"

migrate-create-apply-dev:
	@test -n "$(MSG)" || (echo "Use: make migrate-create-apply-dev MSG='migration message'" && exit 1)
	$(MIG) create --env dev -m "$(MSG)"
	$(MIG) apply --env dev

migrate-create-apply-prod:
	@test -n "$(MSG)" || (echo "Use: make migrate-create-apply-prod MSG='migration message'" && exit 1)
	$(MIG) create --env prod -m "$(MSG)"
	$(MIG) apply --env prod

migrate-current-dev:
	$(MIG) current --env dev --verbose

migrate-current-prod:
	$(MIG) current --env prod --verbose

migrate-heads-dev:
	$(MIG) heads --env dev --verbose

migrate-heads-prod:
	$(MIG) heads --env prod --verbose

migrate-apply-dev:
	$(MIG) apply --env dev

migrate-apply-prod:
	$(MIG) apply --env prod

backup-all:
	$(DB) backup --env all

backup-dev:
	$(DB) backup --env dev

backup-prod:
	$(DB) backup --env prod

restore-dev:
	@test -n "$(FILE)" || (echo "Use: make restore-dev FILE=/abs/path/backup.dump" && exit 1)
	$(DB) restore --env dev --file "$(FILE)"

restore-prod:
	@test -n "$(FILE)" || (echo "Use: make restore-prod FILE=/abs/path/backup.dump" && exit 1)
	$(DB) restore --env prod --file "$(FILE)"

nightly-backup:
	./scripts/nightly_backup.sh
