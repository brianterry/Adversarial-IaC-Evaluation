# Experiment Rerun Plan (v2.3 Framework Fixes)

All experiments rerun from scratch with v2.3 methodology:
- Mixed vulnerability sourcing (50% novel)
- Precision verification filter
- Trivy/Checkov manifest validation gate
- Cross-provider phantom concordance mitigation

## Prerequisites (Amazon Linux 2023)

### Step 1: System Packages

AL2023 ships Python 3.9 by default. Install Python 3.11+ and build dependencies:

```bash
# Update system
sudo dnf update -y

# Install Python 3.11 and development headers
sudo dnf install -y python3.11 python3.11-pip python3.11-devel

# Build tools for compiled deps (numpy, scipy, pandas)
sudo dnf install -y gcc gcc-c++ make

# Git (should already be present, but confirm)
sudo dnf install -y git
```

Verify:
```bash
python3.11 --version   # Should print Python 3.11.x
pip3.11 --version       # Should print pip ... (python 3.11)
gcc --version           # Should print gcc (GCC) 11.x+
```

### Step 2: Install Trivy (Amazon Linux 2023)

```bash
# Add the Trivy yum repository
cat << 'EOF' | sudo tee /etc/yum.repos.d/trivy.repo
[trivy]
name=Trivy repository
baseurl=https://aquasecurity.github.io/trivy-repo/rpm/releases/$basearch/
gpgcheck=1
enabled=1
gpgkey=https://aquasecurity.github.io/trivy-repo/rpm/public.key
EOF

sudo dnf install -y trivy
trivy --version   # Verify installation
```

### Step 3: Virtual Environment & Python Dependencies

```bash
# Create and activate venv with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install the project in editable mode (pulls all deps from pyproject.toml)
pip install -e .

# Install dev dependencies (pytest, black, flake8, mypy)
pip install -e ".[dev]"

# Install Checkov (IaC static analysis)
pip install checkov
```

### Step 4: Configure Matplotlib for Headless Environment

AL2023 has no display server. Set the non-interactive backend:

```bash
# Create matplotlib config
mkdir -p ~/.config/matplotlib
echo "backend: Agg" > ~/.config/matplotlib/matplotlibrc
```

### Step 5: Verify All Python Dependencies

```bash
# Quick import check for every critical package (uses importlib.metadata for packages
# like langchain_aws that don't expose __version__)
python -c "
import importlib.metadata
pkgs = [
    'langchain', 'langchain-aws', 'langchain-openai', 'langchain-google-genai',
    'langgraph', 'openai', 'boto3', 'click', 'rich', 'pydantic', 'PyYAML',
    'pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn', 'questionary',
]
for pkg in pkgs:
    v = importlib.metadata.version(pkg)
    print(f'{pkg:25} {v}')
print('\n✓ All Python dependencies OK')
"
```

### Step 6: Verify External Tools

```bash
# Trivy
trivy --version

# Checkov
checkov --version

# AWS CLI (pre-installed on AL2023, but verify credentials)
aws --version
aws sts get-caller-identity   # Must succeed — confirms IAM role/creds

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[0].modelId' --output text
```

### Step 7: Environment Variables

```bash
cp .env_template .env
```

Edit `.env` and set:
```bash
# Required for all experiments
AWS_REGION=us-east-1

# Required for cross-provider judge (phantom concordance mitigation)
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...

# Required for E1-S2, E1-S3 (DashScope/Qwen3.5 experiments)
DASHSCOPE_API_KEY=sk-...
```

Verify keys are loaded:
```bash
source .env  # or use python-dotenv auto-loading
python -c "
import os
keys = ['AWS_REGION', 'OPENAI_API_KEY', 'GOOGLE_API_KEY']
for k in keys:
    v = os.environ.get(k, '')
    status = '✓' if v else '✗ MISSING'
    print(f'  {status}  {k}')
dash = os.environ.get('DASHSCOPE_API_KEY', '')
print(f\"  {'✓' if dash else '⚠ optional'}  DASHSCOPE_API_KEY (needed for E1-S2, E1-S3)\")
"
```

### Step 8: Model Access Verification

Confirm all models are activated in us-east-1 Bedrock console:
- `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- `us.anthropic.claude-3-5-haiku-20241022-v1:0`
- `us.amazon.nova-premier-v1:0`
- `amazon.nova-pro-v1:0`
- `us.meta.llama3-3-70b-instruct-v1:0`
- `us.deepseek.r1-v1:0`
- `qwen.qwen3-coder-30b-a3b-v1:0`
- `qwen.qwen3-32b-v1:0`
- `moonshot.kimi-k2-thinking`
- `openai.gpt-oss-120b-1:0`
- `deepseek.v3.2`

### Step 9: Smoke Test

Run one game to confirm v2.3 fixes are active:
```bash
adversarial-iac game \
  -s "Create an S3 bucket for healthcare PHI data" \
  --red-model us.anthropic.claude-3-5-haiku-20241022-v1:0 \
  --blue-model us.anthropic.claude-3-5-haiku-20241022-v1:0 \
  -d hard \
  --red-vuln-source mixed \
  --blue-strategy precise \
  --use-trivy --use-checkov
```
Verify output contains: `scored_manifest.json`, `phantom_manifest.json`,
`precision_stats` in game_result.json, and `phantom_concordance_rate`.

### Quick Reference: Resuming After SSH Disconnect
```bash
# Re-activate the environment after reconnecting
source .venv/bin/activate
source .env
```

---

## Running Experiments Over SSH

Experiments take hours. Use `tmux` or `screen` to survive SSH disconnects:

```bash
# Install tmux if not present
sudo dnf install -y tmux

# Start a named session
tmux new -s experiments

# Inside tmux, activate env and run
source .venv/bin/activate
source .env

# Detach: Ctrl+B then D
# Reattach later: tmux attach -t experiments
```

---

## Execution Schedule

### Phase 1: Core Experiments (Days 1-3)
These produce the primary paper results. Run first.

#### Day 1: E1 Model Stratification (~10 hours, ~$50)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E1_model_comparison_v2.yaml \
  --region us-east-1
```
- 450 games (5 models × 30 scenarios × 3 difficulties × 3 reps)
- Produces Table 2 (model comparison) for §4.1

#### Day 2: E2 Multi-Agent Ablation (~5 hours, ~$20)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E2_multiagent_ablation.yaml \
  --region us-east-1
```
- ~200 games (4 conditions × 8 scenarios × 2 difficulties × 3 reps)
- Produces Table 4 (arms race) for §4.2

#### Day 2 (parallel): E3 Novel vs Database (~5 hours, ~$25)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E3_novel_vs_database_v2.yaml \
  --region us-east-1
```
- 180 games (3 sources × 10 scenarios × 2 difficulties × 3 reps)
- Produces §4.3 (genuine reasoning evidence)

#### Day 3: E4 Difficulty Scaling (~3 hours, ~$12)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E4_difficulty_scaling_v2.yaml \
  --region us-east-1
```
- 90 new games (Llama 3.3 only; Sonnet/Nova Pro/Haiku reused from E1)
- Produces §4.4 (difficulty inversion)

#### Day 3 (parallel): E5 Debate Verification (~4 hours, ~$15)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E5_debate_verification.yaml \
  --region us-east-1
```
- ~120 games (2 conditions × 10 scenarios × 2 difficulties × 3 reps)
- Produces §4.5 (debate weaponization finding)

### Phase 2: Supplementary Conditions (Days 4-6)
These support the precision bottleneck and CoT claims.

#### Day 4: E1-S DeepSeek-R1 (~3 hours, ~$15)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E1S_deepseek_r1.yaml \
  --region us-east-1
```
- 90 games (hard only, 30 scenarios × 3 reps)
- Key result: Does R1 still escape precision bottleneck with v2.3 fixes?

#### Day 4 (parallel): E1-S-Q Qwen3-Coder (~3 hours, ~$12)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E1S_qwen3_coder.yaml \
  --region us-east-1
```
- 90 games (hard only)
- Confirms code specialization ≠ reasoning advantage

#### Day 5: E1-S2 Qwen3.5 Thinking ON (~5 hours, ~$20)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E1S2_qwen35_thinking.yaml \
  --region us-east-1
```
- 90 games (hard only, DashScope backend)
- CoT ON condition for within-model comparison

#### Day 5 (parallel): E1-S3 Qwen3.5 Thinking OFF (~3 hours, ~$12)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E1S3_qwen35_no_thinking.yaml \
  --region us-east-1
```
- 90 games (hard only, DashScope backend)
- CoT OFF control — cleanest isolation of reasoning mechanism

#### Day 6: E1-S4 Qwen3-32B Thinking ON (~4 hours, ~$18)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E1S4_qwen3_32b_thinking.yaml \
  --region us-east-1
```
- 90 games (hard only, Bedrock)
- Bedrock-native CoT replication

#### Day 6 (parallel): E1-S5 Qwen3-32B Thinking OFF (~3 hours, ~$12)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E1S5_qwen3_32b_no_thinking.yaml \
  --region us-east-1
```
- 90 games (hard only, Bedrock)
- Bedrock-native CoT control

### Phase 3: Extended Supplementary (Days 7-8)
Additional reasoning architecture evidence.

#### Day 7: E1-S6 Kimi K2 Thinking (~4 hours, ~$15)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E1S6_kimi_k2_thinking.yaml \
  --region us-east-1
```
- 90 games (hard only)
- Third independent reasoning architecture (Moonshot AI)

#### Day 7 (parallel): E1-S6b OpenAI GPT-OSS-120B (~4 hours, ~$18)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E1S6b_openai_gpt_oss_120b.yaml \
  --region us-east-1
```
- 90 games (hard only)
- Fourth independent reasoning architecture (OpenAI)

#### Day 7 (parallel): E1-S7 DeepSeek V3 (~3 hours, ~$12)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E1S7_deepseek_v3.yaml \
  --region us-east-1
```
- 90 games (hard only)
- Same-family non-reasoning control for DeepSeek-R1

#### Day 8: E2-F Frontier Arms Race (~10 hours, ~$70)
```bash
python scripts/run_experiment.py \
  --config experiments/config/E2F_frontier_arms_race.yaml \
  --region us-east-1
```
- ~192 games (4 conditions × 8 scenarios × 2 difficulties × 3 reps)
- Frontier-tier replication of E2 asymmetry finding

---

## Summary

| Phase | Days | Experiments | Total Games | Est. Cost | Paper Sections |
|-------|------|-------------|-------------|-----------|----------------|
| 1: Core | 1-3 | E1, E2, E3, E4, E5 | ~1,040 | ~$120 | §4.1-§4.5 |
| 2: Supplementary | 4-6 | E1-S, E1-S-Q, E1-S2–S5 | 540 | ~$90 | Table 3 (§4.1) |
| 3: Extended | 7-8 | E1-S6, S6b, S7, E2-F | ~462 | ~$115 | §4.1, §4.2 |
| **Total** | **8 days** | **15 experiments** | **~2,042 games** | **~$325** | Full paper |

## Post-Execution Checklist

### 1. Validate Results
```bash
# Ensure venv is active
source .venv/bin/activate

# Check all experiments completed
for dir in experiments/results/*/; do
  echo "$dir: $(cat $dir/progress.json | python -c 'import json,sys; d=json.load(sys.stdin); print(f"{d.get(\"completed\",0)}/{d.get(\"total\",0)}")')"
done
```

### 2. Verify v2.3 Metrics Present
Confirm each summary.json contains:
- `phantom_concordance_rate` (should be ≤ 0.05)
- `manifest_accuracy` (should be ≥ 0.90)
- `precision_stats` with pass1/pass2 counts

### 3. Generate Paper Tables
```bash
python scripts/analyze_experiments.py \
  --results-dir experiments/results/ \
  --latex-file tables.tex \
  --include-phantom-concordance \
  --include-precision-stats
```

### 4. Compare with Previous Results
Key comparisons to report in paper:
- v2.0 precision vs v2.3 precision (expect ≥5 pp improvement)
- v2.0 phantom concordance rate vs v2.3 (expect >10× reduction)
- v2.0 evasion in full_multiagent vs v2.3 (expect significant reduction)

### 5. Tag Release
```bash
git add -A
git commit -m "v2.3: Rerun all experiments with methodology fixes"
git tag v2.3-rerun
git push origin main --tags
```
