FROM python:3-slim

WORKDIR /usr/src/app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

COPY . .

CMD ["gunicorn", "main:app", "-b", "0.0.0.0:8000"]
