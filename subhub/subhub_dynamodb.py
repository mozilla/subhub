from typing import Optional

from pynamodb.attributes import UnicodeAttribute, ListAttribute
from pynamodb.models import Model, DoesNotExist
from pynamodb.exceptions import PutError
from subhub.tracing import timed, cprofiled

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


class SubHubAccount:
    def __init__(self, table_name: str, region: str, host: Optional[str] = None):
        self.model = _create_account_model(table_name, region, host)

    def new_user(
        self, uid: str, origin_system: str, cust_id: Optional[str] = None
    ) -> SubHubAccountModel:
        return self.model(user_id=uid, cust_id=cust_id, origin_system=origin_system)

    @timed
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


def _create_webhook_model(table_name_, region_, host_):
    class WebHookEventModel(Model):
        class Meta:
            table_name = table_name_
            region = region_
            if host_:
                host = host_

        event_id = UnicodeAttribute(hash_key=True)
        sent_system = ListAttribute()

    return WebHookEventModel


class WebHookEventModel(Model):
    event_id = UnicodeAttribute(hash_key=True)
    sent_system = ListAttribute(default=list)


class WebHookEvent:
    def __init__(self, table_name: str, region: str, host: Optional[str] = None):
        self.model = _create_webhook_model(table_name, region, host)

    def new_event(self, event_id: str, sent_system: list) -> WebHookEventModel:
        return self.model(event_id=event_id, sent_system=[sent_system])

    def get_event(self, event_id: str) -> Optional[WebHookEventModel]:
        try:
            webhook_event = self.model.get(event_id, consistent_read=True)
            return webhook_event
        except DoesNotExist:
            logger.error("get event", event_id=event_id)
            return None

    @staticmethod
    def save_event(webhook_event: WebHookEventModel) -> bool:
        try:
            webhook_event.save()
            return True
        except PutError:
            logger.error("save event", webhook_event=webhook_event)
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
