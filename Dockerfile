FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory for persistence
RUN mkdir -p /app/data

VOLUME ["/app/data"]

CMD ["python", "main.py"]
