#!/usr/bin/env python3
"""
E3 Adjusted Analysis — Computes metrics on tool-confirmed vulnerabilities only.

Four outputs for the paper:
1. Adjusted recall per condition (confirmed vulns only in numerator AND denominator)
2. Phantom concordance rate (Blue "detections" of non-existent vulns)
3. Within-game database vs novel recall gap for mixed condition (confirmed only)
4. Summary statistics for methodology section

Usage:
    python3 scripts/e3_adjusted_analysis.py

    Reads from:
      - experiments/results/exp3_novel_v2/progress.json (game list)
      - output/games/G-*/manifest_validation.json (per-game validation)
      - output/games/G-*/scoring.json (per-game match results)
      - output/games/G-*/red_manifest.json (per-game manifest with is_novel flags)
"""

import json
import math
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


# ============================================================================
# Statistical helpers (no scipy needed)
# ============================================================================

def mean(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0

def std(vals: List[float]) -> float:
    if len(vals) < 2: return 0.0
    m = mean(vals)
    return math.sqrt(sum((x - m)**2 for x in vals) / (len(vals) - 1))

def ci95(vals: List[float]) -> float:
    if len(vals) < 2: return 0.0
    return 1.96 * std(vals) / math.sqrt(len(vals))

def t_test(g1: List[float], g2: List[float]) -> Tuple[float, float]:
    """Welch's t-test. Returns (t_stat, p_value_approx)."""
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2: return 0.0, 1.0
    m1, m2 = mean(g1), mean(g2)
    s1, s2 = std(g1), std(g2)
    se = math.sqrt(s1**2/n1 + s2**2/n2)
    if se == 0: return 0.0, 1.0
    t = (m1 - m2) / se
    z = abs(t)
    # Normal CDF approximation (Abramowitz & Stegun)
    a1,a2,a3,a4,a5 = 0.254829592,-0.284496736,1.421413741,-1.453152027,1.061405429
    p_const = 0.3275911
    x = z / math.sqrt(2)
    t_val = 1.0 / (1.0 + p_const * x)
    y = 1.0 - (((((a5*t_val+a4)*t_val)+a3)*t_val+a2)*t_val+a1)*t_val*math.exp(-x*x)
    p_value = 2 * (1 - 0.5*(1.0 + y))
    return t, p_value

def cohens_d(g1: List[float], g2: List[float]) -> float:
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2: return 0.0
    s1, s2 = std(g1), std(g2)
    pooled = math.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
    if pooled == 0: return 0.0
    return (mean(g1) - mean(g2)) / pooled


# ============================================================================
# Data loading
# ============================================================================

def load_e3_games(exp_dir: str = "experiments/results/exp3_novel_v2",
                  games_dir: str = "output/games") -> List[Dict]:
    """Load all E3v2 game data with manifest validation and scoring."""
    exp_path = Path(exp_dir)
    games_path = Path(games_dir)
    
    progress_file = exp_path / "progress.json"
    if not progress_file.exists():
        print(f"Error: {progress_file} not found")
        sys.exit(1)
    
    progress = json.loads(progress_file.read_text())
    games = []
    
    for game_entry in progress.get("results", []):
        if game_entry.get("status") != "completed":
            continue
        
        game_dir = games_path / game_entry["output_dir"]
        
        # Load manifest validation
        mv_file = game_dir / "manifest_validation.json"
        if not mv_file.exists():
            continue
        mv = json.loads(mv_file.read_text())
        
        # Load scoring
        scoring_file = game_dir / "scoring.json"
        if not scoring_file.exists():
            continue
        scoring = json.loads(scoring_file.read_text())
        
        # Load red manifest (for is_novel flags in mixed condition)
        manifest_file = game_dir / "red_manifest.json"
        manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else []
        
        # Extract condition
        config = game_entry.get("config", {})
        condition = config.get("red_vuln_source", config.get("condition", "unknown"))
        
        games.append({
            "game_id": game_entry["output_dir"],
            "condition": condition,
            "difficulty": config.get("difficulty", "unknown"),
            "manifest_validation": mv,
            "scoring": scoring,
            "manifest": manifest,
            "config": config,
        })
    
    return games


# ============================================================================
# Analysis 1: Adjusted Recall per Condition
# ============================================================================

def compute_adjusted_recall(games: List[Dict]) -> Dict:
    """
    Compute recall using only tool-confirmed vulnerabilities.
    
    Adjusted Recall = (confirmed vulns that were detected) / (total confirmed vulns)
    
    This excludes phantom vulnerabilities from both numerator and denominator,
    giving the true detection rate on vulnerabilities that actually exist in code.
    """
    results = defaultdict(lambda: {
        "raw_recall": [],
        "adjusted_recall": [],
        "confirmed_detected": 0,
        "confirmed_total": 0,
        "phantom_detected": 0,
        "phantom_total": 0,
        "games": 0,
    })
    
    for game in games:
        cond = game["condition"]
        mv = game["manifest_validation"]
        scoring = game["scoring"]
        
        confirmed_ids = set(mv.get("confirmed_vuln_ids", []))
        unconfirmed_ids = set(mv.get("unconfirmed_vuln_ids", []))
        
        # Get detected vuln IDs from scoring matches
        detected_ids = set()
        for match in scoring.get("matches", []):
            if match.get("match_type") in ["exact", "partial", "corroborated"]:
                detected_ids.add(match.get("red_vuln_id"))
        
        # Confirmed vulns: how many were detected?
        confirmed_detected = len(confirmed_ids & detected_ids)
        confirmed_missed = len(confirmed_ids - detected_ids)
        confirmed_total = len(confirmed_ids)
        
        # Phantom vulns: how many were "detected"? (concordance)
        phantom_detected = len(unconfirmed_ids & detected_ids)
        phantom_total = len(unconfirmed_ids)
        
        # Raw recall (against all claimed vulns)
        total_claimed = confirmed_total + phantom_total
        total_detected = len(detected_ids)
        raw_recall = total_detected / total_claimed if total_claimed > 0 else 0.0
        
        # Adjusted recall (against confirmed vulns only)
        adj_recall = confirmed_detected / confirmed_total if confirmed_total > 0 else 0.0
        
        r = results[cond]
        r["raw_recall"].append(raw_recall)
        if confirmed_total > 0:  # Only include games where at least 1 vuln was confirmed
            r["adjusted_recall"].append(adj_recall)
        r["confirmed_detected"] += confirmed_detected
        r["confirmed_total"] += confirmed_total
        r["phantom_detected"] += phantom_detected
        r["phantom_total"] += phantom_total
        r["games"] += 1
    
    return dict(results)


# ============================================================================
# Analysis 2: Phantom Concordance Rate
# ============================================================================

def compute_phantom_concordance(games: List[Dict]) -> Dict:
    """
    For each condition, compute the phantom concordance rate:
    What fraction of Blue Team "detections" correspond to vulnerabilities
    that static tools cannot find in the code?
    
    Phantom concordance = (phantom vulns "detected") / (total vulns "detected")
    
    A high rate means Blue Team is "finding" things that aren't there —
    both Red and Blue are hallucinating the same vulnerability.
    """
    results = defaultdict(lambda: {
        "concordance_rates": [],
        "total_detections": 0,
        "phantom_detections": 0,
        "real_detections": 0,
    })
    
    for game in games:
        cond = game["condition"]
        mv = game["manifest_validation"]
        scoring = game["scoring"]
        
        confirmed_ids = set(mv.get("confirmed_vuln_ids", []))
        unconfirmed_ids = set(mv.get("unconfirmed_vuln_ids", []))
        
        detected_ids = set()
        for match in scoring.get("matches", []):
            if match.get("match_type") in ["exact", "partial", "corroborated"]:
                detected_ids.add(match.get("red_vuln_id"))
        
        real_detections = len(confirmed_ids & detected_ids)
        phantom_detections = len(unconfirmed_ids & detected_ids)
        total_detections = real_detections + phantom_detections
        
        concordance = phantom_detections / total_detections if total_detections > 0 else 0.0
        
        r = results[cond]
        r["concordance_rates"].append(concordance)
        r["total_detections"] += total_detections
        r["phantom_detections"] += phantom_detections
        r["real_detections"] += real_detections
    
    return dict(results)


# ============================================================================
# Analysis 3: Mixed Condition Within-Game Analysis
# ============================================================================

def compute_mixed_within_game(games: List[Dict]) -> Dict:
    """
    For the mixed condition, analyze per-vulnerability detection rates
    split by source (is_novel flag) using only confirmed vulnerabilities.
    
    This controls for scenario/difficulty variance because database and
    novel vulns coexist within the same game.
    """
    mixed_games = [g for g in games if g["condition"] == "mixed"]
    
    db_confirmed_detected = 0
    db_confirmed_total = 0
    novel_confirmed_detected = 0
    novel_confirmed_total = 0
    
    per_game_db_recall = []
    per_game_novel_recall = []
    
    games_with_labels = 0
    
    for game in mixed_games:
        mv = game["manifest_validation"]
        scoring = game["scoring"]
        manifest = game["manifest"]
        
        confirmed_ids = set(mv.get("confirmed_vuln_ids", []))
        
        # Get detected vuln IDs
        detected_ids = set()
        for match in scoring.get("matches", []):
            if match.get("match_type") in ["exact", "partial", "corroborated"]:
                detected_ids.add(match.get("red_vuln_id"))
        
        # Build vuln_id → is_novel mapping from manifest
        vuln_source = {}
        for v in manifest:
            vid = v.get("vuln_id", "")
            is_novel = v.get("is_novel", False)
            rule_source = v.get("rule_source", "database")
            vuln_source[vid] = is_novel or rule_source == "novel"
        
        if not vuln_source:
            continue
        
        # Split confirmed vulns by source
        game_db_confirmed = 0
        game_db_detected = 0
        game_novel_confirmed = 0
        game_novel_detected = 0
        
        has_labels = False
        for vid in confirmed_ids:
            is_novel = vuln_source.get(vid, None)
            if is_novel is None:
                continue
            has_labels = True
            if is_novel:
                game_novel_confirmed += 1
                if vid in detected_ids:
                    game_novel_detected += 1
            else:
                game_db_confirmed += 1
                if vid in detected_ids:
                    game_db_detected += 1
        
        if has_labels:
            games_with_labels += 1
        
        db_confirmed_detected += game_db_detected
        db_confirmed_total += game_db_confirmed
        novel_confirmed_detected += game_novel_detected
        novel_confirmed_total += game_novel_confirmed
        
        if game_db_confirmed > 0:
            per_game_db_recall.append(game_db_detected / game_db_confirmed)
        if game_novel_confirmed > 0:
            per_game_novel_recall.append(game_novel_detected / game_novel_confirmed)
    
    return {
        "games_analyzed": len(mixed_games),
        "games_with_source_labels": games_with_labels,
        "database": {
            "confirmed_detected": db_confirmed_detected,
            "confirmed_total": db_confirmed_total,
            "aggregate_recall": db_confirmed_detected / db_confirmed_total if db_confirmed_total > 0 else None,
            "per_game_recall": per_game_db_recall,
        },
        "novel": {
            "confirmed_detected": novel_confirmed_detected,
            "confirmed_total": novel_confirmed_total,
            "aggregate_recall": novel_confirmed_detected / novel_confirmed_total if novel_confirmed_total > 0 else None,
            "per_game_novel_recall": per_game_novel_recall,
        },
    }


# ============================================================================
# Report
# ============================================================================

def print_header(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def main():
    print_header("E3 ADJUSTED ANALYSIS — Tool-Confirmed Ground Truth")
    
    # Load data
    games = load_e3_games()
    print(f"\n  Loaded {len(games)} completed games")
    by_cond = defaultdict(int)
    for g in games:
        by_cond[g["condition"]] += 1
    for c, n in sorted(by_cond.items()):
        print(f"    {c}: {n} games")
    
    # ── Analysis 1: Adjusted Recall ────────────────────────────────────────
    print_header("1. ADJUSTED RECALL (Tool-Confirmed Vulnerabilities Only)")
    
    adj = compute_adjusted_recall(games)
    
    print(f"\n  {'Condition':<12} {'Raw Recall':>12} {'Adj Recall':>12} {'Manifest Acc':>13} "
          f"{'Confirmed':>10} {'Phantom':>10} {'n':>5} {'n_adj':>6}")
    print(f"  {'-'*80}")
    
    for cond in ["database", "novel", "mixed"]:
        if cond not in adj:
            continue
        r = adj[cond]
        raw_r = mean(r["raw_recall"])
        adj_r = mean(r["adjusted_recall"]) if r["adjusted_recall"] else 0
        ct = r["confirmed_total"]
        pt = r["phantom_total"]
        ma = ct / (ct + pt) if (ct + pt) > 0 else 0
        print(f"  {cond:<12} {raw_r:>11.1%} {adj_r:>11.1%} {ma:>12.1%} "
              f"{ct:>10} {pt:>10} {r['games']:>5} {len(r['adjusted_recall']):>6}")
    
    # Statistical test on adjusted recall: database vs novel
    if "database" in adj and "novel" in adj:
        db_adj = adj["database"]["adjusted_recall"]
        nv_adj = adj["novel"]["adjusted_recall"]
        
        if db_adj and nv_adj:
            print(f"\n  --- Statistical Test: Adjusted Recall (Database vs Novel) ---")
            print(f"  Database: {mean(db_adj):.1%} ± {ci95(db_adj):.1%} (n={len(db_adj)})")
            print(f"  Novel:    {mean(nv_adj):.1%} ± {ci95(nv_adj):.1%} (n={len(nv_adj)})")
            print(f"  Δ = {mean(db_adj) - mean(nv_adj):.1%}")
            t, p = t_test(db_adj, nv_adj)
            d = cohens_d(db_adj, nv_adj)
            stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            print(f"  t = {t:.3f}, p = {p:.4f} {stars}")
            print(f"  Cohen's d = {d:.3f}")
    
    # ── Analysis 2: Phantom Concordance ────────────────────────────────────
    print_header("2. PHANTOM CONCORDANCE RATE")
    print("  (Fraction of Blue Team 'detections' that match non-existent vulns)")
    
    phantom = compute_phantom_concordance(games)
    
    print(f"\n  {'Condition':<12} {'Concordance':>12} {'Phantom Det':>12} {'Real Det':>10} {'Total Det':>10}")
    print(f"  {'-'*60}")
    
    for cond in ["database", "novel", "mixed"]:
        if cond not in phantom:
            continue
        r = phantom[cond]
        cr = mean(r["concordance_rates"])
        print(f"  {cond:<12} {cr:>11.1%} {r['phantom_detections']:>12} "
              f"{r['real_detections']:>10} {r['total_detections']:>10}")
    
    # Highlight novel condition
    if "novel" in phantom:
        nv = phantom["novel"]
        cr = mean(nv["concordance_rates"])
        print(f"\n  ⚠️  Novel condition phantom concordance: {cr:.1%}")
        print(f"     {nv['phantom_detections']} of {nv['total_detections']} Blue Team detections")
        print(f"     matched vulnerabilities that static tools could not confirm.")
        print(f"     These are likely simultaneous Red/Blue hallucinations.")
    
    # ── Analysis 3: Mixed Within-Game ──────────────────────────────────────
    print_header("3. MIXED CONDITION: WITHIN-GAME DATABASE vs NOVEL (Confirmed Only)")
    
    mixed = compute_mixed_within_game(games)
    
    print(f"\n  Games analyzed: {mixed['games_analyzed']}")
    print(f"  Games with source labels: {mixed['games_with_source_labels']}")
    
    db = mixed["database"]
    nv = mixed["novel"]
    
    print(f"\n  {'Source':<12} {'Adj Recall':>12} {'Confirmed':>10} {'Detected':>10}")
    print(f"  {'-'*48}")
    
    if db["aggregate_recall"] is not None:
        print(f"  {'database':<12} {db['aggregate_recall']:>11.1%} {db['confirmed_total']:>10} {db['confirmed_detected']:>10}")
    else:
        print(f"  {'database':<12} {'N/A':>12} {db['confirmed_total']:>10} {db['confirmed_detected']:>10}")
    
    if nv["aggregate_recall"] is not None:
        print(f"  {'novel':<12} {nv['aggregate_recall']:>11.1%} {nv['confirmed_total']:>10} {nv['confirmed_detected']:>10}")
    else:
        print(f"  {'novel':<12} {'N/A':>12} {nv['confirmed_total']:>10} {nv['confirmed_detected']:>10}")
    
    # Per-game t-test if we have enough data
    if db["per_game_recall"] and nv["per_game_novel_recall"]:
        db_r = db["per_game_recall"]
        nv_r = nv["per_game_novel_recall"]
        if len(db_r) >= 5 and len(nv_r) >= 5:
            print(f"\n  --- Within-Game Statistical Test ---")
            print(f"  Database recall: {mean(db_r):.1%} ± {ci95(db_r):.1%} (n={len(db_r)} games)")
            print(f"  Novel recall:    {mean(nv_r):.1%} ± {ci95(nv_r):.1%} (n={len(nv_r)} games)")
            t, p = t_test(db_r, nv_r)
            d = cohens_d(db_r, nv_r)
            stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            print(f"  t = {t:.3f}, p = {p:.4f} {stars}, d = {d:.3f}")
    else:
        if not db["per_game_recall"]:
            print(f"\n  Note: No database-sourced confirmed vulns with per-game labels in mixed games.")
        if not nv["per_game_novel_recall"]:
            print(f"\n  Note: No novel-sourced confirmed vulns with per-game labels in mixed games.")
        print(f"  Within-game comparison requires is_novel/rule_source labels in red_manifest.json.")
    
    # ── Summary for Paper ──────────────────────────────────────────────────
    print_header("4. PAPER FINDINGS SUMMARY")
    
    print("""
  Finding 1: ATTACKER HALLUCINATION ASYMMETRY
    Database manifest accuracy: {db_ma:.1%}
    Novel manifest accuracy:    {nv_ma:.1%}
    → LLMs reliably inject known patterns but hallucinate {nv_hr:.0%}
      of novel vulnerabilities.

  Finding 2: ADJUSTED RECALL ON CONFIRMED VULNERABILITIES
    Database adjusted recall: {db_ar}
    Novel adjusted recall:    {nv_ar}
    → When measured against tool-confirmed ground truth only,
      detection rates {comparison}.

  Finding 3: PHANTOM CONCORDANCE (Measurement Validity)
    Novel phantom concordance: {nv_pc}
    → {nv_pc_n} of Blue Team detections in the novel condition
      matched non-existent vulnerabilities. Both Red and Blue
      hallucinate the same vulnerability patterns.

  Finding 4: METHODOLOGICAL CONTRIBUTION
    → Manifest validation via static tools is load-bearing for
      any recall claim in adversarial LLM evaluation. Without it,
      recall is measured against partially hallucinated ground truth.
      This affects every adversarial benchmark that relies on
      LLM-generated ground truth without tool corroboration.
""".format(
        db_ma=adj["database"]["confirmed_total"] / (adj["database"]["confirmed_total"] + adj["database"]["phantom_total"]) 
            if "database" in adj and (adj["database"]["confirmed_total"] + adj["database"]["phantom_total"]) > 0 else 0,
        nv_ma=adj["novel"]["confirmed_total"] / (adj["novel"]["confirmed_total"] + adj["novel"]["phantom_total"])
            if "novel" in adj and (adj["novel"]["confirmed_total"] + adj["novel"]["phantom_total"]) > 0 else 0,
        nv_hr=adj["novel"]["phantom_total"] / (adj["novel"]["confirmed_total"] + adj["novel"]["phantom_total"])
            if "novel" in adj and (adj["novel"]["confirmed_total"] + adj["novel"]["phantom_total"]) > 0 else 0,
        db_ar=f"{mean(adj['database']['adjusted_recall']):.1%} ± {ci95(adj['database']['adjusted_recall']):.1%}" 
            if "database" in adj and adj["database"]["adjusted_recall"] else "N/A",
        nv_ar=f"{mean(adj['novel']['adjusted_recall']):.1%} ± {ci95(adj['novel']['adjusted_recall']):.1%}"
            if "novel" in adj and adj["novel"]["adjusted_recall"] else "N/A",
        comparison="are statistically indistinguishable" 
            if ("database" in adj and "novel" in adj and adj["database"]["adjusted_recall"] and adj["novel"]["adjusted_recall"]
                and t_test(adj["database"]["adjusted_recall"], adj["novel"]["adjusted_recall"])[1] > 0.05)
            else "differ significantly",
        nv_pc=f"{mean(phantom['novel']['concordance_rates']):.1%}" if "novel" in phantom else "N/A",
        nv_pc_n=f"{phantom['novel']['phantom_detections']}/{phantom['novel']['total_detections']}" if "novel" in phantom else "N/A",
    ))


if __name__ == "__main__":
    main()
