# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

output "terraform_s3_id" {
  value       = aws_s3_bucket.terraform_state.id
  description = "The ID of the S3 Terraform state bucket"
}

# output "terraform_dynamodb_lock_table" {
#   value       = aws_dynamodb_table.terraform_locks.name
#   description = "The name of the DynamoDB table"
# }

output "deployed_at" {
  value = formatdate("YYYYMMDDhhmmss", timestamp())
}
