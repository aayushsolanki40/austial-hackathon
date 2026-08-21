# Austial demo infrastructure (AWS, Terraform)

Minimal-cost AWS deployment of the current Austial backend scaffold (health
module only) and the Angular frontend static build, for live demo/testing
purposes. Account `459141725579`, region `us-east-1`, profile `aayush-gift`.

## Architecture

- Reuses the account's **default VPC** (`vpc-0366a2050e40eaf62`) and its
  existing public subnets -- no new VPC, no NAT Gateway.
- **1x EC2 `t3.micro`** in a public subnet, Elastic IP attached, running the
  backend container directly via Docker (no ECS/Fargate, no ALB). Security
  group allows inbound `8000/tcp` from `0.0.0.0/0` (demo endpoint) and no
  inbound `22` -- access for debugging is via **SSM Session Manager**
  (`aws ssm start-session --target <instance-id>`), using an instance
  profile with `AmazonSSMManagedInstanceCore` (+ ECR read-only so the
  instance can pull its own image).
- **1x RDS `db.t3.micro` Postgres**, single-AZ, 20GB `gp3`,
  `publicly_accessible = false`. Security group only allows `5432` from the
  backend EC2's security group.
- **1x ECR repository** (`austial-backend`) for the backend image.
- **1x S3 bucket** with static website hosting (public-read bucket policy
  scoped to the bucket's objects) for the Angular build output. No
  CloudFront -- plain HTTP S3 website endpoint.

Everything is tagged `Project=austial`, `Environment=demo`.

## A note on the `aayush-gift` AWS CLI profile and Terraform

The `aayush-gift` profile uses the AWS CLI's newer `login_session`
credential type (`aws login`), which the Terraform AWS provider's credential
chain cannot read (it only understands classic profiles, SSO cache,
env vars, or IMDS). Setting `profile = "aayush-gift"` in `provider.tf`
actively breaks Terraform auth. Instead, `provider.tf` has no `profile`
set, and every `terraform` invocation must have short-lived credentials
*exported from* that profile placed in the environment first:

```bash
eval "$(aws configure export-credentials --profile aayush-gift --format env)"
```

These credentials expire in well under an hour, so re-run the `eval` before
each `terraform plan`/`apply` if you get an auth error. The AWS account and
identity used is unchanged (still `459141725579` /
`aayushsolanki40@gmail.com`) -- this only changes how Terraform reads those
credentials, not which account they belong to.

## Re-running

```bash
# from this directory
eval "$(aws configure export-credentials --profile aayush-gift --format env)"
terraform init
terraform plan -out=tfplan.out   # review carefully -- see cost constraints below
terraform apply tfplan.out
```

`db_password` and `api_key` are read from `terraform.tfvars` (gitignored,
not committed -- regenerate if lost, e.g.
`openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24`).

**State is local** (`terraform.tfstate` in this directory, also gitignored).
That's fine for a single-operator demo, but before any team use, move to a
remote backend (S3 bucket + DynamoDB lock table) so state isn't only on one
laptop and concurrent applies don't corrupt it.

## Rebuilding and redeploying the backend image

```bash
# from austial-py/ -- the local checkout is ahead of the last PyPI release
# (0.1.5) and src/main.py depends on unreleased austial.orm APIs, so wheels
# are built locally rather than installing `austial` from PyPI. See the
# comment at the top of backend/Dockerfile for the full explanation.
for pkg in common core config orm terminus testing cli austial; do
  uv build --package austial-$pkg --wheel -o /tmp/austial_wheels 2>/dev/null \
    || uv build --package $pkg --wheel -o /tmp/austial_wheels
done
cp /tmp/austial_wheels/*.whl ../austial-hackathon/backend/vendor/

# from austial-hackathon/backend/
docker build -t austial-backend:latest .

ECR_URL=$(terraform -chdir=../infra/terraform output -raw ecr_repository_url)
aws ecr get-login-password --profile aayush-gift --region us-east-1 \
  | docker login --username AWS --password-stdin "${ECR_URL%/*}"
docker tag austial-backend:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"
```

The EC2 instance's user-data pulls `:latest` in a retry loop on first boot.
To roll out a new image to an already-running instance, either terminate and
let Terraform recreate it, or SSM into the box and run
`docker pull <repo>:latest && docker stop austial-backend && docker rm austial-backend && docker run -d ...` (same `docker run` args as in `user_data.sh.tpl`).

## Redeploying the frontend

```bash
cd austial-hackathon/frontend
npm install
npx ng build
aws s3 sync dist/swadely-app/browser/ \
  s3://$(terraform -chdir=../infra/terraform output -raw s3_bucket_name)/ \
  --profile aayush-gift --delete
```

## Monthly cost estimate (us-east-1, approximate, on-demand pricing)

| Resource | Spec | Est. $/mo |
|---|---|---|
| EC2 | 1x `t3.micro` (free-tier eligible for 12mo; on-demand ~$0.0104/hr after) | ~$7.60 |
| EBS (EC2 root volume) | 30GB `gp3` (AMI's minimum root size; 30GB/mo also within EBS free tier) | ~$0 (free tier) / ~$2.40 after |
| Elastic IP | attached to a running instance | $0 |
| RDS | 1x `db.t3.micro`, single-AZ, Postgres | ~$12.50 |
| RDS storage | 20GB `gp3` | ~$2.30 |
| ECR | 1 repo, <5 small images (lifecycle policy keeps last 5) | ~$0.10 |
| S3 | static site, a few hundred KB, low request volume | ~$0.05 |
| Data transfer | demo-level traffic | ~$1-2 |
| **Total** | | **~$18-27/mo** (lower for the first 12 months while EC2/EBS free tier applies) |

No NAT Gateway (~$32/mo saved), no ALB (~$16+/mo saved), no Multi-AZ RDS
(~2x RDS cost saved), no CloudFront -- all per the brief's cost constraints.

## Known deviations from the brief

1. **EC2 root volume is 30GB, not the implicit smaller default.** The
   Amazon Linux 2023 AMI's backing snapshot is 30GB; `RunInstances` rejects
   a smaller root volume outright. 30GB `gp3` is still within the EBS free
   tier and is not a "high resource" in the sense the brief was guarding
   against (no NAT/ALB/Multi-AZ/bigger instance types were added).
2. **Backend image installs from locally-built wheels (`backend/vendor/`),
   not PyPI's `austial` package.** `src/main.py` imports
   `austial.orm.DataSource`, which only exists in unreleased changes on the
   local `austial-py` checkout (`v0.1.5-1-gdd795bb`), not in the published
   `austial==0.1.5` wheel. See `backend/Dockerfile`'s header comment.
3. **Terraform doesn't use `profile = "aayush-gift"`** in the AWS provider
   block -- see the dedicated section above.
