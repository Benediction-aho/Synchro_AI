# SYNCHRO Infrastructure - AWS + Supabase
# Phase 5: Production Infrastructure

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  
  backend "s3" {
    bucket         = "synchro-terraform-state"
    key            = "phase5/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "synchro-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "synchro"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

# ============================================================
# VPC & Networking
# ============================================================
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  
  name = "synchro-${var.environment}"
  
  cidr_block = "10.0.0.0/16"
  
  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway     = true
  single_nat_gateway     = var.environment == "staging"
  enable_dns_hostnames   = true
  enable_dns_support     = true
  
  tags = {
    Name = "synchro-${var.environment}-vpc"
  }
}

# VPC Flow Logs for security monitoring
resource "aws_flow_log" "vpc" {
  iam_role_arn    = aws_iam_role.flow_logs.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = module.vpc.vpc_id
  
  depends_on = [aws_iam_role_policy.flow_logs]
}

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = "/aws/vpc/synchro-${var.environment}-flowlogs"
  retention_in_days = 30
}

resource "aws_iam_role" "flow_logs" {
  name = "synchro-${var.environment}-flowlogs-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "vpc-flow-logs.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  role = aws_iam_role.flow_logs.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "*"
    }]
  })
}

# ============================================================
# ECS Cluster (Fargate)
# ============================================================
resource "aws_ecs_cluster" "main" {
  name = "synchro-${var.environment}"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs_exec.name
      }
    }
  }
}

resource "aws_cloudwatch_log_group" "ecs_exec" {
  name              = "/aws/ecs/synchro-${var.environment}-exec"
  retention_in_days = 30
}

# ============================================================
# Application Load Balancer
# ============================================================
resource "aws_lb" "main" {
  name               = "synchro-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets
  
  enable_deletion_protection = var.environment == "production"
  
  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    prefix  = "alb-logs"
    enabled = true
  }
}

resource "aws_s3_bucket" "alb_logs" {
  bucket = "synchro-${var.environment}-alb-logs-${random_id.suffix.hex}"
  
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
  
  lifecycle_rule {
    enabled = true
    expiration {
      days = 90
    }
  }
}

resource "aws_lb_target_group" "api" {
  name        = "synchro-${var.environment}-api"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  
  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    matcher             = "200"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_security_group" "alb" {
  name        = "synchro-${var.environment}-alb-sg"
  description = "ALB security group"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ============================================================
# ECS Task Execution Role
# ============================================================
resource "aws_iam_role" "ecs_task_execution" {
  name = "synchro-${var.environment}-ecs-task-execution"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Custom policy for Secrets Manager + CloudWatch
resource "aws_iam_policy" "ecs_task_custom" {
  name = "synchro-${var.environment}-ecs-task-custom"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:synchro/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_custom" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = aws_iam_policy.ecs_task_custom.arn
}

# ============================================================
# ECS Task Role (for application permissions)
# ============================================================
resource "aws_iam_role" "ecs_task" {
  name = "synchro-${var.environment}-ecs-task"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "ecs_task_app" {
  name = "synchro-${var.environment}-ecs-task-app"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:synchro/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage"
        ]
        Resource = "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:synchro-*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_app" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task_app.arn
}

# ============================================================
# ECS Services (API Gateway, Data Ingestion, Learning Worker, Evolution Worker)
# ============================================================
locals {
  service_names = ["api-gateway", "data-ingestion", "learning-worker", "evolution-worker"]
}

resource "aws_ecs_task_definition" "services" {
  for_each = toset(local.service_names)
  
  family                = "synchro-${var.environment}-${each.key}"
  network_mode          = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                   = each.key == "api-gateway" ? "512" : "256"
  memory                = each.key == "api-gateway" ? "1024" : "512"
  execution_role_arn    = aws_iam_role.ecs_task_execution.arn
  task_role_arn         = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([
    {
      name      = each.key
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/synchro-${each.key}:${var.image_tag}"
      cpu       = each.key == "api-gateway" ? 512 : 256
      memory    = each.key == "api-gateway" ? 1024 : 512
      essential = true
      
      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]
      
      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "SERVICE_NAME", value = each.key }
      ]
      
      secrets = [
        { name = "DATABASE_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:synchro/database-url" },
        { name = "JWT_SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:synchro/jwt-secret" },
        { name = "ENCRYPTION_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:synchro/encryption-key" },
        { name = "REDIS_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:synchro/redis-url" },
        { name = "DERIV_WS_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:synchro/deriv-ws-url" }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/synchro-${var.environment}-${each.key}"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      
      healthCheck = {
        command  = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval = 30
        timeout  = 10
        retries  = 3
      }
    }
  ])
}

resource "aws_cloudwatch_log_group" "ecs_services" {
  for_each = toset(local.service_names)
  
  name              = "/ecs/synchro-${var.environment}-${each.key}"
  retention_in_days = 30
}

resource "aws_ecs_service" "services" {
  for_each = toset(local.service_names)
  
  name            = "synchro-${var.environment}-${each.key}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.services[each.key].arn
  desired_count   = each.key == "api-gateway" ? 2 : 1
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = each.key
    container_port   = 8000
  }
  
  deployment_controller {
    type = "ECS"
  }
  
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "synchro-${var.environment}-ecs-tasks-sg"
  description = "ECS tasks security group"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ============================================================
# ElastiCache Redis
# ============================================================
resource "aws_elasticache_subnet_group" "redis" {
  name       = "synchro-${var.environment}-redis-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "redis" {
  name        = "synchro-${var.environment}-redis-sg"
  description = "Redis security group"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "synchro-${var.environment}-redis"
  
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.environment == "production" ? "cache.r6g.xlarge" : "cache.t3.micro"
  number_cache_clusters = var.environment == "production" ? 2 : 1
  
  port                 = 6379
  parameter_group_name = "default.redis7"
  
  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]
  
  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled           = var.environment == "production"
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = true
  auth_token                 = var.redis_auth_token
  
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_logs.arn
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }
  
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_logs.arn
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }
}

resource "aws_cloudwatch_log_group" "redis_logs" {
  name              = "/aws/elasticache/synchro-${var.environment}-redis"
  retention_in_days = 30
}

# ============================================================
# Secrets Manager
# ============================================================
resource "aws_secretsmanager_secret" "secrets" {
  for_each = toset([
    "database-url",
    "jwt-secret",
    "encryption-key",
    "redis-url",
    "deriv-ws-url",
    "bridge/hmac-key"
  ])
  
  name        = "synchro/${each.key}"
  description = "SYNCHRO ${each.key} for ${var.environment}"
  
  rotation_rules {
    automatically_after_days = 90
  }
}

# ============================================================
# S3 Buckets (backups, model versions, reports)
# ============================================================
resource "aws_s3_bucket" "data" {
  bucket = "synchro-${var.environment}-data-${random_id.suffix.hex}"
  
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    enabled = true
    
    noncurrent_version_expiration {
      days = 90
    }
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ============================================================
# Monitoring (CloudWatch + Grafana Cloud integration)
# ============================================================
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "synchro-${var.environment}"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ClusterName", "synchro-${var.environment}"],
            ["AWS/ECS", "MemoryUtilization", "ClusterName", "synchro-${var.environment}"]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "ECS Cluster Utilization"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", "TargetGroup", aws_lb_target_group.api.arn_suffix],
            ["AWS/ApplicationELB", "HTTPCode_Target_2XX_Count", "TargetGroup", aws_lb_target_group.api.arn_suffix],
            ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "TargetGroup", aws_lb_target_group.api.arn_suffix],
            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "TargetGroup", aws_lb_target_group.api.arn_suffix]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "ALB Metrics"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", "ReplicationGroup", "synchro-${var.environment}-redis"],
            ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage", "ReplicationGroup", "synchro-${var.environment}-redis"],
            ["AWS/ElastiCache", "CurrConnections", "ReplicationGroup", "synchro-${var.environment}-redis"]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Redis Metrics"
        }
      }
    ]
  })
}

# ============================================================
# Data Sources
# ============================================================
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# ============================================================
# Outputs
# ============================================================
output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "redis_endpoint" {
  value     = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive = true
}

output "redis_port" {
  value = aws_elasticache_replication_group.redis.port
}