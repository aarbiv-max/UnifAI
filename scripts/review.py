import os
import sys
import subprocess
import google.generativeai as genai
from load_context import load_context
from prompts import prompts
from argparse import ArgumentParser

parser = ArgumentParser(description="A simple script using argparse.")
parser.add_argument("--role", type=str, default="code_review", choices=prompts.keys(), help="The role to use for the reviewer.")
parser.add_argument("--pr_number", type=int, default=None, help="The PR number to use for the reviewer.")
parser.add_argument("--output_file", type=str, default=None, help="The changed files to use for the reviewer.")

args = parser.parse_args()

def get_changed_files():
    """Get list of changed files in the PR (excluding review system files)."""
    base = os.getenv("GITHUB_BASE_REF", "main")
    
    # Ensure the base branch exists
    subprocess.run(["git", "fetch", "origin", base], check=True, 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Get list of changed files
    changed = subprocess.check_output(
        ["git", "diff", f"{base}...HEAD", "--name-only"],
        text=True
    ).strip().split('\n')
    
    # Filter out empty strings and review system files
    return [f for f in changed if f and not f.startswith("scripts/")]

def get_pr_diff(pr_number):
    """Get PR diff, excluding review system files (scripts/)."""
    base = os.getenv("GITHUB_BASE_REF", "main")

    # Ensure the base branch exists
    subprocess.run(["git", "fetch", "origin", base], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    diff = subprocess.check_output(
        ["git", "diff", f"{base}...HEAD"],
        text=True
    )
    
    # Filter out diff sections for scripts/ files (don't review the reviewer!)
    lines = diff.splitlines()
    filtered_lines = []
    skip_section = False
    
    for line in lines:
        # Detect start of new file section in diff
        if line.startswith("diff --git"):
            # Check if this diff is for a scripts/ file
            if " b/scripts/" in line:
                skip_section = True
            else:
                skip_section = False
        
        # Only include lines that aren't part of a scripts/ file diff
        if not skip_section:
            filtered_lines.append(line)
    
    return "\n".join(filtered_lines)


def build_prompt(role, context='', diff=''):
    return prompts[role].format(context=context, diff=diff)

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Missing GEMINI_API_KEY", file=sys.stderr)
        sys.exit(1)
    role = args.role
    if role=="pr_description":
        output_file = 'description_output.txt'
    else:
        output_file = 'review_output.txt'
    pr_number = args.pr_number

    # Get changed files for smart context loading
    changed_files = get_changed_files()
    
    # Map files to domains for display
    def get_file_domain(file_path):
        """Determine which domain a file belongs to."""
        if file_path.startswith("ui/"):
            return "UI"
        elif file_path.startswith("ci/"):
            return "CI/CD"
        elif file_path.startswith("helm/"):
            return "HELM"
        else:
            return "OTHER"
    
    print(f"\n📝 Changed files ({len(changed_files)}):", file=sys.stderr)
    for f in changed_files[:10]:  # Show first 10
        domain = get_file_domain(f)
        print(f"   [{domain:6}] {f}", file=sys.stderr)
    if len(changed_files) > 10:
        print(f"   ... and {len(changed_files) - 10} more", file=sys.stderr)

    # Initialize Gemini client
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3-pro-preview")

    # Load context (only relevant domains)
    context, loaded_domains = load_context(changed_files)
    
    # Convert characters to tokens (rule of thumb: 1 token ≈ 4 chars)
    context_tokens = len(context) // 4
    
    # Show which domains were detected and loaded
    print(f"\n🎯 Loaded domains ({len(loaded_domains)}):", file=sys.stderr)
    domain_map = {
        "UI": "ui/ directory (includes client/, deployment/, etc.)",
        "CI/CD": "ci/ directory (Groovy pipelines)",
        "HELM": "helm/ directory (Kubernetes charts)"
    }
    all_domains = ["UI", "CI/CD", "HELM"]
    for domain in sorted(loaded_domains):
        print(f"   ✓ {domain:8} → {domain_map[domain]}", file=sys.stderr)
    
    print(f"\n📚 Context loaded: ~{context_tokens:,} tokens", file=sys.stderr)

    # Load PR diff
    diff = get_pr_diff(pr_number)

    # Build prompt
    prompt = build_prompt(context, diff)

    # Call Gemini
    print(f"🤖 Sending to Gemini for review...", file=sys.stderr)
    response = model.generate_content(prompt)

    # Print to stdout (GitHub Action consumes this)
    print(response.text)


if __name__ == "__main__":
    main()
