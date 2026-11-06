variable "project_id" {
  description = "The course project, shared by the whole cohort."
  type        = string
  default     = "data-engineering-i1"
}

variable "region" {
  description = "Where every bucket and dataset lives. Fixed at creation: changing it destroys the resource."
  type        = string
  default     = "europe-west1"
}

variable "group" {
  description = "Our group. Every resource name starts with it."
  type        = string
  default     = "g04"
}
