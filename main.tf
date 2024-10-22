locals {
  current_date = formatdate("YYYY-MM-DD", timestamp())
}

resource "aws_key_pair" "bastion_ssh" {
  key_name   = "bastion-ssh"
  public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCgi3D91XGebEMLzMJZfM5RHbZykyDt3XAbrL1YUB+v2O++YCYitf+XlGqXX4QrSt+vaxD7CNSSa4nKw7508MShwBBkiQp8ZAP7L7DIFKmQUdw4Z09eiRK+DzoEFv5/DR9ZzBp+u0Mh0THafKM4Gi8ZJSfx9ee0wZ6YriKb6NyXAH2Tdcbi4ie7VdWSfDs5Y0z9B+AmsK1ZuekgbEv3OlmQeX06D4h+WY8sZXz2yl+ZkvhaMSR4VunmR43bLJRAEGf2rvE4taWDJPaWKcL89bkwFhMRpUwgVP+3vn2q08eJY7AjnDbSeKfzzlHU8O2L+VvAVrpkdqMlLvVgmBQ7XNhN" # Path to your public key file
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
  key_name      = "bastion-ssh"

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
  key_name      = "bastion-ssh"

  tags = {
    Name       = "private-instance-01"
    CreateDate = local.current_date
    CreatedBy  = "Terraform"
  }
}