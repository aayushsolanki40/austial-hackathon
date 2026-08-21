data "aws_caller_identity" "current" {}

# --- Reuse the existing default VPC / public subnets -----------------------

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_subnet" "default" {
  for_each = toset(data.aws_subnets.default.ids)
  id       = each.value
}

locals {
  # Pick 2 subnets in distinct AZs (RDS subnet groups require >= 2 AZs).
  subnet_by_az = { for s in data.aws_subnet.default : s.availability_zone => s.id... }
  selected_azs = slice(sort(keys(local.subnet_by_az)), 0, 2)
  subnet_ids   = [for az in local.selected_azs : local.subnet_by_az[az][0]]
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# --- Security groups ---------------------------------------------------------

resource "aws_security_group" "ec2" {
  name        = "${var.project}-${var.environment}-ec2"
  description = "Austial backend EC2 -- inbound app port only, no SSH (SSM used for access)"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "App port (demo/test endpoint)"
    from_port   = var.app_port
    to_port     = var.app_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound (ECR pulls, SSM, RDS, package installs)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project}-${var.environment}-ec2"
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.project}-${var.environment}-rds"
  description = "Austial RDS -- Postgres access from the backend EC2 SG only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Postgres from backend EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project}-${var.environment}-rds"
  }
}

# --- IAM role for SSM (no SSH key pair, no inbound needed for SSM) ---------

resource "aws_iam_role" "ec2" {
  name = "${var.project}-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# EC2 needs to pull from the ECR repo it runs images from.
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2.name
}

# --- ECR repository for the backend image -----------------------------------

resource "aws_ecr_repository" "backend" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }

  force_delete = true

  tags = {
    Name = "${var.project}-${var.environment}-backend"
  }
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# --- RDS Postgres (single-AZ, private) --------------------------------------

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-${var.environment}-db-subnets"
  subnet_ids = local.subnet_ids

  tags = {
    Name = "${var.project}-${var.environment}-db-subnets"
  }
}

resource "aws_db_instance" "main" {
  identifier     = "${var.project}-${var.environment}-db"
  engine         = "postgres"
  instance_class = var.db_instance_class

  allocated_storage = var.db_allocated_storage
  storage_type      = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az                = false
  publicly_accessible     = false
  skip_final_snapshot     = true
  deletion_protection     = false
  backup_retention_period = 1
  apply_immediately       = true

  tags = {
    Name = "${var.project}-${var.environment}-db"
  }
}

# --- EC2 backend host ---------------------------------------------------------

resource "aws_instance" "backend" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = local.subnet_ids[0]
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  # Depends on RDS being up front so the connection string in user-data is
  # meaningful the first time the container starts (it's a fixed value the
  # provider computes at plan time regardless, but wait for the DB anyway).
  depends_on = [aws_db_instance.main]

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    ecr_repo_url = aws_ecr_repository.backend.repository_url
    ecr_registry = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
    aws_region   = var.aws_region
    image_tag    = var.container_image_tag
    app_port     = var.app_port
    db_endpoint  = aws_db_instance.main.endpoint
    db_username  = var.db_username
    db_password  = var.db_password
    db_name      = var.db_name
    api_key      = var.api_key
  })

  root_block_device {
    # al2023 AMIs ship a snapshot >= 30GB; a smaller root volume is rejected
    # at launch time ("Volume of size 8GB is smaller than snapshot ...").
    # 30GB gp3 is still within EBS free-tier (30GB/mo) so this adds ~$0 cost.
    volume_size = 30
    volume_type = "gp3"
  }

  tags = {
    Name = "${var.project}-${var.environment}-backend"
  }
}

resource "aws_eip" "backend" {
  instance = aws_instance.backend.id
  domain   = "vpc"

  tags = {
    Name = "${var.project}-${var.environment}-backend-eip"
  }
}

# --- S3 static site for the Angular frontend --------------------------------

resource "aws_s3_bucket" "frontend" {
  bucket        = "${var.project}-${var.environment}-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = true

  tags = {
    Name = "${var.project}-${var.environment}-frontend"
  }
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadGetObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}
