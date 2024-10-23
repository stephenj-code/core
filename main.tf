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

resource "aws_internet_gateway" "main-igw" {
  vpc_id = aws_vpc.main-vpc.id

  tags = {
    Name       = "main-igw"
    CreatedBy  = "Terraform"
  }
}

resource "aws_route_table" "public-route-table" {
  vpc_id = aws_vpc.main-vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main-igw.id
  }

  tags = {
    Name       = "public-route-table"
    CreatedBy  = "Terraform"
  }
}

resource "aws_route_table_association" "public-subnet-association" {
  subnet_id      = aws_subnet.public-subnet.id
  route_table_id = aws_route_table.public-route-table.id
}




resource "aws_eip" "nat_eip" {
  domain = "vpc"
}

resource "aws_nat_gateway" "main-nat-gateway" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public-subnet.id

  tags = {
    Name       = "main-nat-gateway"
    CreatedBy  = "Terraform"
  }
}


resource "aws_route_table" "private-route-table" {
  vpc_id = aws_vpc.main-vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_nat_gateway.main-nat-gateway.id
  }

  tags = {
    Name       = "private-route-table"
    CreatedBy  = "Terraform"
  }
}


resource "aws_route_table_association" "private-subnet-association" {
  subnet_id      = aws_subnet.private-subnet.id
  route_table_id = aws_route_table.private-route-table.id
}

resource "aws_security_group" "http-sg" {
  name        = "http-sg"
  description = "Allow HTTP traffic"
  vpc_id      = aws_vpc.main-vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name       = "http-sg"
    CreatedBy  = "Terraform"
  }
}

resource "aws_security_group" "ssh-sg" {
  name        = "ssh-sg"
  description = "Allow SSH traffic"
  vpc_id      = aws_vpc.main-vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name       = "ssh-sg"
    CreatedBy  = "Terraform"
  }
}


resource "aws_instance" "public-instance-01" {
  ami           = var.ami_id # Replace with the actual AMI ID for your region
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public-subnet.id
  key_name      = "bastion-ssh"
  vpc_security_group_ids = [
    aws_security_group.http-sg.id,
    aws_security_group.ssh-sg.id
  ]
  associate_public_ip_address = true

  user_data = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y nginx
    echo "<h1>Hello, World from NGINX!</h1>" > /var/www/html/index.html
    systemctl start nginx
    systemctl enable nginx
    EOF
    
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
  vpc_security_group_ids = [aws_security_group.ssh-sg.id]

  tags = {
    Name       = "private-instance-01"
    CreatedBy  = "Terraform"
  }
} 