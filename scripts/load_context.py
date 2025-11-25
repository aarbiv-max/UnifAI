import os

def load_context():
    """
    Loads architecture and coding convention documents
    from the repo. You can add/remove files as needed.
    """

    files = [
        "ui/ARCHITECTURE.md",
        "ui/README.md",
    ]

    content = []

    for path in files:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content.append(f"\n\n### FILE: {path}\n\n" + f.read())

    return "\n".join(content)
