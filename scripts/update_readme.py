import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

USERNAME = os.getenv("GITHUB_USERNAME", "mohamedmalekh")
README_PATH = os.getenv("README_PATH", "README.md")
START_MARKER = "<!--START:AUTO-REPOS-->"
END_MARKER = "<!--END:AUTO-REPOS-->"


def fetch_repositories() -> list[dict]:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")

    if token:
        # /user/repos can include private repositories when token has repo scope.
        base_url = "https://api.github.com/user/repos"
        query = {
            "affiliation": "owner",
            "sort": "pushed",
            "direction": "desc",
            "per_page": "100",
        }
    else:
        base_url = f"https://api.github.com/users/{USERNAME}/repos"
        query = {
            "sort": "pushed",
            "direction": "desc",
            "per_page": "100",
        }

    url = f"{base_url}?{urllib.parse.urlencode(query)}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-updater",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    repos = [r for r in data if not r.get("fork")]
    repos.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    return repos


def build_section(repos: list[dict]) -> str:
    public_count = sum(1 for r in repos if not r.get("private"))
    private_count = sum(1 for r in repos if r.get("private"))

    lines = []
    lines.append("## Auto-Updated Repository Snapshot")
    lines.append("")
    lines.append(
        f"Last update: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    lines.append("")
    lines.append(
        f"Owned repos detected: {len(repos)} (public: {public_count}, private: {private_count})"
    )
    lines.append("")
    lines.append("### Recently Updated Repositories")
    lines.append("")

    top_repos = repos[:8]
    if not top_repos:
        lines.append("No repositories found.")
    else:
        for repo in top_repos:
            name = repo.get("name", "unknown")
            html_url = repo.get("html_url", "")
            language = repo.get("language") or "N/A"
            visibility = "private" if repo.get("private") else "public"
            pushed_at = (repo.get("pushed_at") or "")[:10]
            lines.append(
                f"- [{name}]({html_url}) | {language} | {visibility} | last push: {pushed_at}"
            )

    lines.append("")
    lines.append(
        "Note: private repositories are included only when GH_TOKEN has the required permissions."
    )

    return "\n".join(lines)


def update_readme(section: str) -> None:
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER not in content or END_MARKER not in content:
        raise ValueError(
            "README markers not found. Add START/END markers before running this script."
        )

    start = content.index(START_MARKER) + len(START_MARKER)
    end = content.index(END_MARKER)

    new_content = content[:start] + "\n\n" + section + "\n\n" + content[end:]

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


if __name__ == "__main__":
    repositories = fetch_repositories()
    section = build_section(repositories)
    update_readme(section)
    print("README updated successfully.")
