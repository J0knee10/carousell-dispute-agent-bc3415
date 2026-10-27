"""Command line entry point: `uv run dispute-agent <command>`.

Exit code 75 means the Gemini quota ran out; progress is saved and the same
command resumes later.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

EXIT_QUOTA = 75


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def _print(msg: str) -> None:
    print(msg, flush=True)


def _quota_exit(err) -> int:
    from .llm import RateLimitError

    e = err.err if hasattr(err, "err") else err
    kind = "daily" if isinstance(e, RateLimitError) and e.daily else "per-minute"
    _print(f"\nSTOPPED: Gemini {kind} quota exhausted for model {getattr(e, 'model', '?')}.")
    if getattr(e, "retry_after_seconds", None):
        _print(f"Suggested retry after: {e.retry_after_seconds:.0f}s")
    _print("Progress is saved. Run the same command again later to resume.")
    _print("Tip: `dispute-agent wait-for-quota --model <model>` waits until the quota is back.")
    return EXIT_QUOTA


def cmd_check_llm(args) -> int:
    from pydantic import BaseModel

    from .llm import RateLimitError, get_llm

    class Ping(BaseModel):
        ok: bool

    for role in ("judge", "generator"):
        llm = get_llm(role, provider=args.provider)
        try:
            llm.generate(task="ping", system="Reply with ok=true.", prompt="ping", schema=Ping) if llm.name != "mock" else None
            _print(f"{role}: {llm.name}/{llm.model} OK")
        except RateLimitError as e:
            _print(f"{role}: {llm.name}/{llm.model} RATE LIMITED (daily={e.daily}, retry_after={e.retry_after_seconds})")
            return EXIT_QUOTA
    return 0


def cmd_build_index(args) -> int:
    from .rag.store import PolicyStore

    n = PolicyStore().build(force=args.force)
    _print(f"Indexed {n} clauses" if n else "Index already up to date")
    return 0


def cmd_sample_listings(args) -> int:
    from .data import mercari

    listings = mercari.sample_listings(n=args.n)
    out = mercari.write_sample(listings)
    _print(f"Wrote {len(listings)} listings to {out}")
    _print(mercari.summary(listings))
    return 0


def cmd_generate(args) -> int:
    from .data.generate import generate_all
    from .llm import RateLimitError, get_llm

    llm = get_llm("generator", provider=args.provider)
    try:
        n = generate_all(llm, limit=args.limit, progress=_print)
    except RateLimitError as e:
        return _quota_exit(e)
    _print(f"Generated {n} cases with {llm.model}")
    return 0


def cmd_split(args) -> int:
    from .data.cases import load_all_cases, make_splits, write_splits

    cases = load_all_cases()
    splits = make_splits(cases)
    out = write_splits(splits)
    _print(f"{len(splits['test'])} test / {len(splits['dev'])} dev cases -> {out}")
    return 0


def cmd_export_labels(args) -> int:
    from .data.labels import export_sheet

    out, n = export_sheet()
    _print(f"Labelling sheet with {n} cases -> {out}")
    return 0


def cmd_agreement(args) -> int:
    from .data.labels import agreement_report

    _print(json.dumps(agreement_report(), indent=2))
    return 0


def cmd_run_case(args) -> int:
    from .agent.graph import build_graph
    from .agent.runner import resume, run_to_review
    from .data.cases import cases_by_id
    from .llm import RateLimitError, get_llm
    from .rag.store import get_store

    case = cases_by_id()[args.case_id]
    llm = get_llm(provider=args.provider)
    graph = build_graph(llm, get_store(), draft_messages=args.approve)
    try:
        r = run_to_review(graph, case, llm)
        for step in r.trace:
            _print(f"- {step['step']} ({step['seconds']}s): {step['summary']}")
        _print(json.dumps(r.state["recommendation"], indent=2))
        if args.approve:
            final = resume(graph, r.thread_id, {"action": "approve", "staff": "cli"})
            _print(json.dumps(final.get("messages", {}), indent=2))
    except RateLimitError as e:
        return _quota_exit(e)
    return 0


def cmd_evaluate(args) -> int:
    from .config import load_config
    from .data.cases import case_ids_for, cases_by_id
    from .evaluation.harness import QuotaExhausted, run_system, write_run_info
    from .evaluation.report import build_report
    from .llm import get_llm
    from .rag.store import get_store

    cfg = load_config()
    llm = get_llm(provider=args.provider)
    run = args.run or f"{llm.name}_{args.split}"
    ids = case_ids_for(args.split)
    by_id = cases_by_id()
    cases = [by_id[i] for i in ids]
    write_run_info(run, {"split": args.split, "case_ids": ids, "provider": llm.name, "model": llm.model})
    systems = ["agent", "baseline"] if args.system == "both" else [args.system]
    threshold = cfg["agent"]["confidence_threshold"]
    try:
        for system in systems:
            run_system(system, cases, llm, get_store(), run, threshold, progress=_print)
    except QuotaExhausted as e:
        _print(f"Done {e.done}, remaining {e.remaining} for this system.")
        build_report(run)
        return _quota_exit(e)
    out, _ = build_report(run)
    _print(f"\nReport: {out}")
    _print(out.read_text(encoding="utf-8"))
    return 0


def cmd_report(args) -> int:
    from .evaluation.report import build_report

    out, _ = build_report(args.run)
    _print(out.read_text(encoding="utf-8"))
    return 0


def cmd_eval_retrieval(args) -> int:
    from .config import path
    from .evaluation.retrieval import evaluate_retrieval, format_retrieval

    lines = []
    for k in (1, 3, 5):
        res = evaluate_retrieval(k=k)
        if k == 3:
            misses = res["misses"]
        lines.append(format_retrieval(res))
    text = "\n\n".join(lines)
    text += "\n\nMisses at k=3 (hybrid):\n" + "\n".join(f"- {m['query']}: expected {m['expected']}, got {m['got']}" for m in misses["hybrid"])
    out = path("outputs.reports_dir") / "retrieval.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Retrieval evaluation\n\n" + text + "\n", encoding="utf-8")
    _print(text)
    _print(f"\nSaved to {out}")
    return 0


def cmd_whatif(args) -> int:
    from .evaluation.whatif import run_whatif
    from .evaluation.harness import QuotaExhausted

    try:
        out, result = run_whatif(args.change, split=args.split, limit=args.limit, provider=args.provider, progress=_print)
    except QuotaExhausted as e:
        return _quota_exit(e)
    _print(json.dumps(result["summary"], indent=2))
    _print(f"Saved to {out}")
    return 0


def cmd_wait_for_quota(args) -> int:
    """Block until a tiny request to the model succeeds. Used as a watchdog after a quota stop."""
    from pydantic import BaseModel

    from .config import gemini_api_key, load_config
    from .llm.gemini import GeminiClient
    from .llm import RateLimitError, LLMError

    class Ping(BaseModel):
        ok: bool

    model = args.model or load_config()["llm"]["judge_model"]
    client = GeminiClient(model=model, api_key=gemini_api_key() or "", max_retry_wait_seconds=0)
    deadline = time.time() + args.max_hours * 3600
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            client.generate(task="ping", system="Reply ok=true.", prompt="ping", schema=Ping)
            _print(f"Quota available again for {model} after {attempt} check(s).")
            return 0
        except RateLimitError as e:
            wait = max(args.interval, (e.retry_after_seconds or 0) + 5)
            _print(f"[{time.strftime('%H:%M:%S')}] still limited (daily={e.daily}); next check in {wait:.0f}s")
            time.sleep(wait)
        except LLMError as e:
            _print(f"Unexpected error: {e}")
            time.sleep(args.interval)
    _print("Gave up waiting.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dispute-agent", description="Carousell dispute agent tools")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, func, help_text):
        sp = sub.add_parser(name, help=help_text)
        sp.set_defaults(func=func)
        return sp

    def provider(sp):
        sp.add_argument("--provider", choices=["gemini", "mock"], default=None, help="override config.yaml")

    provider(add("check-llm", cmd_check_llm, "check the LLM provider responds"))
    add("build-index", cmd_build_index, "build the policy vector index").add_argument("--force", action="store_true")
    add("sample-listings", cmd_sample_listings, "sample listings from Mercari train.tsv").add_argument("--n", type=int, default=None)
    sp = add("generate", cmd_generate, "generate synthetic disputes (resumes)")
    sp.add_argument("--limit", type=int, default=None)
    provider(sp)
    add("split", cmd_split, "make the held-out test split")
    add("export-labels", cmd_export_labels, "create or refresh the labelling sheet")
    add("agreement", cmd_agreement, "agreement between the two labellers")
    sp = add("run-case", cmd_run_case, "run the agent on one case")
    sp.add_argument("case_id")
    sp.add_argument("--approve", action="store_true", help="approve the recommendation and draft messages")
    provider(sp)
    sp = add("evaluate", cmd_evaluate, "evaluate agent and/or baseline (resumes)")
    sp.add_argument("--system", choices=["agent", "baseline", "both"], default="both")
    sp.add_argument("--split", choices=["test", "dev", "all", "seed", "demo"], default="test")
    sp.add_argument("--run", default=None, help="run name (default <provider>_<split>)")
    provider(sp)
    add("report", cmd_report, "rebuild the report for a run").add_argument("run")
    add("eval-retrieval", cmd_eval_retrieval, "retrieval accuracy on the query set")
    sp = add("whatif", cmd_whatif, "re-judge past cases under a proposed policy change")
    sp.add_argument("change", help="the proposed rule, in plain English")
    sp.add_argument("--split", default="dev")
    sp.add_argument("--limit", type=int, default=None)
    provider(sp)
    sp = add("wait-for-quota", cmd_wait_for_quota, "wait until the Gemini quota is available")
    sp.add_argument("--model", default=None)
    sp.add_argument("--interval", type=float, default=300)
    sp.add_argument("--max-hours", type=float, default=26)
    return p


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    args = build_parser().parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
