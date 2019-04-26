import logging
from typing import Optional

from pynamodb.attributes import UnicodeAttribute
from pynamodb.models import Model, DoesNotExist, EXISTS as pynamexists
from pynamodb.exceptions import PutError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SubHubAccountModel(Model):
    userId = UnicodeAttribute(hash_key=True)
    custId = UnicodeAttribute(null=True)
    orig_system = UnicodeAttribute()


class SubHubAccount():
    def __init__(self, table_name, region, host=None):
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

    def get_user(self, uid) -> SubHubAccountModel:
        try:
            subscription_user = self.model.get(uid, consistent_read=True)
            return subscription_user
        except DoesNotExist:
            return None

    def save_user(self, uid, orig_system) -> bool:
        try:
            resp = self.model(userId=uid, custId=None, orig_system=orig_system)
            resp.save()
            return True
        except PutError:
            return False

    def append_custid(self, uid, custId) -> bool:
        try:
            update_user = self.model.get(uid, consistent_read=True)
            update_user.custId = custId
            update_user.save()
            return True
        except DoesNotExist:
            return False

    def remove_from_db(self, uid) -> bool:
        try:
            self.model.get(uid, consistent_read=True).delete()
            return True
        except DoesNotExist as e:
            False
