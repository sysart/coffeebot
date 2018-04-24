import json
from os import environ
from botocore.vendored import requests

# TODO: create log group
# TODO: add cloudwatch trigger

def notify_slack(coffeemaker_id, message):

    response = requests.post(environ['SLACK_URL_' + coffeemaker_id.upper()],
        data=json.dumps({'text': message}),
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )
