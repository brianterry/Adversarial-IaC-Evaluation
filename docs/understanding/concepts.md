# Key Concepts

## Scenario

A text description of infrastructure to create. Examples:

- "Create an S3 bucket for healthcare PHI data with HIPAA compliance"
- "Create a VPC with public and private subnets and NAT gateway"
- "Create IAM roles for a CI/CD pipeline with least privilege"

114 scenarios across 18 domains. Use `adversarial-iac scenarios` to browse.

## Difficulty

Controls how many vulnerabilities Red Team injects and how stealthy they are:

| Level | Vulns | Style |
|-------|-------|-------|
| Easy | 2-3 | Obvious (missing encryption, public access) |
| Medium | 3-4 | Subtle (overly permissive IAM, weak defaults) |
| Hard | 4-5 | Stealthy (dynamic refs, conditional misconfig) |

## Manifest

The Red Team's secret list of what they hid. Stored in `red_team_manifest.json`. Each entry has vulnerability type, location, and evidence. The Judge uses this as ground truth.

## Findings

The Blue Team's reported issues. Stored in `blue_team_findings.json`. Each has severity, location, evidence, and remediation. The Judge matches these to manifest entries.

## Scoring Terms

| Term | Definition |
|------|------------|
| **TP (True Positive)** | Blue correctly found a Red vulnerability |
| **FP (False Positive)** | Blue reported something not in the manifest |
| **FN (False Negative)** | Red vulnerability that Blue missed |
| **Precision** | TP / (TP + FP) — Blue's accuracy |
| **Recall** | TP / (TP + FN) — % of vulns Blue found |
| **F1** | 2 × (P × R) / (P + R) — balanced score |
| **Evasion Rate** | FN / Total — Red's success at hiding |
