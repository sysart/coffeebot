Setup build environment
=======================

1) prerequisite:

    * Python 3.6
    * terraform (https://www.terraform.io/)

2) Install/update the following Python libraries:
    * boto3 (needed only in dev, available in aws lambda env)
    * moto (needed for testing)
    * pytest (needed for testing)

You can install the lbraries with  pip:
`
pip install boto3 moto pytest
`

3) create a secret.tfvars -file in your home directory. do NOT add it under folder. Within that file, setup your aws credentials like this:
`
access_key = "foo"
secret_key = "bar"
`
If you don't have AWS access keys, you can create them from the aws console. Instructions: https://docs.aws.amazon.com/general/latest/gr/managing-aws-access-keys.html

Build and run tests
===================

Use the build script to create the lambda packages and run all the tests:
`
./build.sh
`


Deploy to AWS
=============

NOTE: It is good practice to commit and push your changes before deploying. That way, the version tag will allow tracing back the code revision that was actually deployed

1) In your terminal, to to ./terraform and run
`
terraform init
`

2) Choose a deployment target (prod for production, any other name for deploying a test environment)
`
terraform workspace create my_dev
`
or for a previously created workspace:
`
terraform workspace select my_dev
`

3) Use terraform apply to deploy the environment. Before confirming the terraform plan CAREFULLY CHECK the suggested changes. Don't say we did not warn you ;)
´
terraform apply --var-file=~/secret.tfvars

4) Configure the iot buttons you want to use and add the triggers to the process button event lambda function

Things left to do
================

####Improve deployment 
Currently when deploying the process button event lambda it will not get the iot button trigger. This means that after each deploy you will manually need to add the trigger for the buttons you want to use. We could not figure out how to create the trigger correctly by using terraform, which is why we currently have to do it manually. The goal would be to be able to create the required button triggers automatically.

####Use for the stored data
We are storing all of the button events in dynamodb. Currently we do nothing with the data. The goal with this data would be to firstly visualize the data somehow, using something like to Amazon Quicksight. The second thing we would like to do is to add slash commands for the slack bot. Using a slash command should call an api gateway which triggers a lambda function which in turn fetches the required data from dynamodb. Users should be able to check how many brews have been made withing a certain time period.
