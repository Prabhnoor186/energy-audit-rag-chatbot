terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-north-1"
}

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# 1. Encryption policy — required before a collection can be created.
#    Uses AWS-owned key (simplest option, no extra KMS cost).
# ---------------------------------------------------------------------------
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "rag-chatbot-encryption"
  type = "encryption"
  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource     = ["collection/rag-chatbot"]
      }
    ]
    AWSOwnedKey = true
  })
}

# ---------------------------------------------------------------------------
# 2. Network policy — controls who can reach the collection.
#    Public access here for simplicity (portfolio project, not production).
# ---------------------------------------------------------------------------
resource "aws_opensearchserverless_security_policy" "network" {
  name = "rag-chatbot-network"
  type = "network"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/rag-chatbot"]
        },
        {
          ResourceType = "dashboard"
          Resource     = ["collection/rag-chatbot"]
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# ---------------------------------------------------------------------------
# 3. Data access policy — controls which IAM identities can read/write data.
#    Grants access to the Lambda execution role (defined below) and to
#    whoever is running Terraform (so you can test/query manually too).
# ---------------------------------------------------------------------------
resource "aws_opensearchserverless_access_policy" "data_access" {
  name = "rag-chatbot-access"
  type = "data"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index"
          Resource     = ["index/rag-chatbot/*"]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        },
        {
          ResourceType = "collection"
          Resource     = ["collection/rag-chatbot"]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DescribeCollectionItems",
            "aoss:UpdateCollectionItems"
          ]
        }
      ]
      Principal = [
        data.aws_caller_identity.current.arn,
        aws_iam_role.lambda_rag_role.arn
      ]
    }
  ])
}

# ---------------------------------------------------------------------------
# NOTE: The OpenSearch Serverless collection itself is NOT created here.
# Terraform's AWS provider doesn't yet support NextGen (--generation NEXTGEN).
# Create it via AWS CLI AFTER running `terraform apply` for the policies above:
#
#   aws opensearchserverless create-collection-group \
#     --name rag-chatbot-group \
#     --generation NEXTGEN \
#     --standby-replicas DISABLED \
#     --region eu-north-1
#
#   aws opensearchserverless create-collection \
#     --name rag-chatbot \
#     --type VECTORSEARCH \
#     --collection-group-name rag-chatbot-group \
#     --standby-replicas DISABLED \
#     --region eu-north-1
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 4. IAM role that Lambda will assume to call Bedrock + OpenSearch.
# ---------------------------------------------------------------------------
resource "aws_iam_role" "lambda_rag_role" {
  name = "rag-chatbot-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_rag_policy" {
  name = "rag-chatbot-lambda-policy"
  role = aws_iam_role.lambda_rag_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      },
      {
        # Scoped by IAM action, not by collection ARN — since the collection
        # is created outside Terraform (via CLI), Terraform has no ARN to
        # reference here. "*" is fine at portfolio scale; for production
        # you'd tighten this once the collection ARN is known.
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Outputs — you'll need these for the embedding script and Lambda code
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 5. The Lambda function itself — runs lambda_function.py, using the IAM
#    role above. Code comes from lambda_package.zip (built via the packaging
#    steps: pip install into a folder, copy the .py file in, zip it).
# ---------------------------------------------------------------------------
resource "aws_lambda_function" "rag_chatbot" {
  function_name    = "rag-chatbot-lambda"
  role             = aws_iam_role.lambda_rag_role.arn
  handler          = "lambda_function.lambda_handler" # <filename>.<function name>
  runtime          = "python3.12"
  filename         = "lambda_package.zip"
  source_code_hash = filebase64sha256("lambda_package.zip") # tells Terraform to redeploy if the zip changes
  timeout          = 30                                     # max seconds before Lambda gives up (Bedrock+search can take a few seconds)
  memory_size      = 256
}

output "lambda_function_name" {
  value = aws_lambda_function.rag_chatbot.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.rag_chatbot.arn
}

# ---------------------------------------------------------------------------
# 6. API Gateway — gives the Lambda function a public HTTPS URL.
#    Using "HTTP API" (not the older "REST API") — simpler, cheaper, enough
#    for this project.
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_api" "rag_api" {
  name          = "rag-chatbot-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"] # allow any website (e.g. your Streamlit app) to call this
    allow_methods = ["POST"]
    allow_headers = ["content-type"]
  }
}

# Connects the API to your existing Lambda function
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.rag_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.rag_chatbot.invoke_arn
  payload_format_version = "2.0"
}

# Defines the actual endpoint path: POST /ask
resource "aws_apigatewayv2_route" "ask_route" {
  api_id    = aws_apigatewayv2_api.rag_api.id
  route_key = "POST /ask"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# "Stage" = a deployed, live version of the API (here: auto-deployed on every change)
resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.rag_api.id
  name        = "$default"
  auto_deploy = true
}

# Explicit permission: allows API Gateway (specifically) to invoke this Lambda.
# Without this, API Gateway would get an "access denied" calling Lambda.
resource "aws_lambda_permission" "allow_apigateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rag_chatbot.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.rag_api.execution_arn}/*/*"
}

output "api_endpoint" {
  value = "${aws_apigatewayv2_stage.default_stage.invoke_url}ask"
}
