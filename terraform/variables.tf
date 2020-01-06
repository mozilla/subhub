# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

variable "aws_region" {
  type        = "string"
  default     = "us-west-2"
  description = "the region where to provision the stack."
}

variable "sub_secrets" {
	description = "list of application secret names"
	type        = "list"
	default     = [
	  "STRIPE_API_KEY",
	  "PAYMENT_API_KEY",
	  "SUPPORT_API_KEY",
	  "ALLOWED_ORIGIN_SYSTEMS"
	  ]
	}
	
	variable "hub_secrets" {
	  description = "list of application secret names"
	  type        = "list"
	  default     = [
	    "STRIPE_API_KEY",
	    "HUB_API_KEY",
	    "SALESFORCE_BASKET_URI",
	    "TOPIC_ARN_KEY",
	    "PAYMENT_EVENT_LIST"
	  ]
	}

######################################
# DynamoDB Configuration
######################################

variable "USERS_TABLE_READ_CAPACITY" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "USERS_TABLE_WRITE_CAPACITY" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "DELETED_USERS_TABLE_READ_CAPACITY" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "DELETED_USERS_TABLE_WRITE_CAPACITY" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "EVENTS_TABLE_READ_CAPACITY" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "EVENTS_TABLE_WRITE_CAPACITY" {
  type        = "string"
  description = "AWS DynamoDB read capacity setting for the Users table."
  default     = "5"
}

variable "DEPLOYED_ENV" {
  type    = "string"
  default = "dev"
}

variable "USER_TABLE" {
  type    = "string"
  default = "NOT_SET_USER_TABLE"
}

variable "DELETED_USER_TABLE" {
  type    = "string"
  default = "NOT_SET_DELETED_USER_TABLE"
}

variable "EVENT_TABLE" {
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