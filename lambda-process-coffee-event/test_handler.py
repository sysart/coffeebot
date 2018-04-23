import handler
import os
import pytest
import boto3
from slack_messages import slack_messages
from datetime import datetime, timedelta
from moto import mock_dynamodb2
from boto3.dynamodb.conditions import Key, Attr

def createTable():
    conn = boto3.resource('dynamodb', region_name=os.environ['DYNAMODB_REGION'])
    return conn.create_table(TableName=os.environ['DYNAMODB_BREW_TABLE'],
    KeySchema=[ 
        { 'AttributeName': 'coffeemakerId', 'KeyType': 'HASH' },
        { 'AttributeName': 'start', 'KeyType': 'RANGE' }
    ],
    AttributeDefinitions=[ 
        { 'AttributeName': 'coffeemakerId','AttributeType': 'S' },
        { 'AttributeName': 'start', 'AttributeType': 'S' }
    ],ProvisionedThroughput=
        { 'ReadCapacityUnits': 10,'WriteCapacityUnits': 10 }
    )

class SlackEventConsumer:

    def __init__(self):
        self.events = []

    def consume(self, coffeemaker_id, msg):
        self.events.append({ 'coffeemaker_id': coffeemaker_id, 'msg': msg})


def getItems(table,coffeemaker_id):
    response = table.query(KeyConditionExpression=Key('coffeemakerId').eq(coffeemaker_id))
    return response['Items']

def getItem(table, coffeemaker_id, start):
    return table.get_item(Key={'coffeemakerId': coffeemaker_id, 'start': start})['Item']

def test_wrong_event_structure():
    with pytest.raises(Exception):
        handler.handler({}, {})

def test_invalid_coffeemaker_id():
    with pytest.raises(Exception):
        handler.handler({ 'coffeemakerId': 'Moskova', 'eventType': 'out-of-coffee'}, {})

def test_invalid_event_type():
    with pytest.raises(Exception):
        handler.handler({ 'coffeemakerId': 'Hki1', 'eventType': 'out-of-beer'}, {})

@mock_dynamodb2
def test_start_brew():
    table = createTable()
    slackEventConsumer = SlackEventConsumer()
    startTime = handler.format_timestamp(datetime.now())
    handler.handler({ 
            'coffeemakerId': 'Hki1', 
            'eventType': 'start', 
            'startTime': startTime
        }, {}, slackEventConsumer.consume)
    items = getItems(table, 'Hki1')
    assert len(items) == 1
    assert items[0]['start'] == startTime
    assert items[0].get('end', None) == None

    assert len(slackEventConsumer.events) == 1
    assert slackEventConsumer.events[0]['coffeemaker_id'] == 'Hki1'
    assert slackEventConsumer.events[0]['msg'] == slack_messages['brew_started']

@mock_dynamodb2
def test_end_brew():
    table = createTable()
    slackEventConsumer = SlackEventConsumer()

    startTime = handler.format_timestamp(datetime.now())
    endTime = handler.format_timestamp(datetime.now())
    
    table.put_item(Item={'coffeemakerId': 'Hki1','start': startTime,'end': endTime})

    handler.handler({ 
            'coffeemakerId': 'Hki1', 
            'eventType': 'end', 
            'startTime': startTime,
            'endTime': endTime
        }, {}, slackEventConsumer.consume)
    items = getItems(table, 'Hki1')
    assert len(items) == 1
    assert items[0]['start'] == startTime
    assert items[0]['end'] == endTime

    assert len(slackEventConsumer.events) == 1
    assert slackEventConsumer.events[0]['coffeemaker_id'] == 'Hki1'
    assert slackEventConsumer.events[0]['msg'] == slack_messages['brew_ended']


@mock_dynamodb2
def test_brew_timed_out():
    table = createTable()
    slackEventConsumer = SlackEventConsumer()

    startTime = handler.format_timestamp(datetime.now() - timedelta(seconds=2400))
    
    table.put_item(Item={'coffeemakerId': 'Hki1','start': startTime,'end': None})

    handler.handler(
        { 'eventType': "check-status"}, 
        {}, slackEventConsumer.consume)
    
    items = getItems(table, 'Hki1')
    assert len(items) == 1
    assert items[0]['start'] == startTime
    assert len(items[0]['end']) == 23

    assert len(slackEventConsumer.events) == 1
    assert slackEventConsumer.events[0]['coffeemaker_id'] == 'Hki1'
    assert slackEventConsumer.events[0]['msg'] == slack_messages['brew_timeout']

@mock_dynamodb2
def test_brew_ready():
    table = createTable()
    slackEventConsumer = SlackEventConsumer()

    startTime = handler.format_timestamp(datetime.now() - timedelta(seconds=300))
    
    table.put_item(Item={'coffeemakerId': 'Hki1','start': startTime,'end': None})

    handler.handler(
        { 'eventType': "check-status"}, 
        {}, slackEventConsumer.consume)
    
    items = getItems(table, 'Hki1')
    assert len(items) == 1
    assert items[0]['start'] == startTime
    assert items[0].get('end', None) == None

    assert len(slackEventConsumer.events) == 1
    assert slackEventConsumer.events[0]['coffeemaker_id'] == 'Hki1'
    assert slackEventConsumer.events[0]['msg'] == slack_messages['coffee_ready']

@mock_dynamodb2
def test_brew_ready_and_timeout():
    table = createTable()
    slackEventConsumer = SlackEventConsumer()

    brewedInOulu = handler.format_timestamp(datetime.now() - timedelta(seconds=7800))
    brewedInHki = handler.format_timestamp(datetime.now() - timedelta(seconds=400))
    
    table.put_item(Item={'coffeemakerId': 'Oulu1','start': brewedInOulu,'end': None})
    table.put_item(Item={'coffeemakerId': 'Hki1','start': brewedInHki,'end': None})

    handler.handler(
        { 'eventType': "check-status"}, 
        {}, slackEventConsumer.consume)
    
    assert len(slackEventConsumer.events) == 2
    assert slackEventConsumer.events[0]['coffeemaker_id'] == 'Hki1'
    assert slackEventConsumer.events[0]['msg'] == slack_messages['coffee_ready']

    assert slackEventConsumer.events[1]['coffeemaker_id'] == 'Oulu1'
    assert slackEventConsumer.events[1]['msg'] == slack_messages['brew_timeout']

def test_out_of_coffee():
    slackEventConsumer = SlackEventConsumer()

    handler.handler({ 
        'coffeemakerId': 'Hki1', 
        'eventType': 'out-of-coffee'}, {},slackEventConsumer.consume)

    assert len(slackEventConsumer.events) == 1
    assert slackEventConsumer.events[0]['coffeemaker_id'] == 'Hki1'
    assert slackEventConsumer.events[0]['msg'] == slack_messages['out_of_coffee']
