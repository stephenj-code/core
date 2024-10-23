variable "instance_type" {
  description = "The type of instance to use"
  type        = string
  default     = "t2.micro"
}

variable "ami_id" {
  description = "The AMI ID to use for the instances"
  type        = string
  default     = "ami-050cd642fd83388e4"
}

