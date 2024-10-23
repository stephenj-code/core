# main.tf

provider "aws" {
  region = "us-east-2"
}

resource "aws_vpc" "main-vpc" {
  cidr_block = "20.24.0.0/16"

  tags = {
    Name       = "main-vpc"
    CreatedBy  = "Terraform"
  }
}

resource "aws_subnet" "private-subnet" {
  vpc_id                  = aws_vpc.main-vpc.id
  cidr_block              = "20.24.0.0/24"
  map_public_ip_on_launch = false

  tags = {
    Name       = "private-subnet"
    CreatedBy  = "Terraform"
  }
}

resource "aws_subnet" "public-subnet" {
  vpc_id                  = aws_vpc.main-vpc.id
  cidr_block              = "20.24.1.0/24"
  map_public_ip_on_launch = true

  tags = {
    Name       = "public-subnet"
    CreatedBy  = "Terraform"
  }
}


resource "aws_instance" "public-instance-01" {
  ami           = var.ami_id # Replace with the actual AMI ID for your region
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public-subnet.id
  key_name      = "bastion-ssh"

  tags = {
    Name       = "public-instance-01"
    CreatedBy  = "Terraform"
  }
}

resource "aws_instance" "private-instance-01" {
  ami           = var.ami_id # Replace with the actual AMI ID for your region
  instance_type = var.instance_type
  subnet_id     = aws_subnet.private-subnet.id
  key_name      = "bastion-ssh"

  tags = {
    Name       = "private-instance-01"
    CreatedBy  = "Terraform"
  }
}