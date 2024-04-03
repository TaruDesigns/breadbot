# Use the official Python image
FROM python:3.9-slim

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 libglib2.0-0 libxrender1 libgl1  -y
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
COPY . .

# Expose the port that FastAPI is running on
EXPOSE 5987


# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5987", "--reload"]