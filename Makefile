.PHONY: check lint format typecheck test

check: lint format typecheck

lint:
	uv run ruff check .

format:
	uv run ruff format --check .

typecheck:
	uv run mypy .

test:
	uv run pytest

fix:
	uv run ruff check --fix .
	uv run ruff format .
