# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

resource "random_id" "terraform_state_dynamo_table_name" {
  prefix      = "${var.deployed_env}-terraform-state"
  byte_length = 8
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = random_id.terraform_state_dynamo_table_name.hex
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
}
