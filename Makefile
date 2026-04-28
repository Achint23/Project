.PHONY: setup run clean doctor test

setup:
	uv sync
	@echo "✓ Dependencies installed. Copy .env.local.example to .env.local and add your NVIDIA_API_KEY."

run:
	uv run streamlit run app.py

clean:
	rm -rf .venv __pycache__ core/__pycache__ tests/__pycache__ data/uploads data/cache data/chroma
	@echo "✓ Cleaned."

doctor:
	@echo "=== DocBot Environment Check ==="
	@uv run python -c "from core.config import get_settings; s = get_settings(); print(f'  API Key  : {s.nvidia_api_key[:8]}...{s.nvidia_api_key[-4:]}'); print(f'  Base URL : {s.nvidia_base_url}'); print(f'  Model    : {s.nvidia_model}'); print(f'  Route    : {s.nvidia_route_model}'); print(f'  Embed    : {s.nvidia_embed_model}'); print('✓ Config OK')"
	@echo "Running NIM connectivity smoke test..."
	@uv run pytest tests/test_smoke_nim.py::test_json_mode_roundtrip -x -q
	@echo "✓ Doctor passed — environment is healthy."

test:
	uv run pytest tests/ -x -q
