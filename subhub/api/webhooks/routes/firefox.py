import boto3
import json
import logging

from botocore.exceptions import ClientError
from subhub.api.webhooks.routes.abstract import AbstractRoute
from subhub.cfg import CFG
from subhub import secrets


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class FirefoxRoute(AbstractRoute):
    def route(self):
        sqs_client = boto3.client("sqs", region_name=CFG.AWS_REGION)
        try:
            queues = sqs_client.list_queues(
                QueueNamePrefix="DevSub"
            )  # we filter to narrow down the list
            logger.info(f"queues {queues}")
            queue_url = queues["QueueUrls"][0]
            logger.info(f"queue url {queue_url}")
            msg = sqs_client.send_message(QueueUrl=queue_url, MessageBody=self.payload)

            if msg["ResponseMetadata"]["HTTPStatusCode"] == 200:
                logger.info(f"message sent to Firefox queue: {msg}")
                route_payload = json.loads(self.payload)
                self.report_route(route_payload, "firefox")
            else:
                logger.error(f"unable to send to Firefox queue")
                self.report_route_error(self.payload)

        except ClientError as e:
            logging.error(f"Firefox error: {e}")
            self.report_route_error(self.payload)
