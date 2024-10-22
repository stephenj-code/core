locals {
  current_date = formatdate("YYYY-MM-DD", timestamp())
}

resource "aws_vpc" "main-vpc" {
  cidr_block = "20.24.0.0/16"

  tags = {
    Name       = "main-vpc"
    CreateDate = local.current_date
    CreatedBy  = "Terraform"
  }
}

resource "aws_subnet" "private-subnet" {
  vpc_id                  = aws_vpc.main-vpc.id
  cidr_block              = "20.24.0.0/24"
  map_public_ip_on_launch = false

  tags = {
    Name       = "private-subnet"
    CreateDate = local.current_date
    CreatedBy  = "Terraform"
  }
}

resource "aws_subnet" "public-subnet" {
  vpc_id                  = aws_vpc.main-vpc.id
  cidr_block              = "20.24.1.0/24"
  map_public_ip_on_launch = true

  tags = {
    Name       = "public-subnet"
    CreateDate = local.current_date
    CreatedBy  = "Terraform"
  }
}

resource "aws_instance" "public-instance-01" {
  ami           = "ami-050cd642fd83388e4" # Replace with the actual AMI ID for your region
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.public-subnet.id

  tags = {
    Name       = "public-instance-01"
    CreateDate = local.current_date
    CreatedBy  = "Terraform"
  }
}

resource "aws_instance" "private-instance-01" {
  ami           = "ami-050cd642fd83388e4" # Replace with the actual AMI ID for your region
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.private-subnet.id

  tags = {
    Name       = "private-instance-01"
    CreateDate = local.current_date
    CreatedBy  = "Terraform"
  }
}