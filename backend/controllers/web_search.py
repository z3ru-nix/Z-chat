import json
import urllib.request
import urllib.parse
import urllib.error
import re
import os
from datetime import datetime
from html.parser import HTMLParser
from pymongo import MongoClient




MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
_db = None

def get_db():
    global _db
    if _db is None:
        client = MongoClient(MONGO_URI)
        _db = client["tunix"]
    return _db

def get_triggers_collection():
    return get_db()["search_triggers"]




LINUX_DOMAINS = {
    # Linux e distros
    "linux.org", "kernel.org", "tldp.org",
    "ubuntu.com", "debian.org", "fedoraproject.org",
    "archlinux.org", "manjaro.org", "linuxmint.com",
    "opensuse.org", "gentoo.org", "slackware.com",
    "redhat.com", "rockylinux.org", "almalinux.org",
    "man7.org", "die.net", "ss64.com",
    "wiki.archlinux.org", "help.ubuntu.com",
    "docs.fedoraproject.org", "wiki.debian.org",
    "systemd.io", "gnu.org", "bash.cyberciti.biz",
    "linuxhandbook.com", "linuxize.com",
    "tecmint.com", "cyberciti.biz", "nixcraft.com",
    "itsfoss.com", "omgubuntu.co.uk", "phoronix.com", "lwn.net",

    # Q&A e comunidades
    "askubuntu.com", "unix.stackexchange.com",
    "stackoverflow.com", "superuser.com",
    "reddit.com", "dev.to", "hashnode.com",

    # Documentações oficiais de linguagens
    "docs.python.org", "python.org",
    "developer.mozilla.org", "nodejs.org",
    "docs.oracle.com", "java.com",
    "golang.org", "go.dev",
    "rust-lang.org", "doc.rust-lang.org",
    "cppreference.com", "en.cppreference.com",
    "php.net", "ruby-lang.org", "docs.ruby-lang.org",
    "kotlinlang.org", "swift.org",
    "typescriptlang.org", "learn.microsoft.com",
    "docs.microsoft.com", "docs.oracle.com",
    "haskell.org", "scala-lang.org",

    # Frameworks e ferramentas
    "reactjs.org", "react.dev",
    "vuejs.org", "angular.io",
    "nextjs.org", "nuxt.com",
    "fastapi.tiangolo.com", "flask.palletsprojects.com",
    "djangoproject.com", "laravel.com",
    "expressjs.com", "nestjs.com",
    "spring.io", "quarkus.io",
    "flipper.net", "highboy.com",

    # DevOps e cloud
    "docs.docker.com", "kubernetes.io",
    "docs.github.com", "git-scm.com",
    "gitlab.com", "circleci.com",
    "docs.aws.amazon.com", "cloud.google.com",
    "docs.microsoft.com", "azure.microsoft.com",
    "terraform.io", "ansible.com",
    "helm.sh", "prometheus.io", "grafana.com",

    # Bancos de dados
    "postgresql.org", "mysql.com",
    "mongodb.com", "redis.io",
    "sqlite.org", "mariadb.org",
    "docs.mongodb.com", "cassandra.apache.org",

    # Segurança
    "owasp.org", "cve.mitre.org",
    "nmap.org", "metasploit.com",

    # Tutoriais e referências gerais
    "digitalocean.com", "linode.com",
    "howtogeek.com", "geeksforgeeks.org",
    "w3schools.com", "tutorialspoint.com",
    "realpython.com", "freecodecamp.org",
    "medium.com", "towardsdatascience.com",

    # Lojas para montar Pcs
    "pichau.com", "kbum.com.",
    "mercadolivre.com"
}

LINUX_KEYWORDS = {
    # Linux
    "linux", "ubuntu", "debian", "fedora", "arch", "mint",
    "kernel", "bash", "shell", "terminal", "apt", "dnf",
    "pacman", "systemd", "chmod", "sudo", "ssh", "nginx",
    "apache", "docker", "vim", "grep", "awk", "sed",
    "distro", "wsl", "unix", "gnu", "cli", "daemon",
    "cron", "firewall", "iptables", "ufw", "systemctl",

    # Programação — linguagens
    "python", "javascript", "typescript", "java", "kotlin",
    "golang", "rust", "ruby", "php", "swift", "scala",
    "haskell", "perl", "lua", "elixir", "clojure",
    "c++", "c#", "dotnet", "assembly",

    # Web
    "html", "css", "react", "vue", "angular", "nextjs",
    "nodejs", "express", "django", "flask", "fastapi",
    "laravel", "rails", "spring", "api", "rest", "graphql",
    "websocket", "http", "https", "json", "xml",

    # DevOps e infra
    "kubernetes", "container", "dockerfile", "compose",
    "git", "github", "gitlab", "ci", "cd", "pipeline",
    "ansible", "terraform", "helm", "prometheus", "grafana",
    "aws", "azure", "gcp", "cloud", "serverless",

    # Banco de dados
    "sql", "postgresql", "mysql", "mongodb", "redis",
    "sqlite", "mariadb", "nosql", "orm", "migration",

    # Conceitos gerais
    "algoritmo", "estrutura de dados", "design pattern",
    "api", "microservico", "monolito", "cache", "queue",
    "threading", "async", "concorrencia", "memoria",
    "compilador", "interpretador", "debug", "teste",
    "deploy", "build", "package", "library", "framework",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "Chrome/120.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

MAX_RESULTS = 4
MAX_PAGE_CHARS = 3000
MAX_SNIPPET_LEN = 400



class _TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form"}

    def __init__(self):
        super().__init__()
        self._skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self.parts.append(text)

    def get_text(self):
        return " ".join(self.parts)


def _extract_text_from_html(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    text = parser.get_text()
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_PAGE_CHARS]




def _is_linux_relevant(text: str, url: str) -> bool:
    domain = urllib.parse.urlparse(url).hostname or ""
    domain = domain.replace("www.", "")

    if any(d in domain for d in LINUX_DOMAINS):
        return True

    text_lower = text.lower()
    matches = sum(1 for kw in LINUX_KEYWORDS if kw in text_lower)
    return matches >= 2



def _ddg_search_urls(query: str) -> list[dict]:
    """Scrapa o DuckDuckGo HTML lite — mais confiável que a API JSON."""
    if "linux" not in query.lower():
        query = f"{query} linux"

    params = urllib.parse.urlencode({"q": query, "kl": "br-pt"})
    url = f"https://html.duckduckgo.com/html/?{params}"

    print(f"[DEBUG SEARCH] Query enviada ao DDG HTML: {query}")

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[DEBUG SEARCH] Erro ao chamar DDG HTML: {e}")
        return []

    results = []

    
    links = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )
    snippets = re.findall(
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )

    for i, (href, title) in enumerate(links):
        if len(results) >= MAX_RESULTS * 2:
            break

        # DDG usa redirecionamento, extrai URL real
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        real_url = qs.get("uddg", [href])[0]

        if not real_url.startswith("http"):
            continue

        snippet = ""
        if i < len(snippets):
            snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip()

        title_clean = re.sub(r"<[^>]+>", "", title).strip()

        results.append({
            "url": real_url,
            "title": title_clean,
            "snippet": snippet[:MAX_SNIPPET_LEN],
        })

    print(f"[DEBUG SEARCH] URLs encontradas pelo DDG HTML: {len(results)}")
    for r in results:
        print(f"[DEBUG SEARCH]   → {r['url']}")

    return results


def _fetch_page_content(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                print(f"[DEBUG SEARCH] Ignorado (não é HTML): {url}")
                return None
            html = resp.read().decode("utf-8", errors="replace")
            text = _extract_text_from_html(html)
            print(f"[DEBUG SEARCH] Página lida ({len(text)} chars): {url}")
            return text
    except Exception as e:
        print(f"[DEBUG SEARCH] Erro ao acessar página {url}: {e}")
        return None


def _ddg_search_real(query: str) -> list[dict]:
    raw_results = _ddg_search_urls(query)
    final_results = []

    for item in raw_results:
        if len(final_results) >= MAX_RESULTS:
            break

        url = item["url"]
        if not url.startswith("http"):
            continue

        page_text = _fetch_page_content(url)

        if page_text:
            if not _is_linux_relevant(page_text, url):
                print(f"[DEBUG SEARCH] Rejeitado (não é Linux): {url}")
                continue
            final_results.append({
                "title": item["title"],
                "url": url,
                "content": page_text,
            })
        else:
            if _is_linux_relevant(item["snippet"], url):
                final_results.append({
                    "title": item["title"],
                    "url": url,
                    "content": item["snippet"],
                })

    print(f"[DEBUG SEARCH] Total de resultados finais: {len(final_results)}")
    return final_results


def format_search_context(query: str) -> str:
    results = _ddg_search_real(query)

    if not results:
        print("[DEBUG SEARCH] Nenhum resultado — contexto vazio!")
        return ""

    lines = ["[Conteúdo extraído da web — apenas fontes sobre Linux]"]
    for i, r in enumerate(results, 1):
        lines.append(f"\n--- Fonte {i}: {r['title']} ---")
        lines.append(f"URL: {r['url']}")
        lines.append(r["content"])
    lines.append("\n[Fim do conteúdo web]")

    return "\n".join(lines)




def _load_learned_triggers() -> set:
    try:
        col = get_triggers_collection()
        return {doc["trigger"] for doc in col.find({}, {"trigger": 1})}
    except Exception:
        return set()


def learn_from_message(message: str):
    msg = message.lower().strip()
    words = msg.split()
    candidates = set()

    for i in range(len(words) - 1):
        candidates.add(f"{words[i]} {words[i+1]}")

    for i in range(len(words) - 2):
        candidates.add(f"{words[i]} {words[i+1]} {words[i+2]}")

    for word in words:
        if len(word) > 4:
            candidates.add(word)

    existing = _load_learned_triggers()
    col = get_triggers_collection()

    question_signals = [
        "como", "por que", "porque", "quando", "onde", "qual",
        "quais", "o que", "será", "existe", "tem como", "dá pra",
        "erro", "falhou", "não", "problema", "quem",
        "história", "origem", "criador",
    ]

    is_question = any(sig in msg for sig in question_signals)

    if is_question:
        for candidate in candidates:
            if candidate not in existing and len(candidate) > 4:
                try:
                    col.update_one(
                        {"trigger": candidate},
                        {"$setOnInsert": {
                            "trigger": candidate,
                            "learned_at": datetime.utcnow(),
                            "source_message": message[:200],
                            "hits": 0,
                        }},
                        upsert=True,
                    )
                except Exception:
                    pass


def register_trigger_hit(message: str):
    msg = message.lower()
    col = get_triggers_collection()
    for trigger in _load_learned_triggers():
        if trigger in msg:
            try:
                col.update_one({"trigger": trigger}, {"$inc": {"hits": 1}})
            except Exception:
                pass




def should_search(message: str) -> bool:
    """Busca sempre, exceto mensagens muito curtas ou confirmações simples."""
    msg = message.lower().strip()

    if len(msg) < 4:
        return False

    skip = {
        "ok", "sim", "não", "nao", "certo", "beleza", "obrigado",
        "obg", "valeu", "oi", "olá", "ola", "opa", "tá", "ta",
        "show", "legal", "entendi", "blz", "bom", "ótimo", "otimo",
        "achou?", "cade?", "mande ai", "mande", "pode mandar",
    }

    if msg in skip:
        return False

    learn_from_message(message)
    return True