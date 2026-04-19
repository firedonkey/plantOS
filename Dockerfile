FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

COPY platform/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY platform ./platform

WORKDIR /app/platform
RUN mkdir -p data/uploads

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
