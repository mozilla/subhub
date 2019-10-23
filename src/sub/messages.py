# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import boto3

from abc import ABC
from botocore.exceptions import ClientError

from sub.shared.cfg import CFG
from shared.log import get_logger

logger = get_logger()


class AbstractRoute(ABC):
    def __init__(self, payload) -> None:
        self.payload = payload

    def report_route_error(self, payload) -> None:
        logger.error("message route error", payload=payload)


class Message(AbstractRoute):
    def route(self) -> None:
        try:
            sns_client = boto3.client("sns", region_name=CFG.AWS_REGION)
            response = sns_client.publish(
                TopicArn=CFG.TOPIC_ARN_KEY,
                Message=json.dumps(
                    {"default": self.payload}
                ),  # json.dumps is required by FxA
                MessageStructure="json",
            )
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                logger.info("message sent to queue", response=response)
                logger.info("sns payload", payload=self.payload)
                return response
        except ClientError as e:
            logger.error("SNS error", error=e)
            self.report_route_error(self.payload)
