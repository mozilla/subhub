# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

resource "aws_dynamodb_table" "users_table" {
  name           = "${var.USER_TABLE}"
  billing_mode   = "PROVISIONED"
  read_capacity  = "${var.USERS_TABLE_READ_CAPACITY}"
  write_capacity = "${var.USERS_TABLE_WRITE_CAPACITY}"
  hash_key       = "user_id"
  attribute {
    name = "user_id"
    type = "S"
  }
  tags = var.tags
}

resource "aws_dynamodb_table" "deleted_users_table" {
  name           = "${var.DELETED_USER_TABLE}"
  billing_mode   = "PROVISIONED"
  read_capacity  = "${var.DELETED_USERS_TABLE_READ_CAPACITY}"
  write_capacity = "${var.DELETED_USERS_TABLE_WRITE_CAPACITY}"
  hash_key       = "user_id"
  range_key      = "cust_id"
  attribute {
    name = "user_id"
    type = "S"
  }
  attribute {
    name = "cust_id"
    type = "S"
  }
  tags = var.tags
}

resource "aws_dynamodb_table" "events_table" {
  name           = "${var.EVENT_TABLE}"
  billing_mode   = "PROVISIONED"
  read_capacity  = "${var.EVENTS_TABLE_READ_CAPACITY}"
  write_capacity = "${var.EVENTS_TABLE_WRITE_CAPACITY}"
  hash_key       = "event_id"
  attribute {
    name = "event_id"
    type = "S"
  }
  tags = var.tags
}
