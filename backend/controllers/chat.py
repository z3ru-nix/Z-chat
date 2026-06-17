from flask import Blueprint, request, jsonify, Response, stream_with_context
from ollama import ask_ollama, ask_ollama_stream, MODEL, OllamaAPIError, OllamaConfigError
from backend.controllers.web_search import should_search, format_search_context
import json

chat_bp = Blueprint("chat", __name__)

MEMORY = {}
MAX_MEMORY_MESSAGES = 20

DEFAULT_NOTES = [
    "O aluno esta usando a ZCode como mentora de Linux em pt-BR.",
    "Prefere explicacoes praticas, diretas e com exemplos curtos.",
]

SYSTEM_PROMPT = f"""
Voce e a Zcode, uma IA especialista em Linux, tecnologia e programacao. Ajude com Linux e seu ecossistema, programacao em geral e tecnologia relacionada: terminal, comandos, shell script, permissoes, usuarios, pacotes, systemd, redes, servidores, seguranca, virtualizacao, WSL, distros, linguagens de programacao (Python, JavaScript, Bash, C, C++, Rust, Go, Java, PHP, Ruby, TypeScript e outras), desenvolvimento web, APIs, bancos de dados, DevOps, Docker, Kubernetes, Git, CI/CD, cloud, automacao e ferramentas de desenvolvimento.

Regras de conteudo:
- Voce TEM acesso a internet em tempo real. Quando resultados de busca forem fornecidos no contexto com a tag [Conteudo extraido da web], use essas informacoes como base principal da resposta e cite as fontes.
- Responda em pt-BR.
- Use exemplos praticos e curtos quando ajudar.
- Quando o usuario pedir orientacao de estudo em Linux, siga este roadmap:
  1. Base do Linux: terminal, arquivos, diretorios e comandos essenciais.
  2. Distros e ambiente: Ubuntu, Debian, Fedora, Arch, Mint, servidores, WSL e VMs.
  3. Pacotes e sistema: apt, dnf, pacman, atualizacoes, systemctl e journalctl.
  4. Permissoes e usuarios: sudo, grupos, chmod, chown e seguranca basica.
  5. Shell e automacao: Bash, pipes, redirecionamento, scripts e cron.
  6. Servidor final: SSH, firewall, servicos web, logs, backups e monitoramento.
- Quando o usuario pedir orientacao de estudo em programacao, sugira um roadmap adequado a linguagem ou area escolhida.
- Sugira roadmap apenas quando o aluno pedir orientacao de estudo.
- Se o usuario pedir algo fora de tecnologia, programacao ou Linux, explique com gentileza que voce so pode ajudar nesse tema.
- Voce pode criar um site completo e monstrar a imagem dele como ficou.

- Quando o usuario pedir codigo em qualquer linguagem (Python, JavaScript, Bash, C, C++, Rust, Go, Java, PHP, Ruby, TypeScript, etc.), siga estas diretrizes de qualidade:
  1. Escreva codigo idiomatico, seguindo as convencoes de estilo da linguagem (ex.: PEP8 em Python, Effective Go em Go, gofmt/rustfmt quando aplicavel).
  2. Inclua tratamento de erros adequado quando relevante (try/except, error returns, validacao de entrada).
  3. Use nomes de variaveis e funcoes claros e descritivos, evitando abreviacoes obscuras.
  4. Comente apenas o que nao for obvio — evite comentar linhas autoexplicativas.
  5. Sempre entregue o codigo completo e funcional, nunca trechos truncados, "resto do codigo aqui" ou pseudocodigo quando codigo real for pedido.
  6. Quando aplicavel, explique como rodar/compilar/testar (comando, dependencias, versao da linguagem).
  7. Em scripts shell, use shebang correto e trate erros (ex.: set -e, verificacao de variaveis).
  8. Em linguagens compiladas (C, C++, Rust, Go, Java), garanta codigo que compile sem warnings relevantes e siga boas praticas de seguranca de memoria/concorrencia quando aplicavel.
  9. Em codigo orientado a performance ou seguranca (ex.: parsing, rede, criptografia), aponte riscos comuns (overflow, injection, race conditions) mesmo sem o usuario pedir.



Regras de formatacao:
- Use no maximo 2 emojis por resposta. Prefira nenhum em respostas tecnicas.
- Nao use arte ASCII para representar interfaces graficas.
- Tabelas apenas quando comparar 3 ou mais itens com atributos distintos.
- Blocos de codigo apenas para comandos e codigo real — nao para texto comum.
- Nao termine respostas com listas de "o que voce quer aprender agora?". Seja direto.
- Respostas curtas para perguntas simples, detalhadas apenas quando necessario.
- Faça sites completos com detalhes bons.
- Mande o code e explicque.
- Modelo em uso: {MODEL}
""".strip()

def normalize_session_id(value):
    return str(value or "default").strip()[:80]


def build_messages(session_id, user_message, search_context: str = ""):
    history = MEMORY.get(session_id, [])[-MAX_MEMORY_MESSAGES:]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": "Notas fixas:\n" + "\n".join(DEFAULT_NOTES)},
    ]
    if search_context:
        messages.append({"role": "system", "content": search_context})
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages



@chat_bp.post("/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()
    session_id = normalize_session_id(body.get("sessionId"))

    if not message:
        return jsonify({"error": "Mensagem vazia"}), 400

    search_context = ""
    triggered = should_search(message)
    print(f"[DEBUG] Mensagem: {message}")
    print(f"[DEBUG] should_search disparou: {triggered}")

    if triggered:
        search_context = format_search_context(message)
        print(f"[DEBUG] Contexto gerado: {search_context[:300]}")

    try:
        messages = build_messages(session_id, message, search_context)
        answer = ask_ollama(messages)

        MEMORY.setdefault(session_id, []).extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ])

        return jsonify({
            "answer": answer,
            "memorySize": len(MEMORY[session_id]),
            "searched": bool(search_context),
        })

    except OllamaConfigError as e:
        return jsonify({"error": str(e)}), 500
    except OllamaAPIError:
        return jsonify({"error": "Erro ao falar com o Ollama"}), 500



@chat_bp.get("/chat/stream")
def chat_stream():
    message = request.args.get("message", "").strip()
    session_id = normalize_session_id(request.args.get("sessionId"))

    if not message:
        return jsonify({"error": "Mensagem vazia"}), 400

    search_context = ""
    triggered = should_search(message)
    print(f"[DEBUG STREAM] Mensagem: {message}")
    print(f"[DEBUG STREAM] should_search disparou: {triggered}")

    if triggered:
        search_context = format_search_context(message)
        print(f"[DEBUG STREAM] Contexto gerado: {search_context[:300]}")

    messages = build_messages(session_id, message, search_context)

    def generate():
        full_answer = []

        if search_context:
            yield f"data: {json.dumps({'type': 'search', 'searching': True})}\n\n"

        try:
            for token in ask_ollama_stream(messages):
                full_answer.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            answer = "".join(full_answer)
            MEMORY.setdefault(session_id, []).extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": answer},
            ])

            yield f"data: {json.dumps({'type': 'done', 'memorySize': len(MEMORY[session_id])})}\n\n"

        except OllamaAPIError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )




@chat_bp.post("/chat")
def chat_with_file():
 
    message = request.form.get("message", "").strip()
    session_id = normalize_session_id(request.form.get("sessionId"))
 

  
    if message:
        user_message += f"\n\nPergunta do usuário: {message}"

    try:
        messages = build_messages(session_id, user_message)
        answer = ask_ollama(messages)

        MEMORY.setdefault(session_id, []).extend([
            {"role": "assistant", "content": answer},
        ])

        return jsonify({
            "answer": answer,
            "memorySize": len(MEMORY[session_id])
        })

    except OllamaConfigError as e:
        return jsonify({"error": str(e)}), 500
    except OllamaAPIError:
        return jsonify({"error": "Erro ao falar com o Ollama"}), 502


 

@chat_bp.post("/memory/clear")
def clear_memory():
    body = request.get_json(silent=True) or {}
    session_id = normalize_session_id(body.get("sessionId"))
    MEMORY.pop(session_id, None)
    return jsonify({"ok": True})