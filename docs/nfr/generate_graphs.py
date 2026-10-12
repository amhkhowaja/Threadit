#!/usr/bin/env python3
"""Generate the NFR/load-test graphs under docs/nfr/.

All values are the REAL measured results recorded in
artifacts/docs/NFR_REPORT.md (Floci harness + in-VPC Lambda DynamoDB probe +
real-AWS search-lag). This script only visualizes them; it does not re-run tests.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs" / "nfr"
OUT.mkdir(parents=True, exist_ok=True)

AWS_ORANGE = "#ec7211"
GREEN = "#2e8b57"
BLUE = "#2f6f9f"
PURPLE = "#6b46c1"
RED = "#d64545"
INK = "#152a3a"
GREY = "#9aa7b4"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": "#c9d4de",
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "figure.dpi": 130,
    }
)


def save(fig, name):
    fig.tight_layout()
    p = OUT / name
    fig.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {p}")


def latency_percentiles():
    """In-region DynamoDB latency percentiles (the representative numbers), all
    taken verbatim from the in-VPC 512MB probe in NFR_REPORT.md."""
    labels = ["p50", "p95", "p99", "min"]
    inregion = [5.1, 13.4, 15.0, 4.5]  # ms, verbatim from report
    slo = 150
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    bars = ax.bar(labels, inregion, 0.55, color=GREEN)
    ax.axhline(slo, color=RED, ls="--", lw=1.5)
    ax.text(3.4, slo - 14, f"read SLO {slo} ms", color=RED, ha="right", fontsize=9.5)
    ax.set_ylabel("latency (ms)")
    ax.set_title("In-region DynamoDB read latency vs SLO (10x margin)")
    for b, v in zip(bars, inregion):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, f"{v:g}", ha="center", fontsize=9, color=INK)
    ax.set_ylim(0, 170)
    save(fig, "latency-percentiles.png")


def latency_journey():
    """The honest 'where did the seconds go' story, log scale."""
    ctx = [
        "Laptop (BUD)\n-> us-east-1",
        "In-VPC Lambda\n128 MB",
        "In-VPC Lambda\n512 MB",
    ]
    p99 = [4400, 40, 15.0]
    colors = [RED, AWS_ORANGE, GREEN]
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    bars = ax.bar(ctx, p99, color=colors, width=0.6)
    ax.axhline(150, color=BLUE, ls="--", lw=1.5)
    ax.text(2.4, 170, "read SLO 150 ms", color=BLUE, ha="right", fontsize=9.5)
    ax.set_yscale("log")
    ax.set_ylabel("p99 latency (ms, log scale)")
    ax.set_title("DynamoDB read latency: resolving the topology artifact")
    notes = ["WAN RTT x calls", "CPU-starved client", "real DynamoDB"]
    for b, v, n in zip(bars, p99, notes):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.15, f"{v:g} ms", ha="center", fontsize=9, color=INK)
        ax.text(b.get_x() + b.get_width() / 2, v * 0.5, n, ha="center", fontsize=8, color="white")
    save(fig, "latency-journey.png")


def search_lag():
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.barh(["measured\n(real AWS)"], [1.89], color=PURPLE, height=0.4)
    ax.axvline(10, color=RED, ls="--", lw=1.5)
    ax.text(10, -0.42, "SLO < 10 s", color=RED, ha="center", fontsize=9.5)
    ax.text(1.89, 0, "  1.89 s", va="center", fontsize=12, color=INK, fontweight="bold")
    ax.set_xlim(0, 11)
    ax.set_ylim(-0.6, 0.6)
    ax.set_xlabel("end-to-end indexing lag (s)")
    ax.set_title("Search freshness: write -> Streams -> Lambda -> OpenSearch", fontsize=11, pad=14)
    save(fig, "search-lag.png")


def throughput_availability():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.6))
    a1.bar(["Floci\n(15 users)"], [311], color=BLUE, width=0.5)
    a1.text(0, 318, "311 RPS", ha="center", fontsize=10, color=INK)
    a1.set_ylabel("requests / sec")
    a1.set_title("Throughput (local)")
    a1.set_ylim(0, 360)
    # availability gauge-ish
    a2.bar(["Floci", "Real AWS"], [100, 100], color=[BLUE, AWS_ORANGE], width=0.5)
    a2.axhline(99.9, color=RED, ls="--", lw=1.3)
    a2.text(1.4, 99.9, "SLO 99.9%", color=RED, ha="right", va="bottom", fontsize=9)
    a2.set_ylim(99.0, 100.1)
    a2.set_ylabel("non-5xx availability (%)")
    a2.set_title("Availability under load")
    for i in range(2):
        a2.text(i, 100.02, "100%", ha="center", fontsize=9.5, color=INK)
    save(fig, "throughput-availability.png")


def coverage_matrix():
    """A visual checklist of NFRs covered."""
    rows = [
        ("Latency (p50/p95/p99)", "measured", GREEN),
        ("Throughput (RPS)", "measured", GREEN),
        ("Availability (non-5xx)", "100% both backends", GREEN),
        ("Eventual consistency (RYOW)", "pass (ConsistentRead)", GREEN),
        ("Search freshness lag", "1.89 s (real AWS)", GREEN),
        ("Rate limiting (429)", "enforced + Retry-After", GREEN),
        ("Caching (hot-post burst)", "herd guard, 0 server err", GREEN),
        ("Partition tolerance (DLQ)", "proven on failure", GREEN),
        ("In-VPC SLO sign-off (Fargate)", "deferred to staging", GREY),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.axis("off")
    ax.set_title("NFR coverage", loc="left")
    y = len(rows)
    for name, status, color in rows:
        y -= 1
        mark = "\u2713" if color == GREEN else "\u2192"
        ax.add_patch(plt.Rectangle((0.02, y + 0.12), 0.96, 0.76, color="#f4f7fa", ec="#dbe3ea"))
        ax.text(0.06, y + 0.5, mark, color=color, fontsize=14, va="center", fontweight="bold")
        ax.text(0.12, y + 0.5, name, color=INK, fontsize=11, va="center")
        ax.text(0.97, y + 0.5, status, color=color if color != GREY else "#6b7885",
                fontsize=10, va="center", ha="right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(rows))
    save(fig, "coverage.png")


def main():
    latency_percentiles()
    latency_journey()
    search_lag()
    throughput_availability()
    coverage_matrix()


if __name__ == "__main__":
    main()
