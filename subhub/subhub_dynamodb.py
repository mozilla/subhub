import logging
from typing import Optional

from pynamodb.attributes import UnicodeAttribute
from pynamodb.models import Model, DoesNotExist
from pynamodb.exceptions import PutError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
        except DoesNotExist as e:
            return False
