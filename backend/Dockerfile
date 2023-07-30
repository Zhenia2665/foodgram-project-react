FROM python:3.9.13
WORKDIR /backend

RUN pip install --upgrade pip

COPY . .

RUN pip install -r requirements.txt --no-cache-dir

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
