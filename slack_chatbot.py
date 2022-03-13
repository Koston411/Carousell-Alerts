import json
import requests
from pickle import FALSE
from slack_sdk.webhook import WebhookClient

def slack_post_message(item):	
	slack_data = {
		"blocks": [
            {
			    "type": "header",
			    "text": {
				    "type": "plain_text",
				    "text": (item.title[:147] + '...') if len(item.title) > 147 else item.title, 
				    "emoji": True
			    }
		    },
		    {
			    "type": "section",
			    "text": {
				    "type": "mrkdwn",
				    "text": "*Price:* " + item.price + "\n*Seller:* " + item.seller + "\n*<" + item.url + "|Open listing>*\n"
			    },
			    "accessory": {
				    "type": "image",
    				"image_url": item.image,
	    			"alt_text": ""
		    	}
		    }
	    ]
    }

	webhook_url = "https://hooks.slack.com/services/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"
	response = requests.post(
        webhook_url, data=json.dumps(slack_data),
        headers={'Content-Type': 'application/json'}
    )
    
	if response.status_code != 200:
		raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )