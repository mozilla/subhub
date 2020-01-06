# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

output "deployed_at" {
  value = formatdate("YYYYMMDDhhmmss", timestamp())
}


output "sub_secrets" {
			
  value = [
			
    for secret, arn in zipmap(
			
      sort(var.sub_secrets),
			
      sort(values(aws_secretsmanager_secret.sub-secret)[*]["arn"])) :
			
      map("name", secret, "valueFrom", arn)
			
  ]
			
}
			

			
output "hub_secrets" {
			
  value = [
			
    for secret, arn in zipmap(
			
      sort(var.hub_secrets),
			
      sort(values(aws_secretsmanager_secret.hub-secret)[*]["arn"])) :
			
      map("name", secret, "valueFrom", arn)
			
  ]
			
} 