# carousell-search

Getting near real-time notifications on Carousell.

## Requirements

Python 3+

## Installing

1. `pip3 install -r requirements.txt`

2. Create database by running python script "createDB.py"
    `cd Database`
    `python3 createDB.py`

## Configuring

Configure `configuration.py` with 
- your Slack token from https://api.slack.com/tokens
- your Slack channel
- search queries in `ITEMS`

Ensure that your Slack app has the correct permissions to post in channel


## Creating Docker image
docker build --no-cache -t koston411/carousell_alerts:v1.1 .

## Running Docker image the first time
## is it necessary to have -it -d as arguments?
docker run -v /Users/erwan/Documents/Workspace/Carousell\ Alerts/:/usr/src/app --name carousell_alerts -it -d koston411/carousell_alerts:v1.1

## Push image to Docker Hub
docker push koston411/carousell_alerts:v1.1

<!-- ACCESS INSIDE THE CONTAINER -->
## SSH in the container
docker exec -it carousell_alerts /bin/bash

## Running program in the container
`python3 main.py`