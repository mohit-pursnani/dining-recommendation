import json
import boto3
import os
import subprocess
from botocore.vendored import requests
from boto3.dynamodb.conditions import Key, Attr
from botocore.vendored import requests
from botocore.exceptions import ClientError

def getSQSMsg():
    queue_url = 'https://sqs.us-east-1.amazonaws.com/xxxxxxxxx/dining-bot-queue'
    sqsclient = boto3.client('sqs')
    response = sqsclient.receive_message(QueueUrl=queue_url,MaxNumberOfMessages=1,
        MessageAttributeNames=['All']
    )
    message = response['Messages'][0]
    sqsclient.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=message['ReceiptHandle']
        )
    return message
    
def search(cuisine):
    elasticsearchSearchURL = 'https://search-restaurant-elastic-search-xxxxxxxxx.us-east-1.es.amazonaws.com/'
    http_auth = ('xx', 'xxxxxxx')
    es_query =elasticsearchSearchURL+"restaurants/_search?q={category}".format(
        category=cuisine)
    esResponse = requests.get(es_query, auth=http_auth,headers={"Content-Type": "application/json"}).json()
    print("Elastic Search response:",esResponse)
    try:
        esData = esResponse["hits"]["hits"]
    except KeyError:
        logger.debug("Error extracting hits from ES response")
        
    return esResponse['hits']['hits']

def sendEmail(email,message):
    SENDER = "mp5578@nyu.edu"
    RECIPIENT = email
    SUBJECT = "Restaurant Recommendations for you!"
    CHARSET = "UTF-8"
    client = boto3.client('ses')
    try:
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                  
                    'Text': {
                        'Charset': CHARSET,
                        'Data': message,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

def get_restaurant_data(ids):
    dynamodb = boto3.resource('dynamodb')
    
    table = dynamodb.Table('yelp-restaurants')
    ans = 'Hi!\n Here are your suggestions,\n '
    i = 1
    for id in ids:
        if i<6:
            response = table.get_item(
                Key={
                    'id': id
                }
            )
            print(response)
            response_item = response['Item']
            print(response_item)
            restaurant_name = response_item['name']
            restaurant_address = response_item['address'][0]
            restaurant_zipcode = response_item['zip_code']
            restaurant_rating = str(response_item['rating'])
            
            ans += "{}. {}, located at {}\n".format(i, restaurant_name, restaurant_address)
            
            i += 1
        else:
            break
    return ans


def lambda_handler(event=None, context=None):
    message = getSQSMsg()
    print(message)
    receipt_handle = message['ReceiptHandle']
    req_attributes = message['MessageAttributes']
    cuisine = req_attributes['Typeofcuisine']['StringValue']
    location = req_attributes['Location']['StringValue']
    dining_time = req_attributes['DiningTime']['StringValue']
    num_people = req_attributes['NumberofPeople']['StringValue']
    email = req_attributes['Email']['StringValue']
    number = req_attributes['PhoneNumber']['StringValue']
    num = "+1{}".format(number)
    
    ids = search(cuisine)

    ids = list(map(lambda x: x['_id'], ids))
    print("ids: ",ids)

    rest_details = get_restaurant_data(ids)
    message = str(rest_details) +"requested for " +str(cuisine) + " for " + str(num_people) + " people at " + str(dining_time)  +" time in " + str(location)+ "\n\n"+ "Enjoy your meal!" 

    print(message)
    
    sendEmail(email, message)
    
    return {
        'statusCode': 200,
        'body': json.dumps('LF2 ran succesfully')
    }
