resource "aws_dynamodb_table" "brews" {
  name           = "${local.resource_prefix}_brews"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "coffeemakerId"
  range_key      = "startTime"

  attribute {
    name = "coffeemakerId"
    type = "S"
  }

  attribute {
    name = "startTime"
    type = "S"
  }
}