"""Atualiza a seção de projetos fixados do README a partir da API GraphQL do GitHub.

Uso: python scripts/sync_pinned.py README.md
Variáveis: GITHUB_TOKEN (obrigatória), PROFILE_LOGIN (padrão: FreddiSantos).
Só usa a biblioteca padrão; rodar duas vezes seguidas não muda nada.
"""

import json
import os
import re
import sys
import urllib.request

START, END = "<!-- PINNED:START -->", "<!-- PINNED:END -->"
EMPTY = "_Projects coming soon._"

QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          url
          description
          stargazerCount
          primaryLanguage { name }
        }
      }
    }
  }
}
"""


def fetch_pinned(login: str, token: str) -> list[dict]:
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
    return data["data"]["user"]["pinnedItems"]["nodes"]


def render(repos: list[dict]) -> str:
    if not repos:
        return EMPTY
    lines = ["| Project | Description | Language | ⭐ |", "|---|---|---|---|"]
    for r in repos:
        desc = (r.get("description") or "").replace("|", "\\|")
        lang = (r.get("primaryLanguage") or {}).get("name", "")
        lines.append(
            f"| [{r['name']}]({r['url']}) | {desc} | {lang} | {r['stargazerCount']} |"
        )
    return "\n".join(lines)


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "README.md"
    token = os.environ["GITHUB_TOKEN"]
    login = os.environ.get("PROFILE_LOGIN", "FreddiSantos")

    with open(path, encoding="utf-8") as f:
        readme = f.read()

    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(readme):
        print(f"Marcadores {START} / {END} não encontrados em {path}.", file=sys.stderr)
        return 1

    block = f"{START}\n{render(fetch_pinned(login, token))}\n{END}"
    updated = pattern.sub(lambda _: block, readme)
    if updated != readme:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(updated)
        print("README atualizado.")
    else:
        print("README já estava em dia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
