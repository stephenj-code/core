provider "aws" {
    region = "us-east-2"
    profile = "default"
}

resource "aws_vpc" "main-vpc" {
  cidr_block = "20.24.0.0/16"

  tags = {
    Name = "main-vpc"
  }
}

resource "aws_subnet" "public-subnet" {
  vpc_id            = aws_vpc.main-vpc.id
  cidr_block        = "20.24.1.0/24"
  map_public_ip_on_launch = true

  tags = {
    Name = "main-subnet"
  }
}

resource "aws_instance" "inst-01" {
  ami           = "ami-050cd642fd83388e4" # Replace with the actual AMI ID for your region
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.main-subnet.id

  tags = {
    Name = "inst-00"
  }
}
