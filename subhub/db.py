#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import Optional

from pynamodb.attributes import UnicodeAttribute, ListAttribute
from pynamodb.models import Model, DoesNotExist
from pynamodb.exceptions import PutError

from subhub.log import get_logger

logger = get_logger()


def _create_account_model(table_name_, region_, host_):
    class SubHubAccountModel(Model):
        class Meta:
            table_name = table_name_
            region = region_
            if host_:
                host = host_

        user_id = UnicodeAttribute(hash_key=True)
        cust_id = UnicodeAttribute(null=True)
        origin_system = UnicodeAttribute()

    return SubHubAccountModel


# This exists purely for type-checking, the actual model is dynamically
# created in DbAccount
class SubHubAccountModel(Model):
    user_id = UnicodeAttribute(hash_key=True)
    cust_id = UnicodeAttribute(null=True)
    origin_system = UnicodeAttribute()
    customer_status = UnicodeAttribute()


class SubHubAccount:
    def __init__(self, table_name: str, region: str, host: Optional[str] = None):
        _table = table_name
        _region = region
        _host = host

        class SubHubAccountModel(Model):
            class Meta:
                table_name = _table
                region = _region
                if _host:
                    host = _host

            user_id = UnicodeAttribute(hash_key=True)
            cust_id = UnicodeAttribute(null=True)
            origin_system = UnicodeAttribute()
            customer_status = UnicodeAttribute()

        self.model = SubHubAccountModel

    def new_user(
        self, uid: str, origin_system: str, cust_id: Optional[str] = None
    ) -> SubHubAccountModel:
        return self.model(
            user_id=uid,
            cust_id=cust_id,
            origin_system=origin_system,
            customer_status="active",
        )

    def get_user(self, uid: str) -> Optional[SubHubAccountModel]:
        try:
            subscription_user = self.model.get(uid, consistent_read=True)
            return subscription_user
        except DoesNotExist:
            logger.error("get user", uid=uid)
            return None

    @staticmethod
    def save_user(user: SubHubAccountModel) -> bool:
        try:
            user.save()
            return True
        except PutError:
            logger.error("save user", user=user)
            return False

    def append_custid(self, uid: str, cust_id: str) -> bool:
        try:
            update_user = self.model.get(uid, consistent_read=True)
            update_user.cust_id = cust_id
            update_user.save()
            return True
        except DoesNotExist:
            logger.error("append custid", uid=uid, cust_id=cust_id)
            return False

    def remove_from_db(self, uid: str) -> bool:
        try:
            self.model.get(uid, consistent_read=True).delete()
            return True
        except DoesNotExist:
            logger.error("remove from db", uid=uid)
            return False

    def mark_deleted(self, uid: str) -> bool:
        try:
            delete_user = self.model.get(uid, consistent_read=True)
            delete_user.customer_status = "deleted"
            delete_user.save()
            return True
        except DoesNotExist:
            logger.error("mark deleted", uid=uid)
            return False


def _create_hub_model(table_name_, region_, host_):
    class HubEventModel(Model):
        class Meta:
            table_name = table_name_
            region = region_
            if host_:
                host = host_

        event_id = UnicodeAttribute(hash_key=True)
        sent_system = ListAttribute()

    return HubEventModel


class HubEventModel(Model):
    event_id = UnicodeAttribute(hash_key=True)
    sent_system = ListAttribute(default=list)


class HubEvent:
    def __init__(self, table_name: str, region: str, host: Optional[str] = None):
        self.model = _create_hub_model(table_name, region, host)

    def new_event(self, event_id: str, sent_system: list) -> HubEventModel:
        return self.model(event_id=event_id, sent_system=[sent_system])

    def get_event(self, event_id: str) -> Optional[HubEventModel]:
        try:
            hub_event = self.model.get(event_id, consistent_read=True)
            return hub_event
        except DoesNotExist:
            logger.error("get event", event_id=event_id)
            return None

    @staticmethod
    def save_event(hub_event: HubEventModel) -> bool:
        try:
            hub_event.save()
            return True
        except PutError:
            logger.error("save event", hub_event=hub_event)
            return False

    def append_event(self, event_id: str, sent_system: str) -> bool:
        try:
            update_event = self.model.get(event_id, consistent_read=True)
            if not sent_system in update_event.sent_system:
                update_event.sent_system.append(sent_system)
                update_event.save()
                return True
        except DoesNotExist:
            logger.error("append event", event_id=event_id, sent_system=sent_system)
            return False

    def remove_from_db(self, event_id: str) -> bool:
        try:
            self.model.get(event_id, consistent_read=True).delete()
            return True
        except DoesNotExist:
            logger.error("remove from db", event_id=event_id)
            return False
