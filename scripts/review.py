import os
import sys
import subprocess
import google.generativeai as genai
from load_context import load_context

def get_pr_diff(pr_number):
    base = os.getenv("GITHUB_BASE_REF", "main")

    # Ensure the base branch exists
    subprocess.run(["git", "fetch", "origin", base], check=True)

    diff = subprocess.check_output(
        ["git", "diff", f"{base}...HEAD"],
        text=True
    )
    return diff


def build_prompt(context, diff):
    return f"""
You are an AI Code Review Assistant.

Your job:
- Review the pull request diff
- Follow *strictly* the project's architecture and code conventions
- Provide helpful, actionable feedback
- Keep comments concise but detailed
- Suggest improved commit messages when relevant
- Flag: bugs, smells, style issues, missing tests, or design violations

--- PROJECT CONTEXT ---
{context}

--- PULL REQUEST DIFF ---
{diff}

Return your answer in this format:

### 🔍 Summary
(overview)

### 🧩 File-by-file feedback
(file paths, issues, improvements)

### 🛠 Suggested Improvements
(better patterns, refactors)

### ✍️ Suggested Commit Message
(single recommended commit message)
"""


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Missing GEMINI_API_KEY", file=sys.stderr)
        sys.exit(1)

    pr_number = sys.argv[1]

    # Initialize Gemini client
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3-pro-preview")

    # Load context
    context = load_context()

    # Load PR diff
    diff = get_pr_diff(pr_number)

    # Build prompt
    prompt = build_prompt(context, diff)

    # Call Gemini
    response = model.generate_content(prompt)

    # Print to stdout (GitHub Action consumes this)
    print(response.text)


if __name__ == "__main__":
    main()
