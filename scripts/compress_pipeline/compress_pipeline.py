"""
Compress pipeline instruction files using LLMLingua-2 to reduce token cost.

Usage:
    python compress_pipeline.py --ratio 0.6
    python compress_pipeline.py --ratio 0.5 --output-dir ../../.cursor/skills-compressed
"""

import argparse
import os
import sys
from pathlib import Path

import tiktoken

REPO_ROOT = Path(__file__).resolve().parents[2]

PIPELINE_FILES = [
    ".cursor/commands/pipeline.md",
    ".cursor/skills/pipeline-designer/SKILL.md",
    ".cursor/skills/pipeline-design-reviewer/SKILL.md",
    ".cursor/skills/pipeline-coder/SKILL.md",
    ".cursor/skills/pipeline-code-reviewer/SKILL.md",
    ".cursor/skills/pipeline-qa/SKILL.md",
    ".cursor/skills/pipeline-debugger/SKILL.md",
]

FORCE_TOKENS = [
    # Verdicts
    "APPROVE",
    "NEEDS REVISION",
    "REJECT",
    "CLEAN",
    "NEEDS REFACTORING",
    "MAJOR CLEANUP REQUIRED",
    "PASS",
    "FAIL",
    "FIXED",
    "NOT FIXED",
    "PARTIALLY FIXED",
    # Severities
    "CRITICAL",
    "MAJOR",
    "MINOR",
    "ALIGNMENT ISSUE",
    # Phase headers
    "PHASE 1",
    "PHASE 2",
    "PHASE 3",
    "PHASE 4",
    "PHASE 5",
    "PHASE 6",
    # Control flow
    "IF",
    "ELSE",
    "THEN",
    "STOP",
    "WAIT",
    "MUST",
    "NEVER",
    "STRICT",
    "MANDATORY",
    # Pipeline modes
    "full",
    "design-only",
    "design-and-review",
    "implement",
    "review-only",
    "code-review-only",
    "qa-only",
    "debug",
    # Architecture terms
    "Domain",
    "Application",
    "Adapter",
    "Port",
    "Hexagonal",
    # Structural markers
    "###",
    "##",
    "#",
    "|",
    "---",
    "```",
]


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    enc = tiktoken.get_encoding(encoding_name)
    return len(enc.encode(text))


def compress_text(llm_lingua, text: str, ratio: float) -> str:
    result = llm_lingua.compress_prompt(
        text,
        rate=ratio,
        force_tokens=FORCE_TOKENS,
        drop_consecutive=True,
    )
    return result["compressed_prompt"]


def main():
    parser = argparse.ArgumentParser(
        description="Compress pipeline files using LLMLingua-2"
    )
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.6,
        help="Compression ratio — fraction of tokens to KEEP (default: 0.6)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: scripts/compress_pipeline/output/)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
        help="LLMLingua-2 model to use",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading LLMLingua-2 model: {args.model}")
    print("(First run will download the model, ~500MB)\n")

    from llmlingua import PromptCompressor

    llm_lingua = PromptCompressor(
        model_name=args.model,
        use_llmlingua2=True,
        device_map="cpu",
    )

    results = []
    total_original = 0
    total_compressed = 0

    print(f"{'File':<55} | {'Original':>8} | {'Compressed':>10} | {'Ratio':>5}")
    print("-" * 90)

    for rel_path in PIPELINE_FILES:
        src_path = REPO_ROOT / rel_path
        if not src_path.exists():
            print(f"WARNING: {rel_path} not found, skipping")
            continue

        original_text = src_path.read_text(encoding="utf-8")
        original_tokens = count_tokens(original_text)

        compressed_text = compress_text(llm_lingua, original_text, args.ratio)
        compressed_tokens = count_tokens(compressed_text)

        actual_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 0

        dest_path = output_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(compressed_text, encoding="utf-8")

        total_original += original_tokens
        total_compressed += compressed_tokens

        results.append({
            "file": rel_path,
            "original": original_tokens,
            "compressed": compressed_tokens,
            "ratio": actual_ratio,
        })

        print(f"{rel_path:<55} | {original_tokens:>8} | {compressed_tokens:>10} | {actual_ratio:>5.2f}")

    print("-" * 90)
    overall_ratio = total_compressed / total_original if total_original > 0 else 0
    print(f"{'TOTAL':<55} | {total_original:>8} | {total_compressed:>10} | {overall_ratio:>5.2f}")
    print(f"\nTokens saved: {total_original - total_compressed} "
          f"({(1 - overall_ratio) * 100:.1f}% reduction)")
    print(f"\nCompressed files written to: {output_dir.resolve()}")
    print(f"Target ratio: {args.ratio} | Actual ratio: {overall_ratio:.2f}")


if __name__ == "__main__":
    main()
