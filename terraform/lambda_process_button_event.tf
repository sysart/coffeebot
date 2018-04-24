data "archive_file" "lambda_process-button_event" {
  type        = "zip"
  source_dir = "../lambda-process-button-event"
  output_path = "${var.builddir}/lambda-process-button-event.zip"
}

resource "aws_s3_bucket_object" "lambda_process_button_event" {
  bucket = "${var.s3_deploybucket}"
  key    = "coffeebot/deploy/${terraform.workspace}/${local.version}/lambda-process-button-event.zip"
  source = "${var.builddir}/lambda-process-button-event.zip"
}

resource "aws_iam_role" "lambda_process_button_event_role" {
  name = "${local.resource_prefix}_lambda_process_button_event_role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": { "Service": "lambda.amazonaws.com" },
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "lambda_process_button_event_policy" {
  name = "${local.resource_prefix}_lambda_process_button_event_policy"
  role = "${aws_iam_role.lambda_process_button_event_role.id}"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query"
      ],
      "Resource": "${aws_dynamodb_table.brews.arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "${aws_lambda_function.process_coffee_event.arn}"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
      ],
        "Resource": [
          "arn:aws:logs:*:*:*"
      ]
    }
  ]
}
EOF
}

resource "aws_lambda_function" "process_button_event" {
  s3_bucket        = "${aws_s3_bucket_object.lambda_process_button_event.bucket}"
  s3_key           = "${aws_s3_bucket_object.lambda_process_button_event.key}"
  function_name    = "${local.resource_prefix}_process_button_event"
  role             = "${aws_iam_role.lambda_process_button_event_role.arn}"
  handler          = "handler.handler"
  runtime          = "python3.6"

  environment {
    variables = {
      DYNAMODB_REGION           = "${var.region}"
      DYNAMODB_BREW_TABLE       = "${aws_dynamodb_table.brews.name}"
      LAMBDA_PROCESS_BREW_EVENT = "${aws_lambda_function.process_coffee_event.function_name}"
    }
  }

  tags = { 
    version = "${local.version}"
  }
}
