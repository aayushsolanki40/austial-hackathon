terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local state for this demo deployment. See README.md for notes on moving
  # to a remote backend (S3 + DynamoDB lock table) before any team use.
}

provider "aws" {
  region = var.aws_region

  # NOTE: the `aayush-gift` CLI profile (see var.aws_profile) uses AWS CLI's
  # newer `login_session` credential type (`aws login`), which the
  # Terraform AWS provider's credential chain cannot read directly (it only
  # understands classic profiles / SSO cache / env vars / IMDS). Setting
  # `profile = var.aws_profile` here actively breaks auth ("A Profile was
  # specified along with the environment variables ... Profile is now used
  # instead"). Instead, every terraform command in this directory must be
  # run with temporary credentials *exported from* that profile placed in
  # the environment first, e.g.:
  #   eval "$(aws configure export-credentials --profile aayush-gift --format env)"
  # See README.md for the full helper. The account/identity actually used
  # is still exclusively aayush-gift (459141725579) -- this only changes
  # *how* Terraform reads those same credentials, not which account is used.

  default_tags {
    tags = {
      Project     = "austial"
      Environment = "demo"
    }
  }
}
