from os import environ
import json
import boto3
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key

dynamo_region = environ['DYNAMODB_REGION']
dynamo_brew_table = environ['DYNAMODB_BREW_TABLE']
lambda_process_brew_event = environ['LAMBDA_PROCESS_BREW_EVENT']

iotButtonConfig = {
	'G030PT025262W2X0':'Hki1'
	# add other buttons and their id here
	#   make sure to also add configuration for the new id in 
	#   lambda process-coffee-event's config
}

def format_timestamp(ts):
	""" Formats given timestamp as Iso8601 string"""
	return ts.strftime('%Y-%m-%dT%H:%M:%S.00Z')


def get_current_brew(coffeemaker_id):
	""" Returns latest not brew for given coffeemaker if not ended
	    Returns None when no brew found or brew already ended"""

	table = boto3.resource('dynamodb', region_name=dynamo_region).Table(dynamo_brew_table)
	response = table.query(
		KeyConditionExpression=Key('coffeemakerId').eq(coffeemaker_id),
		ScanIndexForward=False,
		Limit=1)
	brews = response['Items']
	if len(brews) == 0 or brews[0].get('end', None) != None: 
		return None
	return brews[0]


def invoke_coffee_event_lambda(event):
	boto3.client('lambda').invoke(
	    FunctionName=lambda_process_brew_event,
	    InvocationType='RequestResponse',
	    Payload= bytes(json.dumps(event), 'utf-8')
	)

def handler(event, context, coffee_event_consumer = invoke_coffee_event_lambda): 
	print("Received event:", event)
	serial = event['serialNumber']
	clickType = event['clickType']
	coffeemaker_id = iotButtonConfig[serial]

	if clickType == 'DOUBLE': 
		coffee_event_consumer({
			'coffeemakerId': coffeemaker_id,
			'eventType': 'start',
			'startTime': format_timestamp(datetime.now())
		})

	elif clickType == 'LONG': 
		coffee_event_consumer({
			'coffeemakerId': coffeemaker_id,
			'eventType': 'out-of-coffee'
	})

	elif clickType == 'SINGLE': 
		brew = get_current_brew(coffeemaker_id)
		if brew is None: print('stop was pressed, but no brew in progress. ¯\_(ツ)_/¯')
		else: coffee_event_consumer({
			'coffeemakerId': coffeemaker_id,
			'eventType': 'end',
			'startTime': brew['start'],
			'endTime': format_timestamp(datetime.now())
		})

	else: raise Exception("Unknown clicktype:", clickType)
