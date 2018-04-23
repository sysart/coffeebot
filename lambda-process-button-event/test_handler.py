import handler
import os
import pytest
import boto3
from datetime import datetime, timedelta
from moto import mock_dynamodb2
from boto3.dynamodb.conditions import Key, Attr

class EventConsumer():
    """Used to mock out lambda invocation, since it is super hard to test with moto :/"""
    
    def __init__(self):
        self.coffee_event = None

    def consume(self, event): 
        self.coffee_event = event

def create_table():
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


def test_wrong_event_structure():
    with pytest.raises(Exception):
        handler.handler({}, {})

def test_invalid_coffeemaker_id():
    with pytest.raises(Exception):
        handler.handler({ 'serialNumber': '42', 'clickType': 'SINGLE'}, {})

def test_invalid_event_type():
    with pytest.raises(Exception):
        handler.handler({ 'serialNumber': 'G030PT025262W2X0', 'clickType': 'TRIPLE'}, {})

def test_start():
    event_consumer = EventConsumer()
    handler.handler({ 'serialNumber': 'G030PT025262W2X0', 'clickType': 'DOUBLE'}, {}, event_consumer.consume)
    
    assert event_consumer.coffee_event['eventType'] == 'start'
    assert event_consumer.coffee_event['coffeemakerId'] == 'Hki1'
    assert len(event_consumer.coffee_event['startTime']) == 23

@mock_dynamodb2
def test_end():
    table = create_table()
    start = handler.format_timestamp(datetime.today() - timedelta(hours=3))
    table.put_item(Item={'coffeemakerId': 'Hki1','start': start,'end': None})

    event_consumer = EventConsumer()
    handler.handler({ 'serialNumber': 'G030PT025262W2X0', 'clickType': 'SINGLE'}, {}, event_consumer.consume)
    
    assert event_consumer.coffee_event['eventType'] == 'end'
    assert event_consumer.coffee_event['coffeemakerId'] == 'Hki1'
    assert event_consumer.coffee_event['startTime'] == start 
    assert len(event_consumer.coffee_event['endTime']) == 23

@mock_dynamodb2
def test_end_without_started_brew():
    create_table()
    event_consumer = EventConsumer()
    handler.handler({ 'serialNumber': 'G030PT025262W2X0', 'clickType': 'SINGLE'}, {}, event_consumer.consume)
    
    assert event_consumer.coffee_event == None

@mock_dynamodb2
def test_end_when_already_ended():
    table = create_table()
    start = handler.format_timestamp(datetime.today() - timedelta(hours=3))
    end = handler.format_timestamp(datetime.today() - timedelta(hours=2))

    table.put_item(Item={'coffeemakerId': 'Hki1','start': start,'end': end})

    event_consumer = EventConsumer()
    handler.handler({ 'serialNumber': 'G030PT025262W2X0', 'clickType': 'SINGLE'}, {}, event_consumer.consume)
    
    assert event_consumer.coffee_event == None

def test_out_of_coffee():
    event_consumer = EventConsumer()
    handler.handler({ 'serialNumber': 'G030PT025262W2X0', 'clickType': 'LONG'}, {}, event_consumer.consume)
    
    assert event_consumer.coffee_event['eventType'] == 'out-of-coffee'
    assert event_consumer.coffee_event['coffeemakerId'] == 'Hki1'
