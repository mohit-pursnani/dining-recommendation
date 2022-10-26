import json
import boto3

def lambda_handler(event, context):
    client = boto3.client('lex-runtime')
    print(event)
    print(context)
    user_message = event["messages"][0]['unstructured']['text']
    user_id = 'root'
    lex_bot = 'xxxxx';
    bot_alias = 'xxxx';

    
    res = client.post_text(
        botName = lex_bot,
        botAlias = bot_alias,
        userId = user_id,
        inputText = user_message
    );
    response = {
        "messages" : [{
            "type" : "unstructured",
            "unstructured" : {
                "text" : res['message']
                
            }
            
        }]
        
    }
    return response