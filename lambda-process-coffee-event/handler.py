from os import environ
import boto3
from slack_messages import slack_messages
from slack import notify_slack
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr

dynamo_region = environ['DYNAMODB_REGION']
dynamo_brew_table = environ['DYNAMODB_BREW_TABLE']

# TODO: from s3!
coffeemaker_config = {
    'Hki1': {
        'channel': '#helsinki',
        'brew_time': 300,
        'power_off_time': 2400
    },
    'Oulu1': {
        'channel': '#oulu',
        'brew_time': 300,
        'power_off_time': 7200    
    }
}

def format_timestamp(ts):
    """ Formats given timestamp as Iso8601 string"""
    return ts.strftime('%Y-%m-%dT%H:%M:%S.00Z')

def start_brew(table, slack_event_consumer, coffeemaker_id, start_time):
    table.put_item(Item={
        'coffeemakerId': coffeemaker_id,
        'startTime': start_time
    })
    slack_event_consumer(coffeemaker_id, slack_messages['brew_started'])

def end_brew(table, slack_event_consumer, coffeemaker_id, start_time, end_time):
    table.update_item(
        Key={'coffeemakerId': coffeemaker_id, 'startTime': start_time},
        UpdateExpression="set endTime = :end",
        ExpressionAttributeValues={':end': end_time})
    slack_event_consumer(coffeemaker_id, slack_messages['brew_ended'])

def check_coffeemaker_status(table, slack_event_consumer, coffeemaker_id, config, now):
    response = table.query(
    	KeyConditionExpression=Key('coffeemakerId').eq(coffeemaker_id),
    	ScanIndexForward=False,
		Limit=1)
    if len(response['Items']) == 0: return
    brew = response['Items'][-1]

    brew_ready = format_timestamp(now - timedelta(seconds=config['brew_time']))
    power_off = format_timestamp(now - timedelta(seconds=config['power_off_time']))

    if brew.get('endTime', None) == None and brew['startTime'] <= power_off:
        table.update_item(
            Key={'coffeemakerId': coffeemaker_id, 'startTime': brew['startTime']},
            UpdateExpression="set endTime = :end",
            ExpressionAttributeValues={':end': format_timestamp(now)})
        slack_event_consumer(coffeemaker_id, slack_messages['brew_timeout'])

    elif brew.get('doneTime', None) == None and brew['startTime'] <= brew_ready:
        table.update_item(
            Key={'coffeemakerId': coffeemaker_id, 'startTime': brew['startTime']},
            UpdateExpression="set doneTime = :done",
            ExpressionAttributeValues={':done': format_timestamp(now)})
        slack_event_consumer(coffeemaker_id, slack_messages['coffee_ready'])


def check_status(slack_event_consumer):
    table = boto3.resource('dynamodb', region_name=dynamo_region).Table(dynamo_brew_table)
    now = datetime.now()
    
    for coffeemaker_id, config in coffeemaker_config.items():
    	check_coffeemaker_status(table, slack_event_consumer, coffeemaker_id, config, now)

def out_of_coffee(slack_event_consumer, coffeemaker_id):
    slack_event_consumer(coffeemaker_id, slack_messages['out_of_coffee'])


def handler(event, context, slack_event_consumer = notify_slack):
    """
        expected event format:
        {
            eventType: string, [start|end|out-of-coffee|check-status], required
            coffeemakerId: string, id, required for start,end, out-of-coffee
            startTime: iso8601, required for start & end
            endTime: iso8601, required for end
        }
    """
    print("Received event:", event)
    event_type = event.get('eventType')

    table = boto3.resource('dynamodb', region_name=dynamo_region).Table(dynamo_brew_table)

    if event_type == 'start': start_brew(table, slack_event_consumer, event['coffeemakerId'], event['startTime'])
    elif event_type == 'end': end_brew(table, slack_event_consumer, event['coffeemakerId'], event['startTime'], event['endTime'])
    elif event_type == 'check-status': check_status(slack_event_consumer)
    elif event_type == 'out-of-coffee': out_of_coffee(slack_event_consumer, event['coffeemakerId'])
    elif event.get('source') == 'aws.events': check_status(slack_event_consumer)
    else: raise Exception("Unknown eventType:", event_type)

