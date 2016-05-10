#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This lambda function subscribes to SNS beanstalk notifications, and upon recieving an
alarm outputs to slack something of the following format to the `CHANNEL` channel:
https://api.slack.com/docs/formatting/builder?msg=%7B%22username%22%3A%22production-env%22%2C%22icon_emoji%22%3A%22%3Atophat%3A%22%2C%22text%22%3A%22*Health%3A*%20%3Athumbsup%3A%20%E2%9F%B6%20%3Afire%3A%5Cn_Application%20update%20in%20progress%20on%201%20instance_%5Cn_0%20out%20of%201%20instance%20completed%20(running%20for%205%20seconds)._%22%7D
Once you have followed the below steps add your beanstalk notification topics as event sources.

On a new deployment it posts "new deploy" with a random ship emoji... Ahem.

---

Follow these steps to configure the webhook in Slack:

  1. Navigate to https://<your-team-domain>.slack.com/services/new

  2. Search for and select "Incoming WebHooks".

  3. Choose the default channel where messages will be sent and click "Add Incoming WebHooks Integration".

  4. Copy the webhook URL from the setup instructions and use it in the next section.


Follow these steps to encrypt your Slack hook URL for use in this function:

  1. Create a KMS key - http://docs.aws.amazon.com/kms/latest/developerguide/create-keys.html.

  2. Encrypt the event collector token using the AWS CLI.
     $ aws kms encrypt --key-id alias/<KMS key name> --plaintext "<SLACK_HOOK_URL>"

     Note: You must exclude the protocol from the URL (e.g. "hooks.slack.com/services/abc123").

  3. Copy the base-64 encoded, encrypted key (CiphertextBlob) to the ENCRYPTED_HOOK_URL variable.

  4. Give your function's role permission for the kms:Decrypt action.
     Example:

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Stmt1443036478000",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt"
            ],
            "Resource": [
                "<your KMS key ARN>"
            ]
        }
    ]
}
'''
from __future__ import print_function

import boto3
import json
import logging
import re
import random

from base64 import b64decode
from urllib2 import Request, urlopen, URLError, HTTPError

ENCRYPTED_HOOK_URL = "CiDITS..."

HOOK_URL = "https://" + boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED_HOOK_URL))['Plaintext']

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Event: " + str(event))

    state_dict = {"Ok": ":thumbsup:", "Info": ":information_source:", "Severe": ":exclamation:", "Warning": ":suspect:", "Degraded": ":hurtrealbad:"}
    color_dict = {"Ok": "#008000", "Info": "#FBB117", "Severe": "#FF0000", "Warning": "#FBB117", "Degraded": "#FF0000"}
    
    ships = [":ship:", ":shipit:", ":boat:", ":passenger_ship:", ":motor_boat:", ":speedboat:", ":rowboat:"]
    
    d = dict(line.split(": ") for line in event['Records'][0]['Sns']["Message"].splitlines() if ": " in line)

    # NOTE should probably just be a variable but yolo
    d["Environment URL"] = "https://us-west-2.console.aws.amazon.com/elasticbeanstalk/home?region=us-west-2#/application/overview?applicationName=" + d["Application"]
    
    transition = re.match('Environment health has transitioned from (.*?) to (.*?)\.', d['Message'])
    if transition:
        original, became = map(lambda x: state_dict.get(x, x), transition.groups())
        color = color_dict.get(transition.groups()[1], "#FFF")

        headline = "*Health*: " + original + u" <%s|⟶> "%d['Environment URL'] + became + "\n"

        d["Message"] = headline + "\n".join("_" + line + "_" for line in d["Message"].split(". ")[1:])

        # TODO make last line colored (but only if formatting works)
        #attachments = [{"text": headline, "color": color}]
    else:
        attachments = []
        
    if d["Message"] == "New application version was deployed to running EC2 instances.":
        d["Message"] = random.choice(ships) + " New deploy!"
        channel = 'build'
    else:
        channel = 'beanstalk'

    slack_message = {
        'channel': channel,
        'text': d["Message"],
        'username': d["Environment"],
        'icon_emoji': ':tophat:',
        #"attachments": attachments
        #'text': "%s state is now %s: %s" % (alarm_name, new_state, reason)
    }

    req = Request(HOOK_URL, json.dumps(slack_message))

    try:
        response = urlopen(req)
        response.read()
        logger.info("Message posted to %s", slack_message['channel'])
    except HTTPError as e:
        logger.error("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        logger.error("Server connection failed: %s", e.reason)
