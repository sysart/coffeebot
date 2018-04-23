#!/bin/sh
set -e

rm -rf _build
mkdir _build

version=$(git describe --tags --long)
echo ">>> Building version: $version"
echo "$version" > _build/version.info

echo ">>> running python tests for "
export PYTHONDONTWRITEBYTECODE=0
export DYNAMODB_BREW_TABLE=test_brews
export DYNAMODB_REGION=us-east-1
export LAMBDA_PROCESS_BREW_EVENT=mocked-process-coffee-event

pytest lambda-process-button-event
pytest lambda-process-coffee-event

# TODO: create zip, remove from terraform's responsibility
echo ""
echo ""
echo "Build successfull! (⌐■_■)"
echo ""
echo "Deploy instuctions:"
echo " 1) goto ./terraform"
echo " 2) do terraform init"
echo " 3) make sure you are on the right workspace ! (terraform.io/docs/commands/workspace)" 
echo " 4) terraform apply (carefully check changes before approving the deploy)"
echo ""
