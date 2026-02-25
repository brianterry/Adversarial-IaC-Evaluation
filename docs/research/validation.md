# Ground Truth Validation

A key research concern for adversarial benchmarks: **who validates the validator?**

The Red Team declares vulnerabilities in a manifest that it generates itself. How do we know these vulnerabilities actually exist in the code? This page explains the validation system that addresses this concern.

## The Ground Truth Problem

In the adversarial framework:

1. Red Team generates code with "hidden vulnerabilities"
2. Red Team declares these vulnerabilities in a manifest
3. Judge scores Blue Team against this manifest

**But what if the Red Team hallucinates?** If it claims a vulnerability that doesn't exist, Blue Team gets penalized for "missing" something that was never there.

## Solution: External Validation

The framework uses **static analysis tools** (Trivy, Checkov) as an independent oracle to validate Red Team claims.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GROUND TRUTH VALIDATION FLOW                          │
└─────────────────────────────────────────────────────────────────────────┘

  RED TEAM OUTPUT
  ├── main.tf (generated code)
  └── manifest.json (claimed vulns: V1, V2, V3, V4, V5)
                              │
                              ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │  🔍 MANIFEST VALIDATOR                                                 │
  │                                                                        │
  │  Step 1: Run Trivy on generated code                                   │
  │  Step 2: Run Checkov on generated code                                 │
  │  Step 3: Compare tool findings to manifest claims                      │
  │  Step 4: Calculate manifest accuracy                                   │
  └────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  VALIDATION RESULT
  ├── Confirmed: V1, V2, V3, V4 (tools found these)
  ├── Unconfirmed: V5 (tools didn't find this)
  └── Manifest Accuracy: 80%
```

## Validation Metrics

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Manifest Accuracy** | Confirmed / Claimed | % of Red Team claims verified by tools |
| **Hallucination Rate** | Unconfirmed / Claimed | % of claims NOT found by tools |
| **Tool Coverage** | Per-tool breakdown | Which tools confirmed which vulns |

## Enabling Validation

Validation runs automatically when static tools are enabled:

```bash
# Enable Trivy and Checkov for validation
adversarial-iac game --use-trivy --use-checkov ...
```

Or in the interactive wizard, enable static tools under "Advanced Options".

## Validation Output

Each game produces a `manifest_validation.json` file:

```json
{
  "metrics": {
    "manifest_accuracy": 0.80,
    "hallucination_rate": 0.20,
    "total_claimed": 5,
    "total_confirmed": 4,
    "total_unconfirmed": 1
  },
  "tool_coverage": {
    "trivy_confirmed": 3,
    "checkov_confirmed": 4,
    "both_confirmed": 3
  },
  "confirmed_vuln_ids": ["V1", "V2", "V3", "V4"],
  "unconfirmed_vuln_ids": ["V5"],
  "vuln_validation": [
    {
      "vuln_id": "V1",
      "confirmed": true,
      "confirmed_by_trivy": true,
      "confirmed_by_checkov": true,
      "trivy_matches": [{"finding_id": "...", "title": "..."}],
      "checkov_matches": [{"finding_id": "...", "title": "..."}],
      "confidence": 0.95
    },
    {
      "vuln_id": "V5",
      "confirmed": false,
      "confirmed_by_trivy": false,
      "confirmed_by_checkov": false,
      "trivy_matches": [],
      "checkov_matches": [],
      "confidence": 0.0
    }
  ]
}
```

## Interpreting Unconfirmed Vulnerabilities

An "unconfirmed" vulnerability could be:

### 1. Tool-Blind (Real but Not Detected)

The vulnerability exists, but static tools don't have a rule for it.

**Example:** Red Team injects a subtle logic flaw where IAM permissions are technically correct but semantically overpermissive. Tools don't flag it, but it's still a real vulnerability.

**Action:** Manual review confirms validity. Include in ground truth.

### 2. Hallucinated (Doesn't Exist)

The LLM claimed to inject a vulnerability but the code doesn't actually have it.

**Example:** Red Team says "I made the S3 bucket public" but the generated code actually has `acl = "private"`.

**Action:** Manual review reveals false claim. Exclude from ground truth scoring.

### 3. Partially Injected

The vulnerability was attempted but incomplete.

**Example:** Red Team intended to disable encryption but only removed one of two required settings.

**Action:** Judgment call based on exploitability.

## Research Recommendations

For publication-quality results:

1. **Report Manifest Accuracy** — Include mean ± std across all games
2. **Manual Audit Sample** — Review 10-20% of unconfirmed vulnerabilities
3. **Categorize Unconfirmed** — Tool-blind vs hallucinated vs partial
4. **Adjusted Scoring** — Optionally exclude hallucinated vulns from recall calculation

### Sample Paper Table

| Metric | Value |
|--------|-------|
| Total Vulnerabilities Claimed | 250 |
| Confirmed by Static Tools | 198 (79.2%) |
| Unconfirmed | 52 (20.8%) |
| - Tool-Blind (manual verified) | 41 (78.8% of unconfirmed) |
| - Hallucinated | 8 (15.4% of unconfirmed) |
| - Partial/Unclear | 3 (5.8% of unconfirmed) |
| **Adjusted Manifest Accuracy** | **95.7%** |

## Comparative Experiment Runner

Use the comparative experiment script to generate validation statistics:

```bash
python scripts/run_comparative_experiment.py --scenarios 20

# Outputs include:
# - Manifest accuracy by mode (single vs pipeline)
# - Hallucination rates
# - LaTeX tables for paper
```

## Programmatic Access

```python
from src.validation import ManifestValidator, validation_to_dict

validator = ManifestValidator(
    use_trivy=True,
    use_checkov=True,
    language="terraform",
)

validation = validator.validate(code, manifest)

print(f"Manifest Accuracy: {validation.manifest_accuracy:.1%}")
print(f"Confirmed: {validation.confirmed_vulns}")
print(f"Unconfirmed: {validation.unconfirmed_vulns}")
```

## Tool Triangulation in Judging

Beyond manifest validation, static tools also provide **corroboration for Judge decisions**. When enabled, the Judge creates a special "Corroborated" match tier:

### How It Works

1. Red Team claims vulnerability V on resource R
2. Blue Team finds issue F on resource R
3. Static tools also flag resource R

If all three agree, the match is **corroborated** — providing a non-LLM external anchor.

### Example Output

```json
{
  "matches": [
    {
      "red_vuln_id": "V1",
      "blue_finding_id": "F1",
      "match_type": "corroborated",
      "confidence": 0.92,
      "corroborated_by_tool": true,
      "explanation": "[TOOL CORROBORATED] Exact match on S3 encryption"
    }
  ],
  "corroborated_matches": 3,
  "corroboration_rate": 0.60
}
```

### Why This Matters for Research

The corroborated tier directly addresses the LLM circularity concern:

> "You're using an LLM to judge whether another LLM's findings match a third LLM's claimed vulnerabilities."

Corroborated matches are **not dependent on LLM judgment** — they have external tool confirmation. Report the corroboration rate alongside your results.

## Tool-Blind Vulnerabilities

Static tools (Trivy, Checkov) have known coverage gaps:

| Category | Examples | Why Tools Miss It |
|----------|----------|-------------------|
| **Logic-Level IAM** | Overly permissive policies that are syntactically valid | No semantic understanding |
| **Cross-Resource** | Vulnerabilities requiring multi-resource reasoning | Single-resource checks |
| **Context-Dependent** | Settings only wrong in certain scenarios | No scenario awareness |

These "tool-blind" vulnerabilities represent a **harder class of security reasoning** that static tools cannot reach. This makes LLM-based detection more interesting, not less rigorous.

### Recommendation for Papers

Characterize unconfirmed vulnerabilities as either:

1. **Tool-blind** — real vulnerability, tools lack coverage
2. **Hallucinated** — LLM falsely claimed a vulnerability

Manual audit of a sample (10-20%) distinguishes these cases.

## Limitations

1. **Tool Coverage** — Trivy/Checkov don't detect all vulnerability types
2. **Matching Precision** — Tool findings are matched heuristically to manifest claims
3. **Not a Complete Oracle** — Absence of tool finding ≠ absence of vulnerability

Despite these limitations, static tool validation provides valuable **corroborating evidence** for Red Team claims and Judge decisions, significantly strengthening research validity.
