# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


resource "random_id" "terraform_state_bucket_name" {
  prefix      = "${var.deployed_env}-terraform"
  byte_length = 8
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = random_id.terraform_state_bucket_name.hex
  lifecycle {
    prevent_destroy = true
  }
  versioning {
    enabled = true
  }
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}
