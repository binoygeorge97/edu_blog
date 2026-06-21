#!/usr/bin/env python3
"""
Generate baseline and pipeline answers for an eval dataset.

Usage:
  python eval/generate.py --dataset smoke [--mode baseline|pipeline|both] [--force]
  python eval/generate.py --dataset full  [--mode baseline|pipeline|both] [--force]

Output files (skipped if they already exist, unless --force):
  eval/datasets/results_{dataset}_baseline.jsonl
  eval/datasets/results_{dataset}_pipeline.jsonl
"""

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()  # must run before app.telemetry so PHOENIX_* vars are present at register() time

import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app.telemetry  # noqa: F401 — Phoenix registration before any Claude calls
from app.pipeline import run_pipeline

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
DATASET_FILES = {"smoke": "qa_smoke", "full": "qa_30"}

BASELINE_SYSTEM = (
    "Answer the following question concisely and accurately in 1–3 sentences. "
    "Do not add caveats or hedges unless genuinely necessary."
)


def _qa_path(dataset: str) -> str:
    return os.path.join(DATASETS_DIR, f"{DATASET_FILES[dataset]}.jsonl")


def _results_path(dataset: str, mode: str) -> str:
    return os.path.join(DATASETS_DIR, f"results_{dataset}_{mode}.jsonl")


def _load_questions(dataset: str) -> list[dict]:
    with open(_qa_path(dataset)) as f:
        return [json.loads(line) for line in f if line.strip()]


def _guard(path: str, force: bool) -> bool:
    """Return True (skip) if file exists and --force was not passed."""
    if os.path.exists(path) and not force:
        print(f"  ⚠  {os.path.basename(path)} already exists — skipping (--force to overwrite)")
        return True
    return False


# ── Baseline via Batch API (50% off) ─────────────────────────────────────────

async def _generate_baseline(questions: list[dict], out_path: str) -> None:
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    requests = [
        {
            "custom_id": str(i),
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 512,
                "system": BASELINE_SYSTEM,
                "messages": [{"role": "user", "content": q["question"]}],
            },
        }
        for i, q in enumerate(questions)
    ]

    print(f"  Submitting batch of {len(requests)} baseline requests...")
    batch = await client.messages.batches.create(requests=requests)
    print(f"  Batch ID: {batch.id}")

    while batch.processing_status == "in_progress":
        await asyncio.sleep(30)
        batch = await client.messages.batches.retrieve(batch.id)
        counts = batch.request_counts
        print(f"  Status: {batch.processing_status} — "
              f"{counts.succeeded} succeeded, {counts.errored} errored, "
              f"{counts.processing} processing")

    answers: dict[str, str] = {}
    async for result in await client.messages.batches.results(batch.id):
        if result.result.type == "succeeded":
            text = result.result.message.content[0].text
            answers[result.custom_id] = text

    with open(out_path, "w") as f:
        for i, q in enumerate(questions):
            row = {
                "question": q["question"],
                "reference_answer": q["reference_answer"],
                "answer": answers.get(str(i), ""),
            }
            f.write(json.dumps(row) + "\n")

    print(f"  ✓ Baseline results → {out_path}")


# ── Pipeline (sequential to limit concurrent API fan-out) ────────────────────

async def _generate_pipeline(questions: list[dict], out_path: str) -> None:
    rows = []
    for i, q in enumerate(questions, 1):
        print(f"  Pipeline [{i}/{len(questions)}]: {q['question'][:70]}...")
        result = await run_pipeline(q["question"])
        rows.append({
            "question": q["question"],
            "reference_answer": q["reference_answer"],
            "answer": result.answer,
            "confidence": result.confidence,
            "confidence_level": result.confidence_level,
        })

    with open(out_path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print(f"  ✓ Pipeline results → {out_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", choices=["smoke", "full"], default="smoke",
                        help="smoke = 5 questions, full = 30 questions")
    parser.add_argument("--mode", choices=["baseline", "pipeline", "both"], default="both")
    parser.add_argument("--force", action="store_true", help="Overwrite existing result files")
    args = parser.parse_args()

    questions = _load_questions(args.dataset)
    print(f"Loaded {len(questions)} questions from {DATASET_FILES[args.dataset]}.jsonl\n")

    async def run() -> None:
        if args.mode in ("baseline", "both"):
            path = _results_path(args.dataset, "baseline")
            if not _guard(path, args.force):
                print("Generating baseline answers via Batch API...")
                await _generate_baseline(questions, path)

        if args.mode in ("pipeline", "both"):
            path = _results_path(args.dataset, "pipeline")
            if not _guard(path, args.force):
                print("Generating pipeline answers (sequential)...")
                await _generate_pipeline(questions, path)

    asyncio.run(run())


if __name__ == "__main__":
    main()
