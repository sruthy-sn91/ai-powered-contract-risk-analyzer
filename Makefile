# ----- Config -----
PY := python
PIP := pip
VENV := .venv
ACT := . $(VENV)/bin/activate
UVICORN := uvicorn
STREAMLIT := streamlit
API_APP := backend.main:app
ST_HOME := frontend/streamlit_app/Home.py

# ----- Targets -----
.PHONY: setup run seed validate-data index train-lora policy-validate fmt test

setup:
	@test -d $(VENV) || python -m venv $(VENV)
	@$(ACT); $(PIP) install --upgrade pip
	@$(ACT); $(PIP) install -r requirements.txt
	@$(ACT); $(PIP) install -r requirements-dev.txt || true
	@echo "✅ Environment ready. Next: cp .env.template .env"

run:
	@$(ACT); \
	echo "Starting FastAPI on http://127.0.0.1:8000 and Streamlit on http://127.0.0.1:8501"; \
	(API_URL=http://127.0.0.1:8000 $(UVICORN) $(API_APP) --host 0.0.0.0 --port 8000 --reload & \
	API_URL=http://127.0.0.1:8000 $(STREAMLIT) run $(ST_HOME) --server.port 8501 --server.headless true); \
	trap 'pkill -f "$(API_APP)"; pkill -f "streamlit run";' EXIT

validate-data:
	@$(ACT); $(PY) -m scripts.validate_data

seed:
	@$(ACT); $(PY) -m scripts.seed_demo

index:
	@$(ACT); $(PY) -m scripts.build_indices

train-lora:
	@$(ACT); $(PY) -m models.lora_finetune_cuad --subset_size 200

policy-validate:
	@$(ACT); $(PY) -m scripts.policy_validate --policy policies/policy.example.yaml --schema policies/schema.yaml

fmt:
	@$(ACT); black .

test:
	@$(ACT); pytest -q
