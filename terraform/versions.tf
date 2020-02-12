# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

terraform {
  required_version = "= 0.12.8"
  # https://www.terraform.io/docs/configuration/terraform.html#specifying-required-provider-versions
  required_providers {
    # For latest releases checkout out the release page on
    # Github at:
    #   https://github.com/terraform-providers/terraform-provider-aws/releases
    # For information on this release checkout:
    #   https://github.com/terraform-providers/terraform-provider-aws/releases/tag/v2.42.0
    aws = "= 2.43.0"
  }
  backend "s3" {
    key = "global/s3/terraform.tfstate"
  }
}
