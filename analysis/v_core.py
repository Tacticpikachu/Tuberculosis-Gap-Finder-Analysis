"""Core validation: V2 forecast accuracy, V3 better than chance, V4 death funnel. V1 skipped (team decision).

Reads:  data/clean/score_a.csv, data/raw/tb_state_year.csv (optional; columns state, year,
        notifications, deaths [, tier])
Saves:  outputs/validation_results.csv, outputs/roc_curve.png, outputs/confusion_matrix.png,
        outputs/funnel.png (if V4 data), outputs/validation_log.md
Pass rules are those fixed in README.md.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import binomtest, hypergeom, norm
from sklearn.metrics import roc_auc_score, roc_curve

ROOT = Path(__file__).resolve().parents[1]
CLEAN, RAW, OUT = ROOT / "data" / "clean", ROOT / "data" / "raw", ROOT / "outputs"
STATE = RAW / "tb_state_year.csv"
N_BOOT, SEED, TOP = 1000, 42, 3
MYT = timezone(timedelta(hours=8))


def top_k(df, col):
    """Top 3 by col within year; ties broken by higher raw case count (README)."""
    order = df.sort_values([col, "cases"], ascending=False).groupby("year").cumcount()
    return order.sort_index() < TOP


def metrics(y, pred, score, truth_rate, pred_rate):
    tp, fp = int((pred & y).sum()), int((pred & ~y).sum())
    fn, tn = int((~pred & y).sum()), int((~pred & ~y).sum())
    div = lambda a, b: a / b if b else np.nan
    auc = roc_auc_score(y, score) if 0 < y.sum() < len(y) else np.nan
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "sensitivity": div(tp, tp + fn),
            "specificity": div(tn, tn + fp), "ppv": div(tp, tp + fp), "npv": div(tn, tn + fn),
            "auc": auc, "mae": float(np.mean(np.abs(pred_rate - truth_rate)))}


def v2(a):
    years = sorted(a["year"].unique())
    pairs = [(int(t), int(t) + 1) for t in years if t + 1 in years]
    if not pairs:
        return None, "no consecutive year pair with data"
    rows = []
    for t, t1 in pairs:
        cur, nxt = a[a.year == t].set_index("code"), a[a.year == t1].set_index("code")
        nxt = nxt.assign(truth=top_k(nxt.reset_index(), "raw_rate").to_numpy())
        cur = cur.assign(model=top_k(cur.reset_index(), "smoothed_rate").to_numpy(),
                         base=top_k(cur.reset_index(), "raw_rate").to_numpy())
        j = cur.join(nxt[["truth", "raw_rate", "partial_year"]], rsuffix="_t1")
        rows.append(j.assign(year_t=t, year_t1=t1).reset_index())
    d = pd.concat(rows, ignore_index=True)
    y = d["truth"].to_numpy(bool)
    res = {}
    for name, pred, score in [("model", "model", "smoothed_rate"), ("baseline", "base", "raw_rate")]:
        res[name] = metrics(y, d[pred].to_numpy(bool), d[score].to_numpy(float),
                            d["raw_rate_t1"].to_numpy(float), d[score].to_numpy(float))
    skill = 1 - res["model"]["mae"] / res["baseline"]["mae"]

    rng = np.random.default_rng(SEED)
    boot = {k: [] for k in ["auc", "sensitivity", "skill"]}
    for _ in range(N_BOOT):
        i = rng.integers(0, len(d), len(d))
        b = d.iloc[i]
        yb = b["truth"].to_numpy(bool)
        m = metrics(yb, b["model"].to_numpy(bool), b["smoothed_rate"].to_numpy(float),
                    b["raw_rate_t1"].to_numpy(float), b["smoothed_rate"].to_numpy(float))
        bm = np.mean(np.abs(b["raw_rate"] - b["raw_rate_t1"]))
        boot["auc"].append(m["auc"]); boot["sensitivity"].append(m["sensitivity"])
        boot["skill"].append(1 - m["mae"] / bm if bm else np.nan)
    ci = {k: tuple(np.nanpercentile(v, [2.5, 97.5])) for k, v in boot.items()}

    mc = d["model"] == d["truth"]; bc = d["base"] == d["truth"]
    b01, b10 = int((mc & ~bc).sum()), int((~mc & bc).sum())
    mcnemar_p = binomtest(b01, b01 + b10, 0.5).pvalue if b01 + b10 else 1.0

    passed = (ci["auc"][0] > 0.5) and (res["model"]["sensitivity"] >= 0.67) and (skill > 0)
    out = {"pairs": pairs, "n": len(d), "res": res, "skill": skill, "ci": ci,
           "mcnemar": (b01, b10, mcnemar_p), "pass": passed, "data": d,
           "partial": bool(d["partial_year_t1"].any() | d["partial_year"].any())}
    return out, None


def v3(d):
    rounds = d.groupby("year_t")
    hits = int((d["model"] & d["truth"]).sum())
    pmf = np.array([1.0])
    one = hypergeom(10, TOP, TOP).pmf(np.arange(TOP + 1))
    for _ in range(rounds.ngroups):
        pmf = np.convolve(pmf, one)
    return hits, rounds.ngroups, float(pmf[hits:].sum())


def v4():
    if not STATE.exists():
        return None
    s = pd.read_csv(STATE)
    s = s.groupby("state", as_index=False)[["notifications", "deaths"]].sum()
    p0 = s["deaths"].sum() / s["notifications"].sum()
    n = np.linspace(max(1, s["notifications"].min() * 0.8), s["notifications"].max() * 1.1, 300)
    lim = {z: p0 + z * np.sqrt(p0 * (1 - p0) / n) for z in (norm.ppf(0.975), norm.ppf(0.999))}
    se = np.sqrt(p0 * (1 - p0) / s["notifications"])
    s["ratio"] = s["deaths"] / s["notifications"]
    s["above_95"] = s["ratio"] > p0 + norm.ppf(0.975) * se
    s["above_998"] = s["ratio"] > p0 + norm.ppf(0.999) * se
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(s["notifications"], s["ratio"], c=np.where(s["above_95"], "#c0392b", "#34495e"))
    for _, r in s.iterrows():
        ax.annotate(r["state"], (r["notifications"], r["ratio"]), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.axhline(p0, color="grey", lw=1)
    for z, ls, lab in [(norm.ppf(0.975), "--", "95%"), (norm.ppf(0.999), ":", "99.8%")]:
        ax.plot(n, lim[z], "k" + ls, lw=1, label=lab)
    ax.set(xlabel="TB notifications", ylabel="Deaths per notified case", title="V4 funnel plot")
    ax.legend(); fig.tight_layout(); fig.savefig(OUT / "funnel.png", dpi=150); plt.close(fig)
    return s, p0


def plots(r):
    d = r["data"]
    fig, ax = plt.subplots(figsize=(5, 5))
    for name, col in [("Model (smoothed)", "smoothed_rate"), ("Baseline (raw)", "raw_rate")]:
        fpr, tpr, _ = roc_curve(d["truth"], d[col])
        ax.plot(fpr, tpr, label=f"{name} AUC {roc_auc_score(d['truth'], d[col]):.2f}")
    ax.plot([0, 1], [0, 1], "k:", lw=1)
    ax.set(xlabel="False positive rate", ylabel="True positive rate", title="V2 ROC (pooled)")
    ax.legend(); fig.tight_layout(); fig.savefig(OUT / "roc_curve.png", dpi=150); plt.close(fig)
    m = r["res"]["model"]
    cm = np.array([[m["tp"], m["fn"]], [m["fp"], m["tn"]]])
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=14)
    ax.set_xticks([0, 1], ["Pred top-3", "Pred other"]); ax.set_yticks([0, 1], ["True top-3", "True other"])
    ax.set_title("V2 confusion matrix (model)"); fig.tight_layout()
    fig.savefig(OUT / "confusion_matrix.png", dpi=150); plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    a = pd.read_csv(CLEAN / "score_a.csv")
    rows, log = [], []
    rows.append({"test": "V1", "metric": "status", "value": "skipped (team decision)", "pass": ""})

    r, why = v2(a)
    if r is None:
        rows.append({"test": "V2", "metric": "status", "value": f"not run: {why}", "pass": ""})
    else:
        plots(r)
        for side in ("model", "baseline"):
            for k, v in r["res"][side].items():
                rows.append({"test": "V2", "metric": f"{side}_{k}", "value": v, "pass": ""})
        rows += [
            {"test": "V2", "metric": "skill_score", "value": r["skill"], "pass": ""},
            {"test": "V2", "metric": "auc_ci95", "value": "%.3f-%.3f" % r["ci"]["auc"], "pass": ""},
            {"test": "V2", "metric": "sensitivity_ci95", "value": "%.3f-%.3f" % r["ci"]["sensitivity"], "pass": ""},
            {"test": "V2", "metric": "skill_ci95", "value": "%.3f-%.3f" % r["ci"]["skill"], "pass": ""},
            {"test": "V2", "metric": "mcnemar_b01_b10_p", "value": "%d/%d p=%.3f" % r["mcnemar"], "pass": ""},
            {"test": "V2", "metric": "year_pairs", "value": str(r["pairs"]), "pass": ""},
            {"test": "V2", "metric": "verdict", "value": "AUC CI lower>0.5, sens>=0.67, skill>0",
             "pass": "PASS" if r["pass"] else "FAIL"}]
        hits, k, p = v3(r["data"])
        rows.append({"test": "V3", "metric": f"P(hits >= {hits} | {k} rounds)", "value": p, "pass": "report"})

    v = v4()
    if v is None:
        rows.append({"test": "V4", "metric": "status", "value": "not run: data/raw/tb_state_year.csv missing", "pass": ""})
    else:
        s, p0 = v
        flagged = s.loc[s["above_95"], "state"].tolist()
        rows.append({"test": "V4", "metric": "states_above_95", "value": ", ".join(flagged) or "none",
                     "pass": "H2 supported" if flagged else "H2 not supported"})
        rows.append({"test": "V4", "metric": "pooled_death_ratio", "value": p0, "pass": ""})

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "validation_results.csv", index=False)

    now = datetime.now(MYT).strftime("%Y-%m-%d %H:%M MYT")
    md = [f"# Validation log", f"Run: {now} · script analysis/v_core.py", "",
          "| Test | Result | Pass |", "|---|---|---|"]
    md.append("| V1 Data accuracy | skipped (team decision) | - |")
    if r is None:
        md.append(f"| V2 Forecast accuracy | not run: {why} | - |")
    else:
        m = r["res"]["model"]
        md.append(f"| V2 Forecast accuracy | pairs {r['pairs']}; n={r['n']}; AUC {m['auc']:.2f} "
                  f"(CI {r['ci']['auc'][0]:.2f}-{r['ci']['auc'][1]:.2f}); sens {m['sensitivity']:.2f}; "
                  f"skill {r['skill']:.2f}; McNemar p={r['mcnemar'][2]:.2f}"
                  f"{'; includes partial year(s)' if r['partial'] else ''} | {'PASS' if r['pass'] else 'FAIL'} |")
        md.append(f"| V3 Better than chance | {hits} hits over {k} round(s); P = {p:.3f} | reported |")
    md.append("| V4 Death check | " + ("not run: data/raw/tb_state_year.csv missing | - |" if v is None else
              f"flagged above 95%: {', '.join(flagged) or 'none'} | reported |"))
    for t in ["V5 Face validity", "V6 Cost model verification", "V7 Cost robustness",
              "V8 Siting robustness", "V9 Siting verification", "V10 Moran stability"]:
        md.append(f"| {t} | not completed (time) | - |")
    (OUT / "validation_log.md").write_text("\n".join(md) + "\n")

    print(f"Saved outputs/validation_results.csv: {len(res)} rows")
    print(res.to_string(index=False))
    print("\n" + "\n".join(md))


if __name__ == "__main__":
    main()
