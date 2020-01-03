# Terraform Global S3

This directory provides the bootstrapping of the Terraform state S3 bucket.

## Bootstrapping

Bootstrapping requires the creation of dependent resources that Terraform requires
for both state and lock management.  These are covered in the global direction.  In
this directory, there are 2 sub directories that cover each of these aspects:

* `s3`, this directory bootstraps an AWS S3 bucket for the purposes of Terraform state management.
* `dynamodb`, this directory bootstraps an AWS S3 bucket for the purposes of Terraform lock management.


### Terraform Initialization

You will need to initialize Terraform first.  This is done with the following command,

```
terraform init
```


### Observe the Plan

Execute the following plan to understand what Terraform is going to do when an action is
applied.  This will tell you if you are in fact, going to create the aforementioned object.

```
terraform plan
```

### Apply the Changes

If you agree with the changes in the above step then merely apply them with the following command.

```
terraform apply
```

After this step is performed, you will get values printed to the terminal that represent the names of the created objects.  They are outputted as follows:

* `terraform_s3_id`

This value will need to be placed into the top level Terraform directory, at the file
`backend.hcl` in the variable, `bucket`.

## Author(s)

Stewart Henderson <shenderson@mozilla.com>
