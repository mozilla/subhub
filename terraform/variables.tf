# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

variable "aws_region" {
  type        = "string"
  default     = "us-west-2"
  description = "the region where to provision the stack."
}

######################################
# DynamoDB Configuration
######################################

variable "users_table_read_capacity" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "users_table_write_capacity" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "deleted_users_table_read_capacity" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "deleted_users_table_write_capacity" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "events_table_read_capacity" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "events_table_write_capacity" {
  type        = "string"
  description = "AWS DynamoDB write capacity setting for the Users table."
  default     = "5"
}

variable "region" {
  type        = "string"
  description = "AWS Region."
  default     = "us-west-2"
}

variable "DEPLOYED_ENV" {
  type    = "string"
  default = "dev"
}

variable "users_table" {
  type    = "string"
  default = "NOT_SET_USER_TABLE"
}

variable "deleted_users_table" {
  type    = "string"
  default = "NOT_SET_DELETED_USER_TABLE"
}

variable "events_table" {
  type    = "string"
  default = "NOT_SET_EVENT_TABLE"
}

# AWS Tags
# The tagging guidelines can be found at
#   https://mana.mozilla.org/wiki/pages/viewpage.action?spaceKey=SRE&title=Tagging
variable "tags" {
  type = "map"
  default = {
    name          = "subhub"
    environment   = ""
    cost-center   = "1440"
    project-name  = "subhub"
    project-desc  = "subhub"
    project-email = "subhub@mozilla.com"
    deployed-env  = ""
    deploy-method = "terraform"
    sources       = "test"
  }
}
