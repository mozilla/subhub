# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import Optional, Any, List, cast, Type, TYPE_CHECKING, Union

from deprecated import deprecated
from pynamodb.attributes import UnicodeAttribute, ListAttribute
from pynamodb.connection import Connection
from pynamodb.models import Model, DoesNotExist
from pynamodb.exceptions import PutError, DeleteError

from shared.log import get_logger

logger = get_logger()


# This exists purely for type-checking, the actual model is dynamically
# created in DbAccount
class SubHubAccountModel(Model):

    user_id = UnicodeAttribute(hash_key=True)
    cust_id = UnicodeAttribute(null=True)
    origin_system = UnicodeAttribute()
    customer_status = UnicodeAttribute()


def _create_account_model(table_name_, region_, host_) -> Any:
    class SubHubAccountModel(Model):
        class Meta:
            table_name = table_name_
            region = region_
            if host_:
                host = host_

        user_id = UnicodeAttribute(hash_key=True)
        cust_id = UnicodeAttribute(null=True)
        origin_system = UnicodeAttribute()
        customer_status = UnicodeAttribute()

    return SubHubAccountModel


class SubHubAccount:
    def __init__(self, table_name: str, region: str, host: Optional[str] = None):
        self.model = _create_account_model(table_name, region, host)

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
        logger.debug(
            f"Enter {SubHubAccount.__class__.__name__}::{SubHubAccount.get_user.__name__}"
        )
        subscription_user: SubHubAccountModel = None
        try:
            subscription_user = self.model.get(uid, consistent_read=True)
        except DoesNotExist as error:
            logger.error("User find error", uid=uid, error=error)
        logger.debug(
            f"Exit {SubHubAccount.__class__.__name__}::{SubHubAccount.get_user.__name__}"
        )
        return subscription_user

    @staticmethod
    def save_user(user: SubHubAccountModel) -> bool:
        logger.debug(
            f"Enter {SubHubAccount.__class__.__name__}::{SubHubAccount.save_user.__name__}"
        )
        saved = False
        try:
            user.save()
            saved = True
        except PutError as error:
            logger.error("Failed to save User", user=user)
            logger.error("Save error", error=error)
            saved = False
        logger.debug(
            f"Exit {SubHubAccount.__class__.__name__}::{SubHubAccount.save_user.__name__}"
        )
        return saved

    @deprecated("Prefer new customer creation and deletion")
    def append_custid(self, uid: str, cust_id: str) -> bool:
        logger.debug(
            f"Enter {SubHubAccount.__class__.__name__}::{SubHubAccount.append_custid.__name__} ({uid}, {cust_id})"
        )
        saved = False
        try:
            update_user = self.model.get(uid, consistent_read=True)
            update_user.cust_id = cust_id
            update_user.save()
            saved = True
        except DoesNotExist:
            logger.error("append custid", uid=uid, cust_id=cust_id)
            saved = False
        logger.debug(
            f"Exit {SubHubAccount.__class__.__name__}::{SubHubAccount.append_custid.__name__} ({uid}, {cust_id})"
        )
        return saved

    def remove_from_db(self, uid: str) -> bool:
        logger.debug(
            f"Enter {SubHubAccount.__class__.__name__}::{SubHubAccount.remove_from_db.__name__} ({uid})"
        )
        removed = False
        try:
            conn = Connection(host=self.model.Meta.host, region=self.model.Meta.region)
            conn.delete_item(
                self.model.Meta.table_name, hash_key=uid, range_key=None
            )  # Note that range key is optional
            removed = True
        except DeleteError as e:
            logger.error("failed to remove user from db", uid=uid)
            removed = False
        logger.debug(
            f"Exit {SubHubAccount.__class__.__name__}::{SubHubAccount.remove_from_db.__name__} ({uid})"
        )
        return removed

    @deprecated(
        "mark_deleted is no longer used and can therefore be removed from both SubHubDeletedAccountModel and SubHubAccountModel"
    )
    def mark_deleted(self, uid: str) -> bool:
        logger.debug(
            f"Enter {SubHubAccount.__class__.__name__}::{SubHubAccount.mark_deleted.__name__} ({uid})"
        )
        deleted = False
        try:
            delete_user = self.model.get(uid, consistent_read=True)
            delete_user.customer_status = "deleted"
            delete_user.save()
            deleted = True
        except DoesNotExist:
            logger.error("mark deleted", uid=uid)
            deleted = False
        logger.debug(
            f"Exit {SubHubAccount.__class__.__name__}::{SubHubAccount.mark_deleted.__name__} ({uid})"
        )
        return deleted


def _create_hub_model(table_name_, region_, host_) -> Any:
    class HubEventModel(Model):
        class Meta:
            table_name = table_name_
            region = region_
            if host_:
                host = host_

        event_id = UnicodeAttribute(hash_key=True)
        sent_system = ListAttribute()  # type: ignore

    return HubEventModel


class HubEventModel(Model):
    event_id = UnicodeAttribute(hash_key=True)
    sent_system: Any = ListAttribute(default=list)


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
            return False
        except DoesNotExist:
            logger.error("append event", event_id=event_id, sent_system=sent_system)
            return False

    def remove_from_db(self, uid: str) -> bool:
        try:
            conn = Connection(host=self.model.Meta.host, region=self.model.Meta.region)
            conn.delete_item(
                self.model.Meta.table_name, hash_key=uid, range_key=None
            )  # Note that range key is optional
            return True
        except DeleteError:
            logger.error("failed to remove event from db", uid=uid)
            return False


# This exists purely for type-checking, the actual model is dynamically
# created in DbAccount
class SubHubDeletedAccountModel(Model):
    user_id = UnicodeAttribute(hash_key=True)
    cust_id = UnicodeAttribute(null=True)
    origin_system = UnicodeAttribute()
    customer_status = UnicodeAttribute()


def _create_deleted_account_model(table_name_, region_, host_) -> Any:
    class SubHubDeletedAccountModel(Model):
        class Meta:
            table_name = table_name_
            region = region_
            if host_:
                host = host_

        user_id = UnicodeAttribute(hash_key=True)
        cust_id = UnicodeAttribute(null=True)
        origin_system = UnicodeAttribute()
        customer_status = UnicodeAttribute()

    return SubHubDeletedAccountModel


class SubHubDeletedAccount:
    def __init__(self, table_name: str, region: str, host: Optional[str] = None):
        self.model = _create_deleted_account_model(table_name, region, host)

    def new_user(
        self, uid: str, origin_system: str, cust_id: Optional[str] = None
    ) -> SubHubDeletedAccountModel:
        logger.debug(
            f"Enter {SubHubDeletedAccount.__class__.__name__}::{SubHubAccount.new_user.__name__} ({uid}, {origin_system}, {cust_id})"
        )
        user = self.model(
            user_id=uid,
            cust_id=cust_id,
            origin_system=origin_system,
            customer_status="deleted",
        )
        logger.debug(
            f"Exit {SubHubDeletedAccount.__class__.__name__}::{SubHubAccount.new_user.__name__} ({uid}, {origin_system}, {cust_id})",
            user=user,
        )
        return user

    def get_user(self, uid: str) -> Optional[SubHubDeletedAccountModel]:
        logger.debug(
            f"Enter {SubHubDeletedAccount.__class__.__name__}::{SubHubAccount.get_user.__name__} ({uid})"
        )
        subscription_user: Optional[Any] = None
        try:
            subscription_user = self.model.get(uid, consistent_read=True)
        except DoesNotExist:
            logger.error("get user", uid=uid)
        logger.debug(
            f"Enter {SubHubDeletedAccount.__class__.__name__}::{SubHubAccount.get_user.__name__} ({uid})"
        )
        return subscription_user

    @staticmethod
    def save_user(user: SubHubDeletedAccountModel) -> bool:
        logger.debug(
            f"Enter {SubHubDeletedAccount.__class__.__name__}::{SubHubAccount.save_user.__name__} ({user})"
        )
        saved = False
        try:
            user.save()
            saved = True
        except PutError:
            logger.error("save user", user=user)
            saved = False
        logger.debug(
            f"Enter {SubHubDeletedAccount.__class__.__name__}::{SubHubAccount.save_user.__name__} ({user})"
        )
        return saved

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
            conn = Connection(host=self.model.Meta.host, region=self.model.Meta.region)
            conn.delete_item(
                self.model.Meta.table_name, hash_key=uid, range_key=None
            )  # Note that range key is optional
            return True
        except DeleteError:
            logger.error("failed to remove deleted user from db", uid=uid)
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
