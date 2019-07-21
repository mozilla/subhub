from subhub.subhub_dynamodb import SubHubAccount


class DynamoUtils:
    def __init__(self, table_name, region, host):
        self.subhub_account = SubHubAccount(table_name, region, host)

    def create_user(self, uid, origin_system, customer_id):
        self.subhub_account.new_user(uid, origin_system, customer_id)

    def delete_user(self, uid):
        self.subhub_account.remove_from_db(uid)
