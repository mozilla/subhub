# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import datetime
from typing import Optional, Any, List, Dict
from shared.log import get_logger
from google.cloud import spanner
from shared.cfg import CFG

logger = get_logger()

class Database:
    """
    This file assumes the schema:

    CREATE TABLE DeletedUser (
     user_id STRING(MAX) NOT NULL,
     cust_id STRING(MAX),
     origin_system STRING(MAX),
     customer_status STRING(MAX),
     subscription_info STRING(MAX),
     deleted_at TIMESTAMP NOT NULL,
    ) PRIMARY KEY (CustomerNumber);

    CREATE TABLE Event (
     event_id STRING(MAX) NOT NULL,
     sent_system STRING(MAX),
     event_at TIMESTAMP NOT NULL,
    ) PRIMARY KEY (event_id);
    """
    def __init__(self):
        spanner_client = spanner.Client()
        instance = spanner_client.instance(CFG.SPANNER_INSTANCE)
        self.database = instance.database(CFG.SPANNER_DATABASE)

    def insert_event(self, event_id, sent_system):
        self.database.run_in_transaction(self._insert_event, event_id, sent_system)

    def update_event(self, event_id, sent_system):
        self.database.run_in_transaction(self._update_event, event_id, sent_system)

    def get_event(self, event_id):
        return self.database.run_in_transaction(self._get_event, event_id)

    def insert_deleted_user(self, user_id, cust_id, origin_system, customer_status, subscription_info, deleted_at):
        self.database.run_in_transaction(self._insert_deleted_user, user_id, cust_id, origin_system, customer_status, subscription_info, deleted_at)

    def update_deleted_user(self, user_id, cust_id, origin_system, customer_status, subscription_info, deleted_at):
        self.database.run_in_transaction(self._update_deleted_user, user_id, cust_id, origin_system, customer_status, subscription_info, deleted_at)

    def get_deleted_user(self, user_id, cust_id):
        return self.database.run_in_transaction(self.get_deleted_user, user_id, cust_id)

    def get_deleted_user_by(self, cust_id):
        return self.database.run_in_transaction(self._get_deleted_user_by, cust_id)

    def _insert_event(self, transaction, event_id, sent_system):
        transaction.update(
            table='Event',
            columns=('event_id', 'sent_system', 'event_at'),
            values=[
                (event_id, sent_system, datetime.datetime.utcnow()),
            ])

    def _update_event(self, transaction, event_id, sent_system):
        transaction.insert(
            table='Event',
            columns=('event_id', 'sent_system', 'event_at'),
            values=[
                (event_id, sent_system, datetime.datetime.utcnow()),
            ])

    def _get_event(self, transaction, event_id):
        return transaction.execute_sql(
            """SELECT sent_system, event_at From DeletedUser
               WHERE event_id={event_id}""".format(
                event_id=event_id))

    def _insert_deleted_user(self, transaction, user_id, cust_id, origin_system, customer_status, subscription_info):
        transaction.insert(
            table='Event',
            columns=('user_id', 'cust_id', 'origin_system', 'customer_status', 'subscription_info', 'deleted_at'),
            values=[
                (user_id, cust_id,  origin_system, customer_status, subscription_info, datetime.datetime.utcnow()),
            ])

    def _update_deleted_user(self, transaction, user_id, cust_id, origin_system, customer_status, subscription_info):
        transaction.update(
            table='Event',
            columns=('user_id', 'cust_id', 'origin_system', 'customer_status', 'subscription_info', 'deleted_at'),
            values=[
                (user_id, cust_id,  origin_system, customer_status, subscription_info, datetime.datetime.utcnow()),
            ])

    def _get_deleted_user(self, transaction, user_id, customer_id):
        return transaction.execute_sql(
            """SELECT user_id, cust_id, origin_system, customer_status, subscription_info, deleted_at From DeletedUser
               WHERE user_id={user_id} AND cust_id={cust_id}""".format(
                user_id=user_id, cust_id=customer_id))

    def _get_deleted_user_by(self, transaction, customer_id):
        return transaction.execute_sql(
            """SELECT user_id, cust_id, origin_system, customer_status, subscription_info, deleted_at From DeletedUser
               WHERE cust_id={cust_id}""".format(
                cust_id=customer_id))