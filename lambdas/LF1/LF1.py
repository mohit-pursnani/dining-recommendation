import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3
import json
import re

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')

def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def validate_dining_suggestion(location, cuisine, time, numberOfPeople, email, phoneNumber):

    regex = '^[a-z 0-9]+[\._}?[a-z 0-9]+[@]\w+[.]\w{2,3}$'
    locations = ['brooklyn','manhattan','bronx','queens', 'staten island']
    
    # initialize string
    input_location = locations[0]
    for i in range(1, len(locations)):
      input_location = input_location+ ", " + str(locations[i])
    
    
    if location is not None and location.lower() not in locations:
        return build_validation_result(False,
                                       'Location',
                                       'We do not have suggestions for {0}, would you like suggestions for a differenet location?  '
                                       'We are currently operating in {1} '.format(location, input_location))
                                       
    cuisines = ['chinese', 'indian', 'italian', 'mexican', 'thai','japanese']
    
    # initialize string
    input_cuisines = cuisines[0]
    for i in range(1, len(cuisines)):
      input_cuisines = input_cuisines+ ", " + str(cuisines[i])
    
    if cuisine is not None and cuisine.lower() not in cuisines:
        return build_validation_result(False,
                                       'Cuisine',
                                       'We do not have suggestions for {0}, would you like suggestions for a differenet cuisine ?  '
                                       'Our most popular Cuisines are {1}'.format(cuisine, input_cuisines))        
    
    if time is not None:
        if len(time) != 5:
            return build_validation_result(False, 'DiningTime', 'I did not quite get that, can you put time in HH:MM or HH:MM am/pm format')

        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        
        HOUR        = datetime.datetime.now().hour
        MINUTE      = datetime.datetime.now().minute
        SECONDS     = datetime.datetime.now().second
        
        print(HOUR, MINUTE, SECONDS)
            
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', None)

        if hour < 10 or hour > 24:
            # Outside of business hours
            return build_validation_result(False, 'Time', 'Our business hours are from 10 AM. to 11 PM. Can you specify a time during this range?')
    
    if numberOfPeople is not None:
        numberOfPeople = int(numberOfPeople)
        if numberOfPeople > 50 or numberOfPeople <= 0:
            return build_validation_result(False,
            'NumberOfPeople',
            'That does not look like a valid number {}, '
            'It should be less than 50'.format(numberOfPeople))
    
    if email is not None:
         if not(re.search(regex, email)):
            return build_validation_result(False,
                                           'Email',
                                           'That does not look like a valid mail {}, '
                                           'Could you please repeat? '.format(email))
                                           
    if phoneNumber is not None and not phoneNumber.isnumeric():
        if len(phoneNumber) != 10:
            return build_validation_result(False,
                                           'PhoneNumber',
                                           'That does not look like a valid number {}, '
                                           'Could you please repeat? '.format(phoneNumber))
    return build_validation_result(True, None, None)


def diningSuggestions(intent_request,context):
    
    location = get_slots(intent_request)["Location"]
    cuisine = get_slots(intent_request)["Typeofcuisine"]
    time = get_slots(intent_request)["DiningTime"]
    numberOfPeople = get_slots(intent_request)["NumberofPeople"]
    phoneNumber = get_slots(intent_request)["PhoneNumber"]
    email = get_slots(intent_request)["Email"]
    source = intent_request['invocationSource']
    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    
    
    print("time: ", time)
    
    requestData = {
        "typeofcuisine": cuisine,
        "location":location,
        "diningtime": time,
        "limit":"3",
        "numberOfPeople": numberOfPeople,
        "Email": email,
        "PhoneNumber": phoneNumber
    }
                
    print (requestData)
    output_session_attributes['requestData'] = json.dumps(requestData)

    if source == 'DialogCodeHook':
        slots = get_slots(intent_request)
        validation_result = validate_dining_suggestion(location, cuisine, time, numberOfPeople, email, phoneNumber)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
        return delegate(output_session_attributes, get_slots(intent_request))
        
    messageId = sendSQSMessage(requestData)
    print (messageId)
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Thank you for the information, we are generating our recommendations, we will send the recommendations to your mail/phoneNumber when they are generated'})

def sendSQSMessage(requestData):
    queue_url = 'https://sqs.us-east-1.amazonaws.com/xxxxxxxxx/dining-bot-queue'
    sqs = boto3.client('sqs', region_name='us-east-1')

    
    messageAttributes = {
        'Typeofcuisine': {
            'DataType': 'String',
            'StringValue': requestData['typeofcuisine']
        },
        'Location': {
            'DataType': 'String',
            'StringValue': requestData['location']
        },
        "DiningTime": {
            'DataType': "String",
            'StringValue': requestData['diningtime']
        },
        'NumberofPeople': {
            'DataType': 'Number',
            'StringValue': requestData['numberOfPeople']
        },
        'Email': {
            'DataType': 'String',
            'StringValue': requestData['Email']
        },
        'PhoneNumber': {
            'DataType': 'Number',
            'StringValue': requestData['PhoneNumber']
        }
    }
    
    messageBody=('Slots for the Restaurant')
    
    print(messageBody)
    
    response = sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageAttributes = messageAttributes,
        MessageBody = messageBody)
        
    print(response)
    print("Message sent on queue")
    
    return response['MessageId']


def welcome(intent_request):
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Hey there, How may I serve you today?'})

def thankYou(intent_request):
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'My pleasure, Have a great day!!'})


def dispatch(intent_request,context):
    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    if intent_name == 'DiningSuggestionsIntent':
        return diningSuggestions(intent_request,context)
    elif intent_name == 'ThankYouIntent':
        return thankYou(intent_request)
    elif intent_name == 'GreetingIntent':
        return welcome(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


def lambda_handler(event, context):
    os.environ['TZ'] = 'America/New_York'
    time.tzset()

    return dispatch(event,context)