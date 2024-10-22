variable "inst_type" {
  description = "The type of instance to use"
  type        = string
  default     = "t2.micro"
}

variable "tags" {
  description = "A map of tags to assign to the resources"
  type        = map(string)
  default = {
    CreateDate = formatdate("YYYY-MM-DD", timestamp())
    CreatedBy  = "Terraform"
  }
}