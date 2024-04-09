FROM python:3.10-slim-buster

WORKDIR /app

COPY requirements.txt .
COPY main.py .

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 5987

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5987"]