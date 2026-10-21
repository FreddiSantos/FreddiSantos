"""Atualiza as seções automáticas do README do perfil.

- PINNED: tabela com os repositórios fixados; se não houver nenhum fixado, usa os
  repositórios públicos atualizados mais recentemente (sem forks e sem o próprio perfil).
- METRICS: mostra a imagem github-metrics.svg só se o arquivo existir (evita imagem quebrada
  enquanto o secret METRICS_TOKEN não estiver configurado).

Uso: python scripts/sync_pinned.py README.md
Variáveis: GITHUB_TOKEN (obrigatória), PROFILE_LOGIN (padrão: FreddiSantos).
Só usa a biblioteca padrão; rodar duas vezes seguidas não muda nada.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PINNED = ("<!-- PINNED:START -->", "<!-- PINNED:END -->")
METRICS = ("<!-- METRICS:START -->", "<!-- METRICS:END -->")
EMPTY = "_Projects coming soon._"
METRICS_FILE = "github-metrics.svg"
METRICS_BLOCK = f"## 📊 GitHub metrics\n\n![GitHub metrics]({METRICS_FILE})"

REPO_FIELDS = "name url description stargazerCount isFork primaryLanguage { name }"
QUERY = f"""
query($login: String!) {{
  user(login: $login) {{
    pinnedItems(first: 6, types: REPOSITORY) {{
      nodes {{ ... on Repository {{ {REPO_FIELDS} }} }}
    }}
    repositories(first: 10, privacy: PUBLIC, ownerAffiliations: OWNER,
                 orderBy: {{field: PUSHED_AT, direction: DESC}}) {{
      nodes {{ {REPO_FIELDS} }}
    }}
  }}
}}
"""


def fetch_featured(login: str, token: str) -> list[dict]:
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    user = data["data"]["user"]
    pinned = user["pinnedItems"]["nodes"]
    if pinned:
        return pinned
    recent = user["repositories"]["nodes"]
    return [r for r in recent if not r["isFork"] and r["name"] != login][:6]


def render(repos: list[dict]) -> str:
    if not repos:
        return EMPTY
    lines = ["| Project | Description | Language |", "|---|---|---|"]
    for r in repos:
        desc = (r.get("description") or "").replace("|", "\\|")
        lang = (r.get("primaryLanguage") or {}).get("name", "")
        lines.append(f"| [{r['name']}]({r['url']}) | {desc} | {lang} |")
    return "\n".join(lines)


def replace(readme: str, markers: tuple[str, str], content: str) -> str:
    start, end = markers
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(readme):
        raise ValueError(f"Marcadores {start} / {end} não encontrados.")
    inner = f"\n{content}\n" if content else "\n"
    return pattern.sub(lambda _: f"{start}{inner}{end}", readme)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "README.md")
    token = os.environ["GITHUB_TOKEN"]
    login = os.environ.get("PROFILE_LOGIN", "FreddiSantos")

    readme = path.read_text(encoding="utf-8")
    updated = replace(readme, PINNED, render(fetch_featured(login, token)))
    has_metrics = (path.parent / METRICS_FILE).exists()
    updated = replace(updated, METRICS, METRICS_BLOCK if has_metrics else "")

    if updated != readme:
        path.write_text(updated, encoding="utf-8", newline="\n")
        print("README atualizado.")
    else:
        print("README já estava em dia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
