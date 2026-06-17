import json
import os
import asyncio
import aiohttp
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from typing import AsyncGenerator

MODEL = os.getenv("OLLAMA_MODEL", "minimax-m2.5:cloud")
LOCAL_OLLAMA_URL = "http://localhost:11434/api/chat"
CLOUD_OLLAMA_URL = "https://ollama.com/api/chat"
OLLAMA_URL = os.getenv("OLLAMA_URL") or (
    CLOUD_OLLAMA_URL if os.getenv("VERCEL") or os.getenv("OLLAMA_API_KEY") else LOCAL_OLLAMA_URL
)

_session: aiohttp.ClientSession | None = None


class OllamaConfigError(RuntimeError):
    pass


class OllamaAPIError(RuntimeError):
    pass


def is_cloud_url(url: str) -> bool:
    return urlparse(url).hostname == "ollama.com"


def _headers_for_url(url: str) -> dict:
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("OLLAMA_API_KEY")
    if api_key and is_cloud_url(url):
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def validate_ollama_config():
    if os.getenv("VERCEL") and not is_cloud_url(OLLAMA_URL):
        raise OllamaConfigError(
            "No Vercel, OLLAMA_URL precisa apontar para um endpoint publico."
        )
    if is_cloud_url(OLLAMA_URL) and not os.getenv("OLLAMA_API_KEY"):
        raise OllamaConfigError(
            "Configure OLLAMA_API_KEY nas variaveis de ambiente da Vercel."
        )




def ask_ollama(messages, *, temperature=0.35, timeout=60):
    """Versão síncrona — retorna a resposta completa de uma vez."""
    validate_ollama_config()

    payload = {
        "model": MODEL,
        "stream": False,
        "messages": messages,
        "options": {"temperature": temperature},
    }

    req = Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers_for_url(OLLAMA_URL),
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise OllamaAPIError(
            f"Ollama respondeu com HTTP {error.code}: {details[:500]}"
        ) from error

    return data.get("message", {}).get("content") or "Não consegui gerar uma resposta agora."


def ask_ollama_stream(messages, *, temperature=0.35, timeout=60):
    """Versão síncrona com streaming — gera token por token para o SSE."""
    validate_ollama_config()

    payload = {
        "model": MODEL,
        "stream": True,
        "messages": messages,
        "options": {"temperature": temperature},
    }

    req = Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers_for_url(OLLAMA_URL),
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as response:
            for line in response:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    continue
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise OllamaAPIError(
            f"Ollama respondeu com HTTP {error.code}: {details[:500]}"
        ) from error




async def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=20,
            keepalive_timeout=30,
        )
        _session = aiohttp.ClientSession(connector=connector)
    return _session


async def ask_ollama_stream_async(
    messages: list,
    *,
    temperature: float = 0.35,
    timeout: int = 60,
) -> AsyncGenerator[str, None]:
    """Versão async com streaming — para uso fora do Flask."""
    validate_ollama_config()

    payload = {
        "model": MODEL,
        "stream": True,
        "messages": messages,
        "options": {"temperature": temperature},
    }

    session = await get_session()

    try:
        async with session.post(
            OLLAMA_URL,
            json=payload,
            headers=_headers_for_url(OLLAMA_URL),
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status != 200:
                details = await response.text()
                raise OllamaAPIError(f"HTTP {response.status}: {details[:500]}")

            async for line in response.content:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    continue

    except aiohttp.ClientError as e:
        raise OllamaAPIError(f"Erro de conexão: {e}") from e


async def ask_ollama_batch(
    batch: list[list[dict]],
    *,
    temperature: float = 0.35,
    max_concurrent: int = 10,
) -> list[str]:
    """Processa várias mensagens em paralelo."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _one(messages):
        async with semaphore:
            chunks = []
            async for token in ask_ollama_stream_async(messages, temperature=temperature):
                chunks.append(token)
            return "".join(chunks)

    return await asyncio.gather(*[_one(m) for m in batch])


async def ask_ollama_safe(
    messages: list,
    *,
    retries: int = 3,
    temperature: float = 0.35,
) -> str:
    """Async com retry automático e backoff."""
    for attempt in range(retries):
        try:
            chunks = []
            async for token in ask_ollama_stream_async(messages, temperature=temperature):
                chunks.append(token)
            return "".join(chunks)
        except OllamaAPIError:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)

    return "Não consegui gerar uma resposta agora."