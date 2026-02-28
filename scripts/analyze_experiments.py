#!/usr/bin/env python3
"""
Statistical Analysis for Adversarial IaC Experiments

Generates publication-ready statistics from experiment CSV files:
- Descriptive statistics with confidence intervals
- T-tests (E3: novel vs database)
- ANOVA (E1: model comparison, E4: difficulty scaling)
- Effect sizes (Cohen's d)
- Per-vulnerability type analysis
- LaTeX table export

Usage:
    python scripts/analyze_experiments.py experiments/results/exp-20260227_051952
    python scripts/analyze_experiments.py experiments/results/exp-* --compare
    python scripts/analyze_experiments.py experiments/results/exp-20260227_051952 --latex
"""

import argparse
import csv
import json
import sys
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import math

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Statistical Functions (no scipy dependency required)
# ============================================================================

def mean(values: List[float]) -> float:
    """Calculate mean."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def std(values: List[float], ddof: int = 1) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - ddof)
    return math.sqrt(variance)


def sem(values: List[float]) -> float:
    """Calculate standard error of mean."""
    if len(values) < 2:
        return 0.0
    return std(values) / math.sqrt(len(values))


def ci95(values: List[float]) -> float:
    """Calculate 95% confidence interval half-width."""
    return 1.96 * sem(values)


def cohens_d(group1: List[float], group2: List[float]) -> float:
    """Calculate Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0
    m1, m2 = mean(group1), mean(group2)
    s1, s2 = std(group1), std(group2)
    # Pooled standard deviation
    pooled_std = math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return (m1 - m2) / pooled_std


def t_test_independent(group1: List[float], group2: List[float]) -> Tuple[float, float]:
    """
    Independent samples t-test (Welch's t-test).
    Returns (t_statistic, approximate_p_value).
    """
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0, 1.0
    m1, m2 = mean(group1), mean(group2)
    s1, s2 = std(group1), std(group2)
    
    se = math.sqrt(s1**2 / n1 + s2**2 / n2)
    if se == 0:
        return 0.0, 1.0
    
    t_stat = (m1 - m2) / se
    
    # Welch-Satterthwaite degrees of freedom
    num = (s1**2 / n1 + s2**2 / n2) ** 2
    denom = (s1**2 / n1)**2 / (n1 - 1) + (s2**2 / n2)**2 / (n2 - 1)
    df = num / denom if denom > 0 else 1
    
    # Approximate p-value using normal approximation for large samples
    # (good enough for n > 30, which all our experiments have)
    z = abs(t_stat)
    # Standard normal CDF approximation
    p_value = 2 * (1 - _normal_cdf(z))
    
    return t_stat, p_value


def _normal_cdf(x: float) -> float:
    """Approximate standard normal CDF using Abramowitz and Stegun."""
    # Constants
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    
    sign = 1 if x >= 0 else -1
    x = abs(x) / math.sqrt(2)
    
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
    
    return 0.5 * (1.0 + sign * y)


def f_test_oneway(*groups: List[float]) -> Tuple[float, float, float]:
    """
    One-way ANOVA F-test.
    Returns (F_statistic, approximate_p_value, eta_squared).
    """
    k = len(groups)
    if k < 2:
        return 0.0, 1.0, 0.0
    
    all_values = [v for g in groups for v in g]
    grand_mean = mean(all_values)
    N = len(all_values)
    
    # Between-group sum of squares
    ss_between = sum(len(g) * (mean(g) - grand_mean)**2 for g in groups)
    
    # Within-group sum of squares
    ss_within = sum(sum((v - mean(g))**2 for v in g) for g in groups)
    
    # Degrees of freedom
    df_between = k - 1
    df_within = N - k
    
    if df_within == 0 or ss_within == 0:
        return 0.0, 1.0, 0.0
    
    # F statistic
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    f_stat = ms_between / ms_within
    
    # Eta squared (effect size)
    ss_total = ss_between + ss_within
    eta_sq = ss_between / ss_total if ss_total > 0 else 0.0
    
    # Approximate p-value (using chi-squared approximation for large samples)
    # For large df_within, F * df_between ~ chi-squared(df_between)
    p_value = _chi2_p_value(f_stat * df_between, df_between)
    
    return f_stat, p_value, eta_sq


def _chi2_p_value(x: float, df: int) -> float:
    """Very rough chi-squared p-value approximation."""
    if df <= 0 or x <= 0:
        return 1.0
    # Wilson-Hilferty approximation
    z = ((x / df)**(1/3) - (1 - 2/(9*df))) / math.sqrt(2/(9*df))
    return 1 - _normal_cdf(z)


def effect_size_label(d: float) -> str:
    """Label effect size per Cohen's conventions."""
    d = abs(d)
    if d < 0.2:
        return "negligible"
    elif d < 0.5:
        return "small"
    elif d < 0.8:
        return "medium"
    else:
        return "large"


def p_value_stars(p: float) -> str:
    """Return significance stars."""
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    else:
        return "ns"


# ============================================================================
# Data Loading
# ============================================================================

def load_experiment_csv(exp_dir: Path) -> List[Dict]:
    """Load results.csv from an experiment directory."""
    csv_path = exp_dir / "results.csv"
    if not csv_path.exists():
        print(f"Error: No results.csv in {exp_dir}")
        return []
    
    results = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for key in ['precision', 'recall', 'f1_score', 'evasion_rate']:
                if key in row:
                    try:
                        row[key] = float(row[key])
                    except (ValueError, TypeError):
                        row[key] = 0.0
            
            # Handle adjusted precision if present
            if 'adjusted_precision' in row:
                try:
                    row['adjusted_precision'] = float(row['adjusted_precision'])
                except (ValueError, TypeError):
                    row['adjusted_precision'] = row.get('precision', 0.0)
            
            results.append(row)
    
    return results


def load_experiment_config(exp_dir: Path) -> Dict:
    """Load the experiment config."""
    for name in ["config.json", "experiment_config.json"]:
        path = exp_dir / name
        if path.exists():
            return json.loads(path.read_text())
    return {}


# ============================================================================
# Analysis Functions
# ============================================================================

def descriptive_stats(values: List[float], label: str = "") -> Dict:
    """Compute descriptive statistics."""
    if not values:
        return {"label": label, "n": 0}
    
    return {
        "label": label,
        "n": len(values),
        "mean": mean(values),
        "std": std(values),
        "sem": sem(values),
        "ci95": ci95(values),
        "min": min(values),
        "max": max(values),
        "median": sorted(values)[len(values) // 2],
    }


def analyze_by_group(results: List[Dict], group_key: str, metric: str) -> Dict[str, List[float]]:
    """Group results by a key and extract a metric."""
    groups = defaultdict(list)
    for r in results:
        group = r.get(group_key, "unknown")
        # Clean up quoted strings
        group = group.strip().strip('"')
        val = r.get(metric, 0.0)
        if isinstance(val, str):
            try:
                val = float(val)
            except ValueError:
                continue
        groups[group].append(val)
    return dict(groups)


def print_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_subheader(title: str):
    """Print a formatted subsection header."""
    print(f"\n  --- {title} ---")


# ============================================================================
# Report Generators
# ============================================================================

def report_descriptive(results: List[Dict], exp_name: str = ""):
    """Print descriptive statistics report."""
    print_header(f"DESCRIPTIVE STATISTICS{f' — {exp_name}' if exp_name else ''}")
    print(f"  Total games: {len(results)}")
    
    for metric in ['precision', 'recall', 'f1_score', 'evasion_rate']:
        values = [r[metric] for r in results if metric in r]
        stats = descriptive_stats(values, metric)
        print(f"\n  {metric.replace('_', ' ').title():20s}  "
              f"{stats['mean']:.1%} ± {stats['ci95']:.1%} (95% CI)  "
              f"σ={stats['std']:.1%}  "
              f"[{stats['min']:.1%}, {stats['max']:.1%}]  "
              f"n={stats['n']}")


def report_e3_novel_vs_database(results: List[Dict]):
    """E3-specific analysis: novel vs database vulnerability detection."""
    print_header("E3: NOVEL vs DATABASE VULNERABILITY ANALYSIS")
    
    # Group by vulnerability source (condition field or red_vuln_source)
    source_key = 'condition' if 'condition' in results[0] else 'red_vuln_source'
    
    groups = analyze_by_group(results, source_key, 'recall')
    f1_groups = analyze_by_group(results, source_key, 'f1_score')
    evasion_groups = analyze_by_group(results, source_key, 'evasion_rate')
    precision_groups = analyze_by_group(results, source_key, 'precision')
    
    # Print per-group stats
    print_subheader("Per-Condition Metrics")
    print(f"  {'Condition':<15} {'F1':>10} {'Recall':>10} {'Precision':>10} {'Evasion':>10} {'n':>5}")
    print(f"  {'-'*60}")
    
    for condition in sorted(f1_groups.keys()):
        f1 = f1_groups.get(condition, [])
        rec = groups.get(condition, [])
        prec = precision_groups.get(condition, [])
        ev = evasion_groups.get(condition, [])
        print(f"  {condition:<15} "
              f"{mean(f1):>9.1%} {mean(rec):>9.1%} {mean(prec):>9.1%} {mean(ev):>9.1%} {len(f1):>5}")
    
    # T-test: database vs novel
    if 'database' in groups and 'novel' in groups:
        print_subheader("Statistical Test: Database vs Novel (Recall)")
        db = groups['database']
        novel = groups['novel']
        
        t_stat, p_val = t_test_independent(db, novel)
        d = cohens_d(db, novel)
        
        print(f"  Database recall: {mean(db):.1%} ± {ci95(db):.1%} (n={len(db)})")
        print(f"  Novel recall:    {mean(novel):.1%} ± {ci95(novel):.1%} (n={len(novel)})")
        print(f"  Difference:      {mean(db) - mean(novel):.1%}")
        print(f"  t = {t_stat:.3f}, p = {p_val:.4f} {p_value_stars(p_val)}")
        print(f"  Cohen's d = {d:.3f} ({effect_size_label(d)})")
        
        # Same for F1
        print_subheader("Statistical Test: Database vs Novel (F1)")
        db_f1 = f1_groups['database']
        novel_f1 = f1_groups['novel']
        
        t_stat, p_val = t_test_independent(db_f1, novel_f1)
        d = cohens_d(db_f1, novel_f1)
        
        print(f"  Database F1: {mean(db_f1):.1%} ± {ci95(db_f1):.1%} (n={len(db_f1)})")
        print(f"  Novel F1:    {mean(novel_f1):.1%} ± {ci95(novel_f1):.1%} (n={len(novel_f1)})")
        print(f"  Difference:  {mean(db_f1) - mean(novel_f1):.1%}")
        print(f"  t = {t_stat:.3f}, p = {p_val:.4f} {p_value_stars(p_val)}")
        print(f"  Cohen's d = {d:.3f} ({effect_size_label(d)})")
        
        # Evasion rate comparison
        print_subheader("Statistical Test: Database vs Novel (Evasion Rate)")
        db_ev = evasion_groups['database']
        novel_ev = evasion_groups['novel']
        
        t_stat, p_val = t_test_independent(db_ev, novel_ev)
        d = cohens_d(novel_ev, db_ev)  # Novel - Database (positive = novel harder)
        
        print(f"  Database evasion: {mean(db_ev):.1%} ± {ci95(db_ev):.1%}")
        print(f"  Novel evasion:    {mean(novel_ev):.1%} ± {ci95(novel_ev):.1%}")
        print(f"  Difference:       {mean(novel_ev) - mean(db_ev):.1%}")
        print(f"  t = {t_stat:.3f}, p = {p_val:.4f} {p_value_stars(p_val)}")
        print(f"  Cohen's d = {d:.3f} ({effect_size_label(d)})")


def report_e1_model_comparison(results: List[Dict]):
    """E1-specific analysis: model comparison."""
    print_header("E1: MODEL COMPARISON ANALYSIS")
    
    model_key = 'red_model'
    
    f1_groups = analyze_by_group(results, model_key, 'f1_score')
    recall_groups = analyze_by_group(results, model_key, 'recall')
    precision_groups = analyze_by_group(results, model_key, 'precision')
    evasion_groups = analyze_by_group(results, model_key, 'evasion_rate')
    
    # Print per-model stats
    print_subheader("Per-Model Metrics (mean ± 95% CI)")
    print(f"  {'Model':<25} {'F1':>14} {'Recall':>14} {'Precision':>14} {'Evasion':>14} {'n':>5}")
    print(f"  {'-'*90}")
    
    for model in sorted(f1_groups.keys()):
        f1 = f1_groups[model]
        rec = recall_groups.get(model, [])
        prec = precision_groups.get(model, [])
        ev = evasion_groups.get(model, [])
        print(f"  {model:<25} "
              f"{mean(f1):.1%}±{ci95(f1):.1%} "
              f"{mean(rec):.1%}±{ci95(rec):.1%} "
              f"{mean(prec):.1%}±{ci95(prec):.1%} "
              f"{mean(ev):.1%}±{ci95(ev):.1%} "
              f"{len(f1):>5}")
    
    # ANOVA on F1 scores
    print_subheader("ANOVA: F1 Score across Models")
    groups_list = [f1_groups[m] for m in sorted(f1_groups.keys())]
    f_stat, p_val, eta_sq = f_test_oneway(*groups_list)
    
    print(f"  F({len(groups_list)-1}, {sum(len(g) for g in groups_list)-len(groups_list)}) = {f_stat:.3f}")
    print(f"  p = {p_val:.4f} {p_value_stars(p_val)}")
    print(f"  η² = {eta_sq:.3f} ({effect_size_label(math.sqrt(eta_sq * 2))})")
    
    # Pairwise comparisons
    print_subheader("Pairwise Comparisons (F1 Score)")
    models = sorted(f1_groups.keys())
    for i in range(len(models)):
        for j in range(i+1, len(models)):
            m1, m2 = models[i], models[j]
            t_stat, p_val = t_test_independent(f1_groups[m1], f1_groups[m2])
            d = cohens_d(f1_groups[m1], f1_groups[m2])
            print(f"  {m1} vs {m2}:")
            print(f"    Δ={mean(f1_groups[m1])-mean(f1_groups[m2]):.1%}, "
                  f"t={t_stat:.2f}, p={p_val:.4f}{p_value_stars(p_val)}, "
                  f"d={d:.2f} ({effect_size_label(d)})")


def report_e4_difficulty(results: List[Dict]):
    """E4-specific analysis: difficulty scaling."""
    print_header("E4: DIFFICULTY SCALING ANALYSIS")
    
    f1_groups = analyze_by_group(results, 'difficulty', 'f1_score')
    evasion_groups = analyze_by_group(results, 'difficulty', 'evasion_rate')
    precision_groups = analyze_by_group(results, 'difficulty', 'precision')
    recall_groups = analyze_by_group(results, 'difficulty', 'recall')
    
    # Print per-difficulty stats
    print_subheader("Per-Difficulty Metrics (mean ± 95% CI)")
    print(f"  {'Difficulty':<12} {'F1':>14} {'Recall':>14} {'Precision':>14} {'Evasion':>14} {'n':>5}")
    print(f"  {'-'*75}")
    
    for diff in ['easy', 'medium', 'hard']:
        if diff in f1_groups:
            f1 = f1_groups[diff]
            rec = recall_groups.get(diff, [])
            prec = precision_groups.get(diff, [])
            ev = evasion_groups.get(diff, [])
            print(f"  {diff:<12} "
                  f"{mean(f1):.1%}±{ci95(f1):.1%} "
                  f"{mean(rec):.1%}±{ci95(rec):.1%} "
                  f"{mean(prec):.1%}±{ci95(prec):.1%} "
                  f"{mean(ev):.1%}±{ci95(ev):.1%} "
                  f"{len(f1):>5}")
    
    # ANOVA on F1
    print_subheader("ANOVA: F1 Score across Difficulties")
    groups_list = [f1_groups[d] for d in ['easy', 'medium', 'hard'] if d in f1_groups]
    if len(groups_list) >= 2:
        f_stat, p_val, eta_sq = f_test_oneway(*groups_list)
        print(f"  F({len(groups_list)-1}, {sum(len(g) for g in groups_list)-len(groups_list)}) = {f_stat:.3f}")
        print(f"  p = {p_val:.4f} {p_value_stars(p_val)}")
        print(f"  η² = {eta_sq:.3f}")
    
    # ANOVA on evasion rate
    print_subheader("ANOVA: Evasion Rate across Difficulties")
    ev_groups = [evasion_groups[d] for d in ['easy', 'medium', 'hard'] if d in evasion_groups]
    if len(ev_groups) >= 2:
        f_stat, p_val, eta_sq = f_test_oneway(*ev_groups)
        print(f"  F = {f_stat:.3f}, p = {p_val:.4f} {p_value_stars(p_val)}, η² = {eta_sq:.3f}")
    
    # Pairwise: easy vs hard
    if 'easy' in f1_groups and 'hard' in f1_groups:
        print_subheader("Pairwise: Easy vs Hard (F1)")
        t_stat, p_val = t_test_independent(f1_groups['easy'], f1_groups['hard'])
        d = cohens_d(f1_groups['hard'], f1_groups['easy'])
        print(f"  Easy F1:  {mean(f1_groups['easy']):.1%} ± {ci95(f1_groups['easy']):.1%}")
        print(f"  Hard F1:  {mean(f1_groups['hard']):.1%} ± {ci95(f1_groups['hard']):.1%}")
        print(f"  t = {t_stat:.3f}, p = {p_val:.4f} {p_value_stars(p_val)}")
        print(f"  Cohen's d = {d:.3f} ({effect_size_label(d)})")


def report_e2_multiagent(results: List[Dict]):
    """E2-specific analysis: multi-agent ablation."""
    print_header("E2: MULTI-AGENT ABLATION ANALYSIS")
    
    condition_key = 'condition'
    
    f1_groups = analyze_by_group(results, condition_key, 'f1_score')
    evasion_groups = analyze_by_group(results, condition_key, 'evasion_rate')
    precision_groups = analyze_by_group(results, condition_key, 'precision')
    recall_groups = analyze_by_group(results, condition_key, 'recall')
    
    # Print per-condition stats
    print_subheader("Per-Condition Metrics (mean ± 95% CI)")
    print(f"  {'Condition':<20} {'F1':>14} {'Recall':>14} {'Precision':>14} {'Evasion':>14} {'n':>5}")
    print(f"  {'-'*85}")
    
    for cond in sorted(f1_groups.keys()):
        f1 = f1_groups[cond]
        rec = recall_groups.get(cond, [])
        prec = precision_groups.get(cond, [])
        ev = evasion_groups.get(cond, [])
        print(f"  {cond:<20} "
              f"{mean(f1):.1%}±{ci95(f1):.1%} "
              f"{mean(rec):.1%}±{ci95(rec):.1%} "
              f"{mean(prec):.1%}±{ci95(prec):.1%} "
              f"{mean(ev):.1%}±{ci95(ev):.1%} "
              f"{len(f1):>5}")
    
    # Key comparisons
    if 'baseline' in evasion_groups:
        baseline_ev = evasion_groups['baseline']
        
        for cond in ['red_pipeline', 'blue_ensemble', 'full_multiagent']:
            if cond in evasion_groups:
                print_subheader(f"Baseline vs {cond} (Evasion Rate)")
                cond_ev = evasion_groups[cond]
                t_stat, p_val = t_test_independent(baseline_ev, cond_ev)
                d = cohens_d(cond_ev, baseline_ev)
                print(f"  Baseline: {mean(baseline_ev):.1%} ± {ci95(baseline_ev):.1%}")
                print(f"  {cond}: {mean(cond_ev):.1%} ± {ci95(cond_ev):.1%}")
                print(f"  Δ = {mean(cond_ev) - mean(baseline_ev):+.1%}")
                print(f"  t = {t_stat:.3f}, p = {p_val:.4f} {p_value_stars(p_val)}")
                print(f"  Cohen's d = {d:.3f} ({effect_size_label(d)})")


# ============================================================================
# LaTeX Export
# ============================================================================

def export_latex_table(results: List[Dict], group_key: str, exp_name: str = "") -> str:
    """Generate a LaTeX table from grouped results."""
    f1_groups = analyze_by_group(results, group_key, 'f1_score')
    recall_groups = analyze_by_group(results, group_key, 'recall')
    precision_groups = analyze_by_group(results, group_key, 'precision')
    evasion_groups = analyze_by_group(results, group_key, 'evasion_rate')
    
    lines = []
    lines.append(f"% {exp_name}")
    lines.append(r"\begin{table}[h]")
    lines.append(r"\centering")
    lines.append(f"\\caption{{{exp_name}}}")
    lines.append(r"\begin{tabular}{lccccr}")
    lines.append(r"\toprule")
    lines.append(f"{group_key.replace('_', ' ').title()} & F1 & Recall & Precision & Evasion & n \\\\")
    lines.append(r"\midrule")
    
    for group in sorted(f1_groups.keys()):
        f1 = f1_groups[group]
        rec = recall_groups.get(group, [])
        prec = precision_groups.get(group, [])
        ev = evasion_groups.get(group, [])
        
        line = (f"{group} & "
                f"{mean(f1)*100:.1f}\\% $\\pm$ {ci95(f1)*100:.1f} & "
                f"{mean(rec)*100:.1f}\\% $\\pm$ {ci95(rec)*100:.1f} & "
                f"{mean(prec)*100:.1f}\\% $\\pm$ {ci95(prec)*100:.1f} & "
                f"{mean(ev)*100:.1f}\\% $\\pm$ {ci95(ev)*100:.1f} & "
                f"{len(f1)} \\\\")
        lines.append(line)
    
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    
    return "\n".join(lines)


# ============================================================================
# Per-Vulnerability Type Analysis
# ============================================================================

def analyze_vulnerability_types(exp_dir: Path):
    """Analyze detection rates by vulnerability type from game results."""
    print_header("PER-VULNERABILITY TYPE ANALYSIS")
    
    # Try to load individual game results
    games_dir = exp_dir / "games"
    if not games_dir.exists():
        # Try loading from game_results in the JSON
        progress_file = exp_dir / "progress.json"
        if progress_file.exists():
            progress = json.loads(progress_file.read_text())
            # Check for output dirs
            game_dirs = []
            for game in progress.get("games", []):
                if game.get("status") == "completed":
                    output_dir = game.get("output_dir", "")
                    if output_dir:
                        game_path = Path("output/games") / output_dir
                        if game_path.exists():
                            game_dirs.append(game_path)
            
            if not game_dirs:
                print("  No individual game results found for per-vuln analysis.")
                print("  (This requires output/games/ directory with game results)")
                return
        else:
            print("  No game data found for per-vulnerability analysis.")
            return
    else:
        game_dirs = sorted(games_dir.iterdir())
    
    # Aggregate by vulnerability type
    type_stats = defaultdict(lambda: {"injected": 0, "detected": 0, "evaded": 0})
    
    for game_dir in game_dirs:
        if not game_dir.is_dir():
            continue
        
        try:
            # Load scoring
            scoring_file = game_dir / "scoring.json"
            if not scoring_file.exists():
                continue
            scoring = json.loads(scoring_file.read_text())
            
            # Load manifest
            manifest_file = game_dir / "red_manifest.json"
            if not manifest_file.exists():
                continue
            manifest = json.loads(manifest_file.read_text())
            
            # Get matched vuln IDs
            matches = scoring.get("matches", [])
            detected_ids = set()
            for m in matches:
                if m.get("match_type") in ["exact", "partial", "corroborated"]:
                    detected_ids.add(m.get("red_vuln_id"))
            
            # Count by type
            for vuln in manifest:
                vtype = vuln.get("type", "unknown")
                type_stats[vtype]["injected"] += 1
                if vuln.get("vuln_id") in detected_ids:
                    type_stats[vtype]["detected"] += 1
                else:
                    type_stats[vtype]["evaded"] += 1
                    
        except Exception as e:
            continue
    
    if not type_stats:
        print("  No vulnerability type data available.")
        return
    
    print(f"\n  {'Vuln Type':<20} {'Injected':>10} {'Detected':>10} {'Evaded':>10} {'Det Rate':>10} {'Eva Rate':>10}")
    print(f"  {'-'*70}")
    
    for vtype in sorted(type_stats.keys(), key=lambda t: type_stats[t]["injected"], reverse=True):
        s = type_stats[vtype]
        det_rate = s["detected"] / s["injected"] if s["injected"] > 0 else 0
        eva_rate = s["evaded"] / s["injected"] if s["injected"] > 0 else 0
        print(f"  {vtype:<20} {s['injected']:>10} {s['detected']:>10} {s['evaded']:>10} "
              f"{det_rate:>9.1%} {eva_rate:>9.1%}")


# ============================================================================
# Main
# ============================================================================

def detect_experiment_type(results: List[Dict], config: Dict) -> str:
    """Auto-detect experiment type from data."""
    name = config.get("name", "").lower()
    
    if "novel" in name or "database" in name:
        return "e3"
    elif "model" in name or "comparison" in name:
        return "e1"
    elif "difficulty" in name or "scaling" in name:
        return "e4"
    elif "multi" in name or "ablation" in name:
        return "e2"
    elif "debate" in name:
        return "e5"
    
    # Heuristic: check what varies
    conditions = set(r.get('condition', '') for r in results)
    sources = set(r.get('red_vuln_source', '') for r in results)
    models = set(r.get('red_model', '') for r in results)
    
    if 'novel' in sources or 'novel' in conditions:
        return "e3"
    if len(models) > 2:
        return "e1"
    if 'baseline' in conditions:
        return "e2"
    
    return "generic"


def main():
    parser = argparse.ArgumentParser(description="Analyze Adversarial IaC Experiments")
    parser.add_argument("experiment_dir", help="Path to experiment results directory")
    parser.add_argument("--type", choices=["e1", "e2", "e3", "e4", "e5", "auto"], 
                        default="auto", help="Experiment type (auto-detected if not specified)")
    parser.add_argument("--latex", action="store_true", help="Export LaTeX tables")
    parser.add_argument("--vuln-types", action="store_true", help="Per-vulnerability type analysis")
    parser.add_argument("--output", "-o", help="Save report to file")
    
    args = parser.parse_args()
    
    exp_dir = Path(args.experiment_dir)
    if not exp_dir.exists():
        print(f"Error: {exp_dir} does not exist")
        sys.exit(1)
    
    # Load data
    results = load_experiment_csv(exp_dir)
    if not results:
        print("No results to analyze.")
        sys.exit(1)
    
    config = load_experiment_config(exp_dir)
    
    # Detect experiment type
    exp_type = args.type
    if exp_type == "auto":
        exp_type = detect_experiment_type(results, config)
        print(f"Auto-detected experiment type: {exp_type}")
    
    exp_name = config.get("name", exp_dir.name)
    
    # Redirect output if needed
    original_stdout = sys.stdout
    if args.output:
        sys.stdout = open(args.output, 'w')
    
    # Always print descriptive stats
    report_descriptive(results, exp_name)
    
    # Experiment-specific analysis
    if exp_type == "e3":
        report_e3_novel_vs_database(results)
    elif exp_type == "e1":
        report_e1_model_comparison(results)
    elif exp_type == "e4":
        report_e4_difficulty(results)
    elif exp_type == "e2":
        report_e2_multiagent(results)
    else:
        # Generic: report by difficulty and condition
        report_e4_difficulty(results)
    
    # LaTeX export
    if args.latex:
        print_header("LATEX TABLES")
        
        if exp_type == "e3":
            print(export_latex_table(results, 'condition', f"E3: Novel vs Database ({exp_name})"))
        elif exp_type == "e1":
            print(export_latex_table(results, 'red_model', f"E1: Model Comparison ({exp_name})"))
        elif exp_type == "e4":
            print(export_latex_table(results, 'difficulty', f"E4: Difficulty Scaling ({exp_name})"))
        elif exp_type == "e2":
            print(export_latex_table(results, 'condition', f"E2: Multi-Agent Ablation ({exp_name})"))
    
    # Per-vulnerability type analysis
    if args.vuln_types:
        analyze_vulnerability_types(exp_dir)
    
    # Restore stdout
    if args.output:
        sys.stdout = original_stdout
        print(f"Report saved to: {args.output}")


if __name__ == "__main__":
    main()
