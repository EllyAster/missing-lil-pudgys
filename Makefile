.PHONY: help install test run docker-build docker-run clean

PYTHON ?= python
INPUT  ?= sample_data/missing_ids.txt
OUTPUT ?= output

help:
	@echo "Targets:"
	@echo "  install      Install dependencies into active venv"
	@echo "  test         Run tests"
	@echo "  run          Run with default sample data (set OPENSEA_API_KEY first)"
	@echo "  docker-build Build Docker image"
	@echo "  docker-run   Run via Docker (set OPENSEA_API_KEY first)"
	@echo "  clean        Remove output directory"

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest tests/ -v

run:
	python3 lilpudgys.run

docker-build:
	docker build -t lil-scan .

docker-run:
	docker run --rm \
		-e OPENSEA_API_KEY=$(OPENSEA_API_KEY) \
		-v $(PWD)/sample_data:/app/sample_data:ro \
		-v $(PWD)/output:/app/output \
		lil-scan \
		--input /app/sample_data/missing_ids.txt \
		--output /app/output \
		--download-images \
		--check-buyable

clean:
	rm -rf $(OUTPUT)
