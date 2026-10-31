.PHONY: help install sample-data ingest test e2e run-backend run-frontend clean

help:
	@echo "PortXFolio Development Commands:"
	@echo "  make sample-data   - Generate synthetic historical dataset if missing"
	@echo "  make ingest        - Run idempotent stock data ETL pipeline"
	@echo "  make test          - Run Pytest test suite"
	@echo "  make run-backend   - Start FastAPI REST API server (port 8000)"
	@echo "  make run-frontend  - Start Streamlit UI application (port 8501)"

sample-data:
	python scripts/generate_sample_data.py

ingest:
	python scripts/ingest_csv.py
	python scripts/seed_data.py

test:
	python -m pytest -v tests/

run-backend:
	uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

run-frontend:
	streamlit run app.py --server.port 8501
