.PHONY: install-public deploy up down logs status test lint-shell

install-public:
	./deployment/install_public.sh

deploy:
	./deployment/deploy.sh

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f dashboard

status:
	docker compose ps

test:
	pytest -q

lint-shell:
	bash -n deployment/deploy.sh deployment/entrypoint.sh deployment/install_public.sh deployment/resolve_merge_conflicts.sh
