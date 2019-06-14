from typing import Optional

from pynamodb.attributes import UnicodeAttribute, ListAttribute
from pynamodb.models import Model, DoesNotExist
from pynamodb.exceptions import PutError
from subhub.log import get_logger

logger = get_logger()


# This exists purely for type-checking, the actual model is dynamically
# created in DbAccount
class SubHubAccountModel(Model):
    userId = UnicodeAttribute(hash_key=True)
    custId = UnicodeAttribute(null=True)
    orig_system = UnicodeAttribute()


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

            userId = UnicodeAttribute(hash_key=True)
            custId = UnicodeAttribute(null=True)
            orig_system = UnicodeAttribute()

        self.model = SubHubAccountModel

    def new_user(
        self, uid: str, origin_system: str, custId: Optional[str] = None
    ) -> SubHubAccountModel:
        return self.model(userId=uid, custId=custId, orig_system=origin_system)

    def get_user(self, uid: str) -> Optional[SubHubAccountModel]:
        try:
            subscription_user = self.model.get(uid, consistent_read=True)
            return subscription_user
        except DoesNotExist:
            return None

    @staticmethod
    def save_user(user: SubHubAccountModel) -> bool:
        try:
            user.save()
            return True
        except PutError:
            return False

    def append_custid(self, uid: str, custId: str) -> bool:
        try:
            update_user = self.model.get(uid, consistent_read=True)
            update_user.custId = custId
            update_user.save()
            return True
        except DoesNotExist:
            return False

    def remove_from_db(self, uid: str) -> bool:
        try:
            self.model.get(uid, consistent_read=True).delete()
            return True
        except DoesNotExist:
            return False


class WebHookEventModel(Model):
    eventId = UnicodeAttribute(hash_key=True)
    sent_system = ListAttribute(default=list)


class WebHookEvent:
    def __init__(self, table_name: str, region: str, host: Optional[str] = None):
        _table = table_name
        _region = region
        _host = host

        class WebHookEventModel(Model):
            class Meta:
                table_name = _table
                region = _region
                if _host:
                    host = _host

            eventId = UnicodeAttribute(hash_key=True)
            sent_system = ListAttribute()

        self.model = WebHookEventModel

    def new_event(self, event_id: str, sent_system: list) -> WebHookEventModel:
        return self.model(eventId=event_id, sent_system=[sent_system])

    def get_event(self, event_id: str) -> Optional[WebHookEventModel]:
        try:
            webhook_event = self.model.get(event_id, consistent_read=True)
            return webhook_event
        except DoesNotExist:
            return None

    @staticmethod
    def save_event(webhook_event: WebHookEventModel) -> bool:
        try:
            webhook_event.save()
            return True
        except PutError:
            return False

    def append_event(self, event_id: str, sent_system: str) -> bool:
        try:
            update_event = self.model.get(event_id, consistent_read=True)
            if not sent_system in update_event.sent_system:
                update_event.sent_system.append(sent_system)
                update_event.save()
                return True
        except DoesNotExist:
            return False

    def remove_from_db(self, event_id: str) -> bool:
        try:
            self.model.get(event_id, consistent_read=True).delete()
            return True
        except DoesNotExist:
            return False
