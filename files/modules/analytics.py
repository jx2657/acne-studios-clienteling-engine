"""
analytics.py
Performance simulation, A/B testing, historical trend analysis,
and AI-powered performance summaries.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from statsmodels.stats.proportion import proportions_ztest
from openai import OpenAI, OpenAIError

PERF_LOG = Path("logs/performance_log.json")
PERF_LOG.parent.mkdir(parents=True, exist_ok=True)


# ── Simulated performance data ────────────────────────────────────────────────

PERSONA_BASE_RATES = {
    "VIP":     {"open": 0.65, "ctr": 0.21, "unsub": 0.005},
    "REGULAR": {"open": 0.40, "ctr": 0.11, "unsub": 0.012},
    "AT_RISK": {"open": 0.18, "ctr": 0.04, "unsub": 0.030},
}


def simulate_campaign_performance(product: str, campaign_id: str) -> dict:
    """
    Simulate realistic per-persona engagement metrics with small random noise.
    In production these would be fetched from HubSpot Reporting or SendGrid webhooks.
    """
    rng = np.random.default_rng()
    results: dict[str, dict] = {}
    for persona, base in PERSONA_BASE_RATES.items():
        noise = rng.uniform(-0.03, 0.03)
        results[persona] = {
            "open_rate":   round(np.clip(base["open"] + noise, 0, 1), 4),
            "click_rate":  round(np.clip(base["ctr"]  + noise, 0, 1), 4),
            "unsub_rate":  round(np.clip(base["unsub"] + noise / 10, 0, 1), 4),
            "sent":        int(rng.integers(800, 1200)),
        }

    record = {
        "campaign_id": campaign_id,
        "product":     product,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "personas":    results,
    }
    _append_perf_log(record)
    return record


# ── A/B Testing ───────────────────────────────────────────────────────────────

def run_ab_test(n: int = 1000) -> dict:
    """
    Simulate a two-proportion z-test comparing two newsletter copy variants.
    Version A: control (craftsmanship focus)
    Version B: AI-optimised (emotional storytelling)
    """
    rng = np.random.default_rng()
    a_conversions = rng.binomial(1, 0.12, n)
    b_conversions = rng.binomial(1, 0.18, n)

    z_stat, p_value = proportions_ztest(
        [a_conversions.sum(), b_conversions.sum()],
        [n, n],
    )
    lift = (b_conversions.mean() - a_conversions.mean()) / max(a_conversions.mean(), 1e-9)

    return {
        "A":      round(float(a_conversions.mean()), 4),
        "B":      round(float(b_conversions.mean()), 4),
        "lift":   round(float(lift), 4),
        "z_stat": round(float(z_stat), 4),
        "p":      round(float(p_value), 6),
        "n":      n,
        "significant": bool(p_value < 0.05),
    }


# ── AI Performance Summary ────────────────────────────────────────────────────

def generate_performance_summary(
    product: str,
    perf: dict,
    ab: dict,
    client: OpenAI | None,
) -> str:
    """
    Ask GPT-4o to interpret the performance data and recommend next steps.
    Falls back to a rule-based summary if the client is unavailable.
    """
    if client is None:
        return _fallback_summary(perf, ab)

    perf_text = "\n".join(
        f"- {persona}: open {m['open_rate']:.0%}, CTR {m['click_rate']:.0%}, unsub {m['unsub_rate']:.1%}"
        for persona, m in perf["personas"].items()
    )
    ab_text = (
        f"A/B test: Version A CTR {ab['A']:.1%}, Version B CTR {ab['B']:.1%}, "
        f"lift {ab['lift']:+.1%}, p={ab['p']:.4f} ({'significant' if ab['significant'] else 'not significant'})."
    )
    prompt = (
        f"You are a growth analyst for Acne Studios. Interpret these campaign results for '{product}':\n\n"
        f"{perf_text}\n{ab_text}\n\n"
        "In 3 concise bullet points:\n"
        "• Which segment performed best and why?\n"
        "• What does the A/B result suggest for future copy?\n"
        "• One concrete recommendation for the next campaign."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=300,
        )
        return resp.choices[0].message.content
    except OpenAIError as e:
        return _fallback_summary(perf, ab) + f"\n\n_(AI summary unavailable: {e})_"


def _fallback_summary(perf: dict, ab: dict) -> str:
    best = max(perf["personas"], key=lambda p: perf["personas"][p]["click_rate"])
    ab_verdict = "Version B outperformed — adopt emotional storytelling." if ab["significant"] else \
                 "A/B result inconclusive — continue testing."
    return (
        f"• **{best}** had the highest CTR ({perf['personas'][best]['click_rate']:.0%}). "
        "Prioritise this segment.\n"
        f"• {ab_verdict}\n"
        "• Consider increasing send frequency for VIP contacts with exclusive previews."
    )


# ── Historical trend ──────────────────────────────────────────────────────────

def load_performance_history() -> pd.DataFrame:
    """Load all historical performance records into a flat DataFrame."""
    raw = _read_perf_log()
    rows = []
    for record in raw:
        for persona, m in record.get("personas", {}).items():
            rows.append({
                "campaign_id": record["campaign_id"],
                "product":     record["product"],
                "recorded_at": record["recorded_at"][:10],  # date only
                "persona":     persona,
                **m,
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


# ── Persistence helpers ───────────────────────────────────────────────────────

def _read_perf_log() -> list[dict]:
    if PERF_LOG.exists():
        try:
            return json.loads(PERF_LOG.read_text())
        except json.JSONDecodeError:
            return []
    return []


def _append_perf_log(record: dict) -> None:
    entries = _read_perf_log()
    entries.append(record)
    PERF_LOG.write_text(json.dumps(entries, ensure_ascii=False, indent=2))
