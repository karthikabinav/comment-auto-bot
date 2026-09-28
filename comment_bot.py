"""comment-auto-bot: a GitHub robot that watches for new issues and posts a
label-based reply.

Behavior:
  - Issue with the "bug" label      -> "Thank you. We will fix it"
  - Issue with the "feature" label  -> "Thank you, we will consider to include this feature."
  - Issue with no label               -> "Thank you for your contribution!"

Deployments:
  - As a GitHub App / webhook listener on the "issues" event, or
  - As a scheduled task / GitHub Action that polls the repo for new issues.

Requires the GITHUB_TOKEN environment variable.
"""

import os
import sys
import requests

RESPONSES = {
    "bug": "Thank you. We will fix it",
    "feature": "Thank you, we will consider to include this feature.",
}
DEFAULT_RESPONSE = "Thank you for your contribution!"

GITHUB_API = "https://api.github.com"


def pick_response(labels):
    """Choose the reply based on the issue labels."""
    names = {label if isinstance(label, str) else label.get("name", "") for label in labels}
    if "bug" in names:
        return RESPONSES["bug"]
    if "feature" in names:
        return RESPONSES["feature"]
    return DEFAULT_RESPONSE


def handle_issue(session, owner, repo, number, labels):
    """Post the label-based reply to a single issue (idempotently)."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{number}/comments"
    existing = {c.get("body", "") for c in session.get(url).json()}
    body = pick_response(labels)
    if body in existing:
        print(f"Issue #{number}: already replied, skipping.")
        return False
    resp = session.post(url, json={"body": body})
    resp.raise_for_status()
    print(f"Issue #{number}: replied with: {body}")
    return True


def watch(owner, repo):
    """Watch for new open issues and reply to each one once."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"token {os.environ[GITHUB_TOKEN]}",
        "Accept": "application/vnd.github+json",
    })
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues?state=open&per_page=100"
    for issue in session.get(url).json():
        if "pull_request" in issue:  # skip pull requests
            continue
        handle_issue(session, owner, repo, issue["number"], issue.get("labels", []))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python comment_bot.py <owner> <repo>")
        sys.exit(1)
    watch(sys.argv[1], sys.argv[2])
