# CWE-284: Improper Access Control — security group open to the world
# CIS AWS Foundations: 5.2 (no ingress from 0.0.0.0/0 to admin ports)
# Expected scanner: Volundr TerraformValidator (VOL-TF-0005, VOL-TF-0006)
# Expected severity: ERROR/WARNING
resource "aws_security_group" "wide_open" {
  name = "wide-open"

  ingress {
    from_port = 0
    to_port = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
