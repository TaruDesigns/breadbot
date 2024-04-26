- [1. BreadBot](#1-breadbot)
  - [1.1. Why](#11-why)
  - [1.2. How](#12-how)
  - [1.3. Running and developing it](#13-running-and-developing-it)
- [2. Planned features](#2-planned-features)


# 1. BreadBot

Discord bot that sees your bread and confirms that it is, in fact, bread, using computer vision. Based on discord.py.

## 1.1. Why

It's a fun project

## 1.2. How

The `.envexample` file includes the environment variables needed for this to work. Currently, it uses Roboflow's pre-trained models to do the inference, but custom models that run locally will be added soon.

It reads messages and filters based on channel and user that sent the message. The attachments are downloaded and inference is performed to estimate labels and segmentation.

## 1.3. Running and developing it

Use `docker compose` to deploy locally. The image is deployed with the code attached as auto-reload, so changes can be published immediately when files are modified.

Additionally, the `haoss` folder contains a sample configuration to deploy this as a Home Assistant addon


# 2. Planned features

- Size estimation of bread
~~- Roundness estimation of bread~~
- Admin panel (based on FastAPI) -> In Progress, basic endpoints created
- ~~Proper async inference with a "BreadBot is typing..." message for better UX~~ Done