variable "inst_type" {
  description = "The type of instance to use"
  type        = string
}

variable "tags" {
  description = "A map of tags to assign to the resources"
  type        = map(string)
  default = {
    CreatedBy  = "Terraform"
    Identifier = "main-vpc"
  }
}