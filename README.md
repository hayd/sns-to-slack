AWS Lambda functions which pipe SNS notification to Slack.

- Create a lambda function in the same region as your alarm.
- Assign it a role which has access to kms decrypt.
- Make a webhook url for your slack teams channel.
- Encrypt the hook url with kms and paste it into the Lambda function.

TODO automate/cli all this if the user has .aws/credentials.

The functions take the output of beanstalk's SNS messages:

https://api.slack.com/docs/formatting/builder?msg=%7B%22username%22%3A%22production-env%22%2C%22icon_emoji%22%3A%22%3Atophat%3A%22%2C%22text%22%3A%22*Health%3A*%20%3Athumbsup%3A%20%E2%9F%B6%20%3Afire%3A%5Cn_Application%20update%20in%20progress%20on%201%20instance_%5Cn_0%20out%20of%201%20instance%20completed%20(running%20for%205%20seconds)._%22%7D

and the output of cloudwatch alarm:

https://api.slack.com/docs/formatting/builder?msg=%7B%22username%22%3A%22HealthCheckStatus%20(AWS%2FRoute53)%22%2C%22icon_emoji%22%3A%22%3Afire_engine%3A%22%2C%22text%22%3A%22*%3Chttps%3A%2F%2Fconsole.aws.amazon.com%2Froute53%2Fhealthchecks%2Fhome%7CAlarm%3E%3A%20%5C%22landing%20page%5C%22*%20%3Athumbsup%3A%20%E2%9F%B6%20%3Afire%3A%5Cn_Threshold%20Crossed%3A%201%20datapoint%20(0.0)%20was%20less%20than%20the%20threshold%20(1.0)._%22%7D
