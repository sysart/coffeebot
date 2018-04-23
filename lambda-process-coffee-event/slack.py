import json
from botocore.vendored import requests

# TODO: this cannot go into git!
slack_urls = {
    'Hki1': "TODO"
}

# TODO: create log group
# TODO: add cloudwatch trigger

def notify_slack(coffeemaker_id, message):

    response = requests.post(slack_urls[coffeemaker_id], 
        data=json.dumps({'text': message}),
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )
