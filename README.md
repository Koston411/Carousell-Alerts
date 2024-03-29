# carousell-search

Getting near real-time notifications on Carousell.

## Requirements

Python 3.8

## Installing

1. `pyenv install 3.8`
   `pyenv local 3.8.x`

2. Initiate venv
    `pyenv python -m venv .venv`
    `source .venv/bin/activate`

3. `pip install -r requirements.txt`

4. Create database by running python script "createDB.py"
    `cd Database`
    `python createDB.py`

## Configuring slack (if needed)

Configure `configuration.py` with 
- your Slack token from https://api.slack.com/tokens
- your Slack channel
- search queries in `ITEMS`

Ensure that your Slack app has the correct permissions to post in channel


## Creating Docker image
docker build --no-cache -t koston411/carousell_alerts:v1.2 .

## Running Docker image the first time
## is it necessary to have -it -d as arguments?
docker run -v /Users/erwan/Documents/Workspace/Carousell\ Alerts/:/usr/src/app --name carousell_alerts -it -d koston411/carousell_alerts:v1.2

## Push image to Docker Hub
docker push koston411/carousell_alerts:v1.2

<!-- ACCESS INSIDE THE CONTAINER -->
## SSH in the container
docker exec -it carousell_alerts /bin/bash

## Running program in the container
`python3 main.py`

<!-- Enhancements to be worked on -->
- Once a group chat is deleted, the application should delete the associated listings which are orpheans