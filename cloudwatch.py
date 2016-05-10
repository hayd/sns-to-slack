#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This lambda function subscribes to SNS Cloudwatch/Healthchecks, and upon recieving an
alarm outputs to slack something of the following format to the `CHANNEL` channel:
https://api.slack.com/docs/formatting/builder?msg=%7B%22username%22%3A%22HealthCheckStatus%20(AWS%2FRoute53)%22%2C%22icon_emoji%22%3A%22%3Afire_engine%3A%22%2C%22text%22%3A%22*%3Chttps%3A%2F%2Fconsole.aws.amazon.com%2Froute53%2Fhealthchecks%2Fhome%7CAlarm%3E%3A%20%5C%22landing%20page%5C%22*%20%3Athumbsup%3A%20%E2%9F%B6%20%3Afire%3A%5Cn_Threshold%20Crossed%3A%201%20datapoint%20(0.0)%20was%20less%20than%20the%20threshold%20(1.0)._%22%7D

Once you have followed the below steps add your SNS topic to event source.
(Have your healthcheck alarms notify the SNS topic.)

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

ENCRYPTED_HOOK_URL = "CiDIT..."

HOOK_URL = "https://" + boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED_HOOK_URL))['Plaintext']

CHANNEL = 'alarms'

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Event: " + str(event))

    contents = json.loads(event["Records"][0]["Sns"]["Message"])
    
    states_dict = {"OK": ":thumbsup:", "INSUFFICIENT_DATA": ":thinking_face:", "ALARM": ":fire:"}
    contents["OldStateValue"] = states_dict.get(contents["OldStateValue"], contents["OldStateValue"])
    contents["NewStateValue"] = states_dict.get(contents["NewStateValue"], contents["NewStateValue"])
    
    message = (
        "*<https://console.aws.amazon.com/route53/healthchecks/home|Alarm> \"" + contents["AlarmName"] + "\"*:  "
        + contents["OldStateValue"] + " ⟶ " + contents["NewStateValue"]
        + "\n_" + contents["NewStateReason"] +"_")

    slack_message = {
        'channel': CHANNEL,
        'text': message,
        'username': contents["Trigger"]["MetricName"] + " ( " + contents["Trigger"]["Namespace"] + " )",
        'icon_emoji': ':fire_engine:',
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
