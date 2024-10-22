provider "aws" {
    region = "us-east-2"
    profile = "default"
}

resource "aws_instance" "chicken-wing" {
  ami           = "ami-050cd642fd83388e4" # Replace with the actual AMI ID for your region
  instance_type = "t2.micro"

  tags = {
    Name = "MyTerraformInstance"
  }
}

