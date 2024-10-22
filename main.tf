provider "aws" {
    region = "us-east-2"
    profile = "default"
}

resource "aws_instance" "chicken-wing" {
  ami           = "ami-06b21ccaeff8cd686" # Replace with the actual AMI ID for your region
  instance_type = "t2.micro"

  tags = {
    Name = "MyTerraformInstance"
  }
}

