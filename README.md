- [1. BreadBot](#1-breadbot)
  - [1.1. Why](#11-why)
  - [1.2. How](#12-how)
- [2. Features (planned and developed)](#2-features-planned-and-developed)
- [3. Running it locally](#3-running-it-locally)
  - [3.1. Using docker](#31-using-docker)
  - [3.2 Using venv](#32-using-venv)


# 1. BreadBot

Discord bot that sees your bread pics and confirms that it is, in fact, bread, using computer vision. Based on discord.py using YOLOv8

## 1.1. Why

It's a fun project

## 1.2. How

Bot reads messages and filters based on channel and user that sent the message. The attachments are downloaded and inference using YOLOv8 is performed to estimate labels and segmentation. Bot replies to the original message with a descritpion and segmented image.

# 2. Features (planned and developed)

~~- Roundness estimation of bread~~ Done
- Admin panel (based on FastAPI) -> In Progress, basic endpoints created
- ~~Proper async inference with a "BreadBot is typing..." message for better UX~~ Done
- Optimize inference models -> Planned

# 3. Running it locally

## 3.1. Using docker

Docker is the preferred method, it's [published on dockerhub](https://hub.docker.com/r/taruelec/breadbot). Note that this image is built for CPU-only deployments. You will need to supply a .env file. The `.envexample` shows the variables you need to supply

```bash
docker pull taruelec/breadbot
docker run --env-file ./.env taruelec/breadbot
``` 

Alternatively, you can use docker compose:

```yaml
services:
  breadbot:
    build: . # Use this for development
    image: taruelec/breadbot # Use this for deployment
    ports:
      - "5987:5987"
    volumes: # Only use this for local development with autoreload
      - "./:/app" # Only use this for local development with autoreload
    env_file:
      - .env
``` 

## 3.2 Using venv

If you don't want to use docker, you can deploy it locally, however, keep in mind that you'll need to install a couple of extra dependencies:

```
opencv-contrib-python-headless==4.8.0.74
ultralytics
``` 

On top of that, depending on your OS, you might need to install additional system dependencies to support opencv/torch
` apt-get update && apt-get install ffmpeg libsm6 libxext6 libglib2.0-0 libxrender1 libgl1  -y`
