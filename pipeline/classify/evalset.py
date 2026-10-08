"""Hand-checked evaluation set.

python -m pipeline.classify.evalset sample [--n 200] [--country TN]
    Writes data/eval/eval.csv: a stratified sample of classified jobs. The `label`
    column is blank; fill it with eligible | likely | unclear | not_eligible after
    reading the original posting (apply_url). Predictions live in a separate file so
    labelling stays blind.
python -m pipeline.classify.evalset score [--country TN]
    Precision of "eligible" and "not_eligible" against the labels.
"""

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from pipeline import config, db
from pipeline.classify.schema import Extraction
from pipeline.classify.verdict import verdict

DIR = Path("data/eval")
LABELS = DIR / "eval.csv"
PREDICTIONS = DIR / "predictions.csv"
VERDICTS = ["eligible", "likely", "unclear", "not_eligible"]


def predictions(conn, code: str) -> dict[str, tuple[str, str, str]]:
    """job id -> (verdict, reason, evidence) for open classified jobs."""
    out = {}
    for r in conn.execute(
        "SELECT j.id, j.location_raw, j.title, e.data FROM jobs j "
        "JOIN extractions e ON e.content_hash = j.content_hash WHERE j.expired_at IS NULL"
    ):
        data = json.loads(r["data"])
        data.pop("evidence_verified", None)
        e = Extraction(**data)
        v, reason = verdict(
            e, code, config.COUNTRIES[code], location=r["location_raw"] or "", title=r["title"]
        )
        out[r["id"]] = (v, reason, e.evidence_quote)
    return out


def sample(conn, n: int, code: str) -> None:
    preds = predictions(conn, code)
    by_verdict: dict[str, list[str]] = {v: [] for v in VERDICTS}
    for job_id, (v, _, _) in preds.items():
        by_verdict[v].append(job_id)
    rnd = random.Random(7)
    # Oversample the rare positive verdicts: precision there is what users feel.
    quota = {"eligible": n * 3 // 10, "likely": n * 3 // 10, "unclear": n // 5}
    quota["not_eligible"] = n - sum(quota.values())
    picked = []
    for v in VERDICTS:
        pool = sorted(by_verdict[v])
        picked += rnd.sample(pool, min(quota[v], len(pool)))
    rnd.shuffle(picked)

    DIR.mkdir(parents=True, exist_ok=True)
    rows = {
        r["id"]: r
        for r in conn.execute(
            f"SELECT id, company_name, title, location_raw, apply_url FROM jobs "
            f"WHERE id IN ({','.join('?' * len(picked))})",
            picked,
        )
    }
    with open(LABELS, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["job_id", "company", "title", "location", "apply_url", "label", "notes"])
        for i in picked:
            r = rows[i]
            w.writerow(
                [i, r["company_name"], r["title"], r["location_raw"], r["apply_url"], "", ""]
            )
    with open(PREDICTIONS, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["job_id", "country", "predicted", "reason", "evidence"])
        for i in picked:
            w.writerow([i, code, *preds[i]])
    print(f"wrote {len(picked)} rows to {LABELS} ({Counter(preds[i][0] for i in picked)})")


def score(code: str) -> str:
    with open(PREDICTIONS, encoding="utf-8") as fh:
        pred = {r["job_id"]: r["predicted"] for r in csv.DictReader(fh) if r["country"] == code}
    with open(LABELS, encoding="utf-8") as fh:
        gold = {r["job_id"]: r["label"].strip() for r in csv.DictReader(fh) if r["label"].strip()}
    pairs = [(pred[i], g) for i, g in gold.items() if i in pred]
    lines = [f"Labelled: {len(pairs)} of {len(pred)}", ""]
    for v in ("eligible", "not_eligible"):
        hits = [g for p, g in pairs if p == v]
        if hits:
            strict = sum(g == v for g in hits) / len(hits)
            lines.append(f"precision({v}) = {strict:.0%} over {len(hits)} predictions")
    elig = [g for p, g in pairs if p == "eligible"]
    if elig:
        ok = sum(g in ("eligible", "likely") for g in elig) / len(elig)
        lines.append(f"eligible predictions that are at least likely: {ok:.0%}")
    lines += [
        "",
        "confusion (rows = predicted, cols = label):",
        "| | " + " | ".join(VERDICTS) + " |",
    ]
    lines.append("|---" * (len(VERDICTS) + 1) + "|")
    for p in VERDICTS:
        cells = [str(sum(1 for a, g in pairs if a == p and g == v)) for v in VERDICTS]
        lines.append(f"| {p} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="pipeline.classify.evalset")
    p.add_argument("cmd", choices=["sample", "score"])
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--country", default="TN", choices=sorted(config.COUNTRIES))
    p.add_argument("--db", default=config.DB_PATH)
    args = p.parse_args(argv)
    if args.cmd == "sample":
        sample(db.connect(args.db), args.n, args.country)
    else:
        print(score(args.country))


if __name__ == "__main__":
    main()
