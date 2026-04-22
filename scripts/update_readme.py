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
    public_repos = [r for r in repos if not r.get("private")]
    private_repos = [r for r in repos if r.get("private")]

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
    lines.append("### Recently Updated Public Repositories")
    lines.append("")

    top_repos = public_repos[:8]
    if not top_repos:
        lines.append("No public repositories found.")
    else:
        for repo in top_repos:
            name = repo.get("name", "unknown")
            html_url = repo.get("html_url", "")
            language = repo.get("language") or "N/A"
            pushed_at = (repo.get("pushed_at") or "")[:10]
            lines.append(
                f"- [{name}]({html_url}) | {language} | last push: {pushed_at}"
            )

    lines.append("")
    lines.append("### Private Work (Tools Used Only)")
    lines.append("")

    if private_count == 0:
        lines.append("- No private repositories detected with current token.")
    else:
        language_counts: dict[str, int] = {}
        for repo in private_repos:
            lang = repo.get("language") or "N/A"
            language_counts[lang] = language_counts.get(lang, 0) + 1

        sorted_langs = sorted(
            language_counts.items(), key=lambda item: (-item[1], item[0].lower())
        )
        tools_summary = ", ".join(
            [f"{name} ({count})" for name, count in sorted_langs[:8]]
        )

        lines.append(f"- Private repositories: {private_count}")
        lines.append(
            f"- Main tools/languages used in private work: {tools_summary or 'N/A'}"
        )

    lines.append("")
    lines.append("Privacy rule: names and links of private repositories are never displayed.")

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
