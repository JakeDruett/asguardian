# CWE-311: Missing Encryption of Sensitive Data — RDS without storage encryption
# CIS AWS Foundations: 2.3.1 (ensure RDS encryption is enabled)
# Expected scanner: Volundr TerraformValidator (VOL-TF-0004)
# Expected severity: ERROR/WARNING
resource "aws_db_instance" "plain" {
  identifier     = "plain-db"
  engine         = "postgres"
  instance_class = "db.t3.micro"
  username       = "app"
}
