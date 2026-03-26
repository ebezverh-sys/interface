FROM python:3.13-slim

# установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /interface

# установка зависимостей
COPY pyproject.toml uv.lock* ./

# создаём виртуальное окружение
RUN uv sync --locked

# копируем кода приложения
COPY . .

# добавляем виртуальное окружение в PATH
ENV PATH="/interface/.venv/bin:$PATH"

# порт
EXPOSE 8501

# команда запуска
CMD ["streamlit", "run", "Home.py", "--server.address=0.0.0.0", "--server.port=8501"]
