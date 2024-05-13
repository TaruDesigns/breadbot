# Using ultralytics dockerimage for GPU support
#FROM ultralytics/ultralytics:latest

# Use the official Python image only if you want to manually install all dependencies
#FROM python:3.10-slim-buster
# If using default python image, these dependencies should be installed
#RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 libglib2.0-0 libxrender1 libgl1  -y

# Using ultralytics without GPU
FROM ultralytics/ultralytics:latest-cpu

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the container
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the local code to the container
#COPY . .

COPY apiroutes ./apiroutes
COPY breadinfer ./breadinfer
COPY discordroutes ./discordroutes
COPY yolov8/trainedmodels ./yolov8/trainedmodels
COPY main.py .

# Copy the .env file

COPY ./.env .

# Expose the port that FastAPI is running on
EXPOSE 5987

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5987", "--reload"]