# Индекс проекта

Репозиторий для экспериментов и обучения в области ИИ/LLM.

## Структура

- [cnn/](../cnn/) — CNN на PyTorch, распознавание MNIST (`cnn_mnist.py`)
- [local-llm-lab/](../local-llm-lab/) — клиент к локальным LLM (LM Studio, Ollama) через OpenAI-совместимый API (`main.py`); заметки по экспериментам в `NOTES.md`
- [obsidian-mcp/](../obsidian-mcp/) — MCP-сервер (read-only) поверх Obsidian vault: поиск и чтение заметок (`server.py`)

## Стек

- Python 3.11+, менеджер пакетов и окружения — uv
- ML/LLM: torch, torchvision, scikit-learn, transformers, datasets, accelerate, huggingface-hub
- Backend (для клиент-серверных экспериментов): Flask
- Frontend (для клиент-серверных экспериментов): Vue 3 + Vite — отдельный npm-проект, не часть uv-окружения

## Агенты

- `backend-dev` — серверный Python/Flask-код
- `frontend-dev` — клиентский Vue-код
- `code-reviewer` — ревью после реализации (обязателен перед завершением задачи)
