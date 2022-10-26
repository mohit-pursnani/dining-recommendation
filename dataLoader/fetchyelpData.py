import json
import datetime
import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import csv
from io import BytesIO
import requests

resultData = []
yelp_limit = 50
# Supported Cuisines
cuisines = ['indian', 'mexican', 'chinese', 'thai', 'italian', 'japanese']
# Change this location to Brooklyn, Manhattan.
locations = ["manhattan", "brooklyn", "queens", "bronx", "staten island"]
restaurantIterations = 20

clientId = 'xxxxxxxxxxxx'
apiKey = 'xxxxxxxxx'

dynamodb = boto3.resource('dynamodb', aws_access_key_id='xxxxxxxxx',
aws_secret_access_key= 'xxxxxxxxxx',
region_name='us-east-1') #DYNAMODB REGION_NAME


table = dynamodb.Table('yelp-restaurants')



for cuisine in cuisines:
    for i in range(restaurantIterations):
        for loc in locations:
            requestData = {
                "term": cuisine + " restaurants",
                "location": loc,
                "limit": yelp_limit,
                "offset": 50*i
            }
            yelp_rest_endpoint = "https://api.yelp.com/v3/businesses/search"
            querystring = requestData
            payload = ""
            headers = {
                "Authorization": "Bearer xxxxxxxxxxxxxxxxxxxxxxx", #YELP API AUTH API KEY
                'cache-control': "no-cache"
            }
            response = requests.get(yelp_rest_endpoint, data=payload, headers=headers, params=querystring)
            message = json.loads(response.text)
            print(message)
            try:
                result = message['businesses']
                for restaurant in result:
                    tableEntry = {
                        'id': restaurant['id'],
                        'alias': restaurant['alias'],
                        'name': restaurant['name'],
                        'is_closed': restaurant['is_closed'],
                        'rating': int(restaurant['rating']),
                        'review_count': int(restaurant['review_count']),
                        'address': restaurant['location']['display_address'],
                        'categories': restaurant['categories'],
                        'cuisine': cuisine,
                    }
                    if (restaurant['coordinates'] and restaurant['coordinates']['latitude'] and restaurant['coordinates']['longitude']):
                        tableEntry['latitude'] = str(restaurant['coordinates']['latitude'])
                        tableEntry['longitude'] = str(restaurant['coordinates']['longitude'])
                    if (restaurant['location']['zip_code']):
                        tableEntry['zip_code'] = restaurant['location']['zip_code']
                    # Add necessary attributes to the yelp-restaurants table
                    resultData.append(tableEntry)
                    table.put_item(
                        Item={
                            'insertedAtTimestamp': str(datetime.datetime.now()),
                            'id': tableEntry['id'],
                            'name': tableEntry['name'],
                            'address': tableEntry['address'],
                            'latitude': tableEntry.get('latitude', None),
                            'longitude': tableEntry.get('longitude', None),
                            'review_count': tableEntry['review_count'],
                            'rating': tableEntry['rating'],
                            'zip_code': tableEntry.get('zip_code', None),
                            'categories': tableEntry['categories'],
                            'cuisine':tableEntry['cuisine']
                            }
                    )
            except:
                pass

host = 'search-restaurant-elastic-search-xxxxxxxxxxxxxxxx.us-east-1.es.amazonaws.com' #ELASTIC SEARCH KEY

host = 'search-restaurant-elastic-search-xxxxxxxxxxxxxxxx.us-east-1.es.amazonaws.com'  # For example, my-test-domain.us-east-1.es.amazonaws.com

es = Elasticsearch(
    hosts=[{'host': host, 'port': 443}],
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    http_auth = ('xx', 'xxxxxxxxx')
)

output = []
for restaurant in resultData:
    index_data = {
        'id': restaurant['id'],
        'cuisine' : restaurant['cuisine']
    }
    print ('dataObject', index_data)
    es.index(index="restaurants", doc_type="Restaurant", id=restaurant['id'], body=index_data, refresh=True)