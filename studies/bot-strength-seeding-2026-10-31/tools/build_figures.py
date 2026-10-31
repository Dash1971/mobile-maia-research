#!/usr/bin/env python3
"""Rebuild figures from published evidence; no inference, model fitting, or network.

Install ../requirements-figures.txt, then run this script. Paths default to the
containing study. figure-metrics.json records numeric summaries and input hashes.
The configuration bootstrap matches verify_public.py; it does not propagate
uncertainty in the final native ratings or the external rating-scale anchor.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

BLUE, ORANGE, GRAY = "#0072B2", "#D55E00", "#666666"
SPEEDS = ("blitz", "rapid")
COLORS = dict(zip(SPEEDS, (BLUE, ORANGE)))
MARKERS = dict(zip(SPEEDS, ("o", "^")))
INPUTS = (
    "data/design-manifest.json", "data/ratings.csv",
    "data/initial-native-perfs.json", "data/final-native-perfs.json",
    "data/frozen-predictions-v1.csv", "data/frozen-predictions-v2.csv",
    "data/seed-baseline.csv", "data/execution-summary.json", "data/evaluation.json",
    "data/games.jsonl.gz", "data/resources-projection.jsonl.gz",
)


def utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def read_json(path):
    return json.loads(path.read_text())


def json_lines(path):
    with gzip.open(path, "rt") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def predictions(path):
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {(row["id"], row["speed"]): float(row["prediction"]) for row in rows}
    assert len(result) == len(rows), "Duplicate prediction keys"
    return result


def speed_legend(ax, **kwargs):
    ax.legend(handles=[Line2D([], [], color=COLORS[s], marker=MARKERS[s],
        linestyle="none", label=s.title()) for s in SPEEDS], frameon=False, **kwargs)


def save(fig, out, name):
    fig.savefig(out / f"{name}.png", dpi=190, facecolor="white")
    fig.savefig(out / f"{name}.svg", metadata={"Date": None}, facecolor="white")
    plt.close(fig)


def heldout_figure(root, out, manifest, final, bootstrap):
    ids = sorted(manifest["heldoutIds"])
    assert len(ids) == 50
    heldout_games = [final[i][s]["games"] for i in ids for s in SPEEDS]
    heldout_rd = [final[i][s]["rd"] for i in ids for s in SPEEDS]
    assert min(heldout_games) == 6 and max(heldout_games) == 7
    methods = (("Recorded seed", "seed-baseline.csv"),
               ("Primary V1", "frozen-predictions-v1.csv"),
               ("Secondary V2", "frozen-predictions-v2.csv"))
    tables = {name: predictions(root / "data" / filename) for name, filename in methods}
    metrics = {}
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    fig.subplots_adjust(left=.14, right=.98, top=.80, bottom=.25, wspace=.38)
    fig.suptitle("Held-out seeding predictions: the 100-point MAE target was not met", y=.97)
    for i, (method, _) in enumerate(methods):
        metrics[method] = {}
        for speed, offset in (("blitz", .12), ("rapid", -.12)):
            errors = np.array([abs(tables[method][(identity, speed)] - final[identity][speed]["rating"])
                               for identity in ids])
            rng = np.random.default_rng(bootstrap["seed"])
            boot = [np.mean(rng.choice(errors, len(errors), replace=True))
                    for _ in range(bootstrap["replicates"])]
            lo, hi = np.quantile(boot, [.025, .975])
            mean = float(np.mean(errors))
            metrics[method][speed] = {"mae": mean, "configurationBootstrapMae95": [float(lo), float(hi)]}
            axes[0].errorbar(mean, i + offset, xerr=[[mean-lo], [hi-mean]],
                            fmt=MARKERS[speed], color=COLORS[speed], capsize=3, markersize=6)
            axes[0].annotate(f"{mean:.0f}", (mean, i+offset), xytext=(0, 7 if offset > 0 else -15),
                             textcoords="offset points", ha="center", fontsize=9, color=COLORS[speed])
    axes[0].axvline(100, color=GRAY, linestyle="--", linewidth=1)
    axes[0].text(98, 2.47, "Target", ha="right", color=GRAY, fontsize=9)
    axes[0].set(yticks=range(3), yticklabels=[name for name, _ in methods],
                ylim=(-.5, 2.55), xlabel="Mean absolute error (rating points)",
                title="All 50 held-out configurations, each speed")
    speed_legend(axes[0], loc="upper left", bbox_to_anchor=(0, 1.0), ncol=2)
    limits = [float("inf"), -float("inf")]
    for speed in SPEEDS:
        actual = np.array([final[identity][speed]["rating"] for identity in ids])
        rd = np.array([final[identity][speed]["rd"] for identity in ids])
        pred = np.array([tables["Secondary V2"][(identity, speed)] for identity in ids])
        axes[1].errorbar(actual, pred, xerr=rd, fmt="none", ecolor=COLORS[speed], alpha=.12, linewidth=.7)
        axes[1].scatter(actual, pred, color=COLORS[speed], marker=MARKERS[speed], s=19, alpha=.8)
        limits[0] = min(limits[0], min(actual-rd), min(pred))
        limits[1] = max(limits[1], max(actual+rd), max(pred))
    limits = [np.floor(limits[0]/200)*200, np.ceil(limits[1]/200)*200]
    axes[1].plot(limits, limits, linestyle="--", linewidth=1, color=GRAY, zorder=0)
    axes[1].set(xlim=limits, ylim=limits, xlabel="Final native rating (whiskers: ±1 native RD)",
                ylabel="Frozen prediction", title="Secondary V2: noisy-label comparison")
    axes[1].set_aspect("equal", adjustable="box")
    for ax in axes:
        ax.grid(axis="x", alpha=.17)
    fig.text(.04, .12, f"Held-out accounts played only {min(heldout_games)}–{max(heldout_games)} games per speed; median final RD ≈{np.median(heldout_rd):.0f}. Native ratings are noisy relative labels.", fontsize=10)
    fig.text(.04, .075, "Left: 95% bootstrap intervals resample configurations (1,000 draws); label and rating-scale uncertainty are not included.", fontsize=9, color=GRAY)
    fig.text(.04, .035, "Right: RD whiskers describe native rating uncertainty, not prediction confidence. No absolute Lichess-scale validation.", fontsize=9, color=GRAY)
    save(fig, out, "heldout-seeding-error")
    return metrics


def original_figure(root, out, initial, final):
    with (root / "data/ratings.csv").open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["cohort"] == "original44"]
    assert len(rows) == 88
    metrics = {}
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.9))
    fig.subplots_adjust(left=.085, right=.98, top=.79, bottom=.24, wspace=.30)
    fig.suptitle("Original 44 bots: earned ratings moved while native uncertainty fell", y=.97)
    for speed in SPEEDS:
        ids = sorted(row["id"] for row in rows if row["speed"] == speed)
        before = np.array([initial[i][speed]["rating"] for i in ids])
        after = np.array([final[i][speed]["rating"] for i in ids])
        before_rd = np.array([initial[i][speed]["rd"] for i in ids])
        after_rd = np.array([final[i][speed]["rd"] for i in ids])
        assert len(ids) == 44
        for identity, b, a in zip(ids, before, after):
            row = next(r for r in rows if r["id"] == identity and r["speed"] == speed)
            assert abs(float(row["initialNativeRating"])-b) < 1e-7
            assert abs(float(row["finalNativeRating"])-a) < 1e-7
        axes[0].scatter(before, after-before, color=COLORS[speed], marker=MARKERS[speed], alpha=.75, s=26)
        axes[1].scatter(before_rd, after_rd, color=COLORS[speed], marker=MARKERS[speed], alpha=.75, s=26)
        metrics[speed] = {"meanAbsoluteRatingChange": float(np.mean(abs(after-before))),
            "initialMedianRd": float(np.median(before_rd)), "finalMedianRd": float(np.median(after_rd)),
            "initialNonprovisional": sum(not initial[i][speed]["provisional"] for i in ids),
            "finalNonprovisional": sum(not final[i][speed]["provisional"] for i in ids)}
    axes[0].axhline(0, color=GRAY, linewidth=1, linestyle="--")
    axes[0].set(xlabel="Actual native rating at start of this run", ylabel="Final − initial rating (points)", title="Rating change during this run")
    limit = max(axes[1].get_xlim()[1], axes[1].get_ylim()[1])
    axes[1].plot([0, limit], [0, limit], color=GRAY, linestyle="--", linewidth=1)
    axes[1].set(xlim=(60, limit), ylim=(60, limit), xlabel="Initial native RD", ylabel="Final native RD", title="Below diagonal: lower uncertainty")
    axes[1].set_aspect("equal", adjustable="box")
    for ax in axes:
        ax.grid(alpha=.17)
    speed_legend(axes[0], loc="upper left")
    before_count = sum(m["initialNonprovisional"] for m in metrics.values())
    after_count = sum(m["finalNonprovisional"] for m in metrics.values())
    rd_text = "; ".join(f"{s.title()} median RD {metrics[s]['initialMedianRd']:.0f} → {metrics[s]['finalMedianRd']:.0f}" for s in SPEEDS)
    fig.text(.05, .125, f"Native nonprovisional bot–speed ratings: {before_count}/88 → {after_count}/88. {rd_text}.", fontsize=10)
    fig.text(.05, .078, "Initial values are earned pre-run native ratings, including the earlier baseline adjustment—not the historical roster seeds.", fontsize=9, color=GRAY)
    fig.text(.05, .035, "Lower RD indicates relative rating precision within this pool; it does not establish an absolute Lichess rating scale.", fontsize=9, color=GRAY)
    save(fig, out, "original44-rating-stability")
    return metrics


def capacity_figure(root, out, summary):
    games = json_lines(root / "data/games.jsonl.gz")
    assert len(games) == summary["admitted"] == summary["finished"]
    assert summary["allAddedWaitsZero"], "Timing caption requires zero added human waits"
    start, end = utc(summary["workerStartedUtc"]), utc(summary["workerEndedOrLastEventUtc"])
    resources = [r for r in json_lines(root / "data/resources-projection.jsonl.gz") if start <= r["at"]/1000 <= end]
    assert len(resources) == summary["resources"]["samplesInsideWorkerWindow"]
    times = np.array([r["at"]/1000 for r in resources])
    roles = ("worker", "app", "adapter", "ws", "mongo", "redis", "gateway")
    memory = np.array([[int(r["cgroups"][role]["MemoryCurrent"]) for role in roles] for r in resources]) / 2**30
    counters = np.array([[int(r["cgroups"][role]["CPUUsageNSec"]) for role in roles] for r in resources], dtype=np.float64)
    dt = np.diff(times)
    cpu = np.diff(counters, axis=0) / 1e9 / dt[:, None]
    assert np.all(cpu >= 0) and np.all(dt > 0), "Missing/reset counter intervals require explicit handling"
    cpu_mean = np.average(cpu, axis=0, weights=dt)
    assert abs(sum(cpu_mean) - summary["resources"]["fullStackCpuLogicalCores"]["timeWeightedMeanLogicalCores"]) < 1e-7
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.2))
    fig.subplots_adjust(left=.08, right=.98, top=.85, bottom=.20, hspace=.48, wspace=.25)
    hours = (times-start)/3600
    ax = axes[0, 0]
    ordered = sorted(games, key=lambda g: g["admissionOrdinal"])
    ax.step([(utc(g["admittedAtUtc"])-start)/3600 for g in ordered], range(1, len(games)+1), where="post", color=BLUE)
    for ordinal, label in ((201, "Training"), (2001, "Validation")):
        x = (utc(ordered[ordinal-1]["admittedAtUtc"])-start)/3600
        ax.axvline(x, color=GRAY, linestyle=":", linewidth=.8)
        ax.text(x+.06, 2700, label, fontsize=8, color=GRAY)
    ax.set(ylim=(0, 3000), ylabel="Cumulative admissions", title="2,623 admitted; all finished and rated")
    ax = axes[0, 1]
    ax.plot(hours[1:], cpu.sum(axis=1), color=GRAY, alpha=.65, linewidth=.7, label="Seven recorded cgroups")
    ax.plot(hours[1:], cpu[:, 0], color=BLUE, linewidth=.8, label="Inference workers")
    ax.set(ylabel="Logical CPU cores", ylim=(0, 6), title=f"Time-weighted CPU: workers {cpu_mean[0]:.2f}, recorded total {sum(cpu_mean):.2f}")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax = axes[1, 0]
    ax.plot(hours, memory.sum(axis=1), color=GRAY, linewidth=.8, label="Seven recorded cgroups")
    ax.plot(hours, memory[:, 0], color=BLUE, linewidth=.8, label="Inference workers")
    ax.set(ylabel="Sampled current memory (GiB)", ylim=(0, 4), title=f"Recorded total sampled maximum: {memory.sum(axis=1).max():.2f} GiB")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax = axes[1, 1]
    latency = (("Inference", "inferenceMs"), ("Request → commit", "requestCommitMs"), ("Whole turn", "turnCommitMs"))
    for y, (_, key) in enumerate(latency):
        mean, p95 = summary[key]["mean"]/1000, summary[key]["p95"]/1000
        ax.plot([mean, p95], [y, y], color=GRAY, linewidth=1)
        ax.scatter(mean, y, color=BLUE, s=28, label="Mean" if y == 0 else None)
        ax.scatter(p95, y, color=ORANGE, marker="|", s=100, label="95th percentile" if y == 0 else None)
        ax.text(p95+.06, y, f"{mean:.2f} / {p95:.2f}", va="center", fontsize=8)
    ax.set(yticks=range(3), yticklabels=[label for label, _ in latency], xlim=(0, 3.8), ylim=(2.5, -.55), xlabel="Seconds (mean / 95th percentile)", title=f"{summary['uniqueAcknowledgedGamePlies']:,} acknowledged moves")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    for ax in (axes[0, 0], axes[0, 1], axes[1, 0]):
        ax.set(xlabel="Hours since worker start", xlim=(0, (end-start)/3600))
    for ax in axes.flat:
        ax.grid(alpha=.15)
    fig.suptitle(f"Measured bot-study capacity: {len(games):,} games in {(end-start)/3600:.2f} hours", y=.975)
    fig.text(.08, .905, f"Observed maximum study concurrency: {summary['maxObservedStudyConcurrencyAtSubmission']} games · {summary['observedUniquePliesPerWorkerSecond']:.2f} acknowledged plies/s · no added human timing waits", fontsize=10)
    fig.text(.05, .12, "Scope: inference workers + app, adapter, WebSocket, MongoDB, Redis and gateway cgroups; OS and unrecorded processes excluded.", fontsize=9, color=GRAY)
    fig.text(.05, .078, "Recorded services include concurrent public traffic. Memory is sampled current usage, not a continuous peak. No human-capacity claim.", fontsize=9, color=GRAY)
    fig.text(.05, .035, "Admission times are not completion times. Whole-turn latency includes queueing and game handling; it is not pure Maia inference time.", fontsize=9, color=GRAY)
    save(fig, out, "measured-capacity")
    return {"games": len(games), "elapsedHours": (end-start)/3600,
            "workerCpuTimeWeightedLogicalCores": float(cpu_mean[0]),
            "recordedTotalCpuTimeWeightedLogicalCores": float(sum(cpu_mean)),
            "recordedTotalSampledMemoryMaxGiB": float(memory.sum(axis=1).max()),
            "resourceSamples": len(resources)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = args.study_dir
    out = args.output_dir or root / "figures"
    out.mkdir(parents=True, exist_ok=True)
    assert np.__version__ == "2.3.5" and matplotlib.__version__ == "3.10.7", "Install requirements-figures.txt"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "svg.hashsalt": "mute-chess-strength-2026-10-31"})
    provenance = read_json(root / "provenance.json")
    bootstrap = provenance["bootstrap"]
    assert bootstrap == {"method": "numpy-default_rng-configuration-bootstrap", "seed": 137,
                         "replicates": 1000, "numpyVersion": "2.3.5"}
    manifest = read_json(root / "data/design-manifest.json")
    initial = read_json(root / "data/initial-native-perfs.json")
    final = read_json(root / "data/final-native-perfs.json")
    summary = read_json(root / "data/execution-summary.json")
    result = {"versions": {"numpy": np.__version__, "matplotlib": matplotlib.__version__},
              "inputSha256": {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in INPUTS},
              "bootstrap": bootstrap,
              "heldout": heldout_figure(root, out, manifest, final, bootstrap),
              "original44": original_figure(root, out, initial, final),
              "capacity": capacity_figure(root, out, summary)}
    evaluation = read_json(root / "data/evaluation.json")
    references = {"Primary V1": evaluation["procedures"]["primaryV1"],
                  "Secondary V2": evaluation["procedures"]["secondaryV2"],
                  "Recorded seed": evaluation["seedBaseline"]}
    for method, reference in references.items():
        for speed in SPEEDS:
            actual = result["heldout"][method][speed]
            expected = reference["speeds"][speed]
            assert abs(actual["mae"] - expected["nativeRatingMae"]) < 1e-9
            assert np.allclose(actual["configurationBootstrapMae95"],
                               expected["configurationBootstrapMae95"], rtol=0, atol=1e-9)
    (out / "figure-metrics.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("Built three figures (PNG + SVG) and figure-metrics.json from published evidence.")


if __name__ == "__main__":
    main()
