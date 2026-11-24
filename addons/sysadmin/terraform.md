# Add-on: Terraform / OpenTofu (sysadmin)

Apply everything below unless the user asks otherwise.

## HCL
- `.tf` files only. Blocks: `terraform`, `provider`, `resource`, `data`, `variable`, `output`, `module`, `locals`.
- 2-space indent; `terraform fmt` and `validate`.

## Providers, resources, data
- `provider "aws" { region = "eu-west-1" }`; pin via `required_providers` + `version`. No credentials in code.
- `resource "aws_s3_bucket" "logs" { bucket = "logs-x" }` creates and owns it; reference `aws_s3_bucket.logs.id`.
- `data "aws_ami" "debian" {}` only reads existing objects.

## Variables, outputs
- `variable "env" { type = string }`, passed with `-var 'env=prod'` or `terraform.tfvars`.
- `output "bucket" { value = aws_s3_bucket.logs.id }` exports values; `locals {}` for computed expressions.

## State
- `terraform.tfstate` maps config to real objects; never edit or commit it (secrets).
- `for_each`/`count` for many objects; `moved` blocks on renames.

## Workflow
- `terraform init` installs providers/modules and sets the backend.
- `terraform plan -out tf.plan`, then `terraform apply tf.plan`.
- `terraform destroy` removes everything. `terraform state list|show|rm` inspects state; `import` adopts existing objects.

## Modules, remote state
- `module "vpc" { source = "./modules/vpc" ... }`; inputs are variables, outputs `module.vpc.id`.
- `backend "s3" { bucket = ..., key = ... }` (or `pg`, `gcs`, `azurerm`): remote state with locking, one per environment.
