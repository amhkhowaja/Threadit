variable "region" {
  type    = string
  default = "us-east-1"
}

variable "use_floci" {
  type        = bool
  default     = false
  description = "When true, target the local Floci emulator at floci_endpoint."
}

variable "floci_endpoint" {
  type    = string
  default = "http://localhost:4566"
}

variable "name_prefix" {
  type    = string
  default = "threadit-dev"
}

variable "table_name" {
  type    = string
  default = "threadit"
}

variable "ddb_billing_mode" {
  type    = string
  default = "PAY_PER_REQUEST"
}

# Capability toggles for Floci parity gaps (FLOCI doc §4.2).
variable "enable_dax" {
  type    = bool
  default = true
}

variable "enable_cloudfront" {
  type    = bool
  default = true
}

variable "enable_xray" {
  type    = bool
  default = true
}
