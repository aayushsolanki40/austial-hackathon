# Austial demo infrastructure (AWS, Terraform)

Minimal-cost AWS deployment of the current Austial backend scaffold (health
module only) and the Angular frontend static build, for live demo/testing
purposes. Account `459141725579`, region `us-east-1`, profile `aayush-gift`.

## Architecture

- Reuses the account's **default VPC** (`vpc-0366a2050e40eaf62`) and its
  existing public subnets -- no new VPC, no NAT Gateway.
- **1x EC2 `t3.micro`** in a public subnet, Elastic IP attached, running the
  backend stack as three sibling Docker containers on a user-defined bridge
  network (no ECS/Fargate, no ALB, still just one instance):
  - `austial-backend` -- the FastAPI/Austial app (`python src/main.py`).
  - `austial-redis` -- `redis:7-alpine`, the Celery broker *and* result
    backend (`REDIS_URL=redis://redis:6379/0`). Plain container, not
    ElastiCache -- see the cost-ceiling note below.
  - `austial-worker` -- same image as the app, running
    `celery -A src.jobs.celery_app worker` instead of the API process.

  A one-off `austial-migrate` container (`python -m alembic upgrade head`,
  idempotent) runs before the API container starts, on every boot --
  keeping schema in sync without a separate manual SSM step.

  `docker-compose.yml` at `backend/docker-compose.yml` models the same
  three-service (plus local Postgres) shape for laptop dev; the EC2 host
  runs the equivalent as plain `docker run`s from `user_data.sh.tpl` rather
  than `docker compose` itself (no compose binary needed on the AMI).

  Security group allows inbound `8000/tcp` from `0.0.0.0/0` (demo
  endpoint, API container only -- Redis/worker are not exposed outside the
  Docker network) and no inbound `22` -- access for debugging is via **SSM
  Session Manager** (`aws ssm start-session --target <instance-id>`), using
  an instance profile with `AmazonSSMManagedInstanceCore` (+ ECR read-only
  so the instance can pull its own image, + scoped S3 access to the
  documents bucket below).

  Confirmed headroom on `t3.micro` (1 vCPU / 1GB RAM): app + Redis + worker
  together use well under half the instance's memory at idle
  (`free -h` shows ~400MB still available with all three running).
- **1x RDS `db.t3.micro` Postgres**, single-AZ, 20GB `gp3`,
  `publicly_accessible = false`. Security group only allows `5432` from the
  backend EC2's security group. Schema is managed by Alembic
  (`backend/alembic/`), not ORM `synchronize=True` -- see the migration
  container above.
- **1x ECR repository** (`austial-backend`) for the backend image.
- **1x S3 bucket** with static website hosting (public-read bucket policy
  scoped to the bucket's objects) for the Angular build output. No
  CloudFront -- plain HTTP S3 website endpoint.
- **1x private S3 bucket** (`austial-demo-documents-<account-id>`) for
  KYC/compliance documents (`DOCUMENTS_S3_BUCKET` env var), used only via
  presigned URLs from `backend/src/storage/object_storage_service.py`.
  Block-all-public-access, SSE-S3 encryption at rest (no new KMS key, to
  stay cheap), versioning enabled. The EC2 instance role has a scoped IAM
  policy (`s3:PutObject`/`GetObject`/`PutObjectAcl` on this bucket's
  objects only, not `s3:*` and not account-wide).

- **Ledger demo beneficiary details** (`LEDGER_BENEFICIARY_NAME`,
  `LEDGER_BENEFICIARY_BANK_NAME`, `LEDGER_BENEFICIARY_ACCOUNT_NUMBER`,
  `LEDGER_BENEFICIARY_SWIFT_BIC`) are plain Terraform variables (not
  secrets -- they're fictitious demo wire details shown to investors on a
  `FundingInstruction`, not a real bank account), defaulted in
  `variables.tf` and passed through `templatefile()` into both the
  `austial-backend` and `austial-worker` `docker run -e` flags in
  `user_data.sh.tpl`. `LedgerService` reads them via
  `config.get_or_throw(...)`, so a missing value fails the app at DI
  container build time, not silently.

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

`jwt_secret` is **not** a variable/tfvars entry -- it's generated by the
`random_password.jwt_secret` Terraform resource (64 chars, no special
characters, so it interpolates cleanly into the `docker run -e` command in
`user_data.sh.tpl`) and stored in Terraform state. It rotates (and forces
an EC2 instance replacement, since `user_data_replace_on_change = true`)
only if that resource is explicitly tainted/replaced -- a normal `plan`/
`apply` with no other changes leaves it stable.

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

The EC2 instance's user-data pulls `:latest` in a retry loop on first boot,
then runs the Alembic migration, then starts `austial-backend`,
`austial-redis`, and `austial-worker`. Because `user_data_replace_on_change
= true`, the simplest way to roll out a new image (or any user-data change)
to an already-running instance is to force it to be recreated, e.g.
`terraform apply -replace=aws_instance.backend` (after the image push
above) -- this re-runs the full user-data script including a fresh
`alembic upgrade head` (idempotent) against the same RDS instance.

To patch a running instance without a full replacement (faster, e.g. for a
same-schema image update), SSM in and run the equivalent by hand:
```bash
aws ssm start-session --target <instance-id> --profile aayush-gift
# inside the session:
docker pull <ecr-repo>:latest
docker run --rm --network austial-net -e DATABASE_URL="$DATABASE_URL" <ecr-repo>:latest python -m alembic upgrade head
docker stop austial-backend austial-worker && docker rm austial-backend austial-worker
# then the same two `docker run -d ...` commands from user_data.sh.tpl (backend + worker;
# austial-redis doesn't need restarting for an app-image-only update)
```

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
| S3 (frontend) | static site, a few hundred KB, low request volume | ~$0.05 |
| S3 (documents) | private bucket, near-empty, low request volume, versioning enabled | ~$0.05 |
| Data transfer | demo-level traffic | ~$1-2 |
| **Total** | | **~$18-27/mo** (lower for the first 12 months while EC2/EBS free tier applies) |

Redis and the Celery worker add **no incremental infra cost** -- they're
plain containers sharing the same already-budgeted EC2 instance, not a
managed ElastiCache/SQS service. This is the reason that option was chosen
over ElastiCache, which would have meant a second billable resource outside
the cost ceiling.

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
