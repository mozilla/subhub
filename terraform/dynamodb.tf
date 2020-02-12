# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

resource "aws_dynamodb_table" "users_table" {
  name           = "${var.users_table}"
  billing_mode   = "PROVISIONED"
  read_capacity  = "${var.users_table_read_capacity}"
  write_capacity = "${var.users_table_write_capacity}"
  hash_key       = "user_id"
  attribute {
    name = "user_id"
    type = "S"
  }
  tags = var.tags
}

resource "aws_dynamodb_table" "deleted_users_table" {
  name           = "${var.deleted_users_table}"
  billing_mode   = "PROVISIONED"
  read_capacity  = "${var.deleted_users_table_read_capacity}"
  write_capacity = "${var.deleted_users_table_write_capacity}"
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
  name           = "${var.events_table}"
  billing_mode   = "PROVISIONED"
  read_capacity  = "${var.events_table_read_capacity}"
  write_capacity = "${var.events_table_write_capacity}"
  hash_key       = "event_id"
  attribute {
    name = "event_id"
    type = "S"
  }
  tags = var.tags
}
