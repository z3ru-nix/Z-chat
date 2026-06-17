const STREAM_URL = '/chat/stream';
const CHAT_URL   = '/chat';

let _controller = null; 

export function stopStream() {
  if (_controller) {
    _controller.abort();
    _controller = null;
  }
}

export async function sendMessage(message, { onToken, onDone, onError, onStop }) {
  
  try {
    await _streamSSE(message, { onToken, onDone, onError, onStop });
  } catch (err) {
    if (err.name === 'AbortError') {
      onStop();
    } else {
   
      await _postFallback(message, { onToken, onDone, onError });
    }
  }
}


async function _streamSSE(message, { onToken, onDone, onError, onStop }) {
  _controller = new AbortController();
  const { signal } = _controller;

  const params = new URLSearchParams({ message, sessionId: _getSession() });
  const url = `${STREAM_URL}?${params}`;

  const response = await fetch(url, { signal });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); 

    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const raw = line.slice(5).trim();
      if (!raw) continue;

      try {
        const data = JSON.parse(raw);

        if (data.type === 'token') {
          onToken(data.content);
        } else if (data.type === 'done') {
          onDone();
          _controller = null;
          return;
        } else if (data.type === 'error') {
          onError(data.message);
          _controller = null;
          return;
        }
      } catch {
        
      }
    }
  }

  onDone();
  _controller = null;
}


async function _postFallback(message, { onToken, onDone, onError }) {
  try {
    const response = await fetch(CHAT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, sessionId: _getSession() }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    const answer = data.answer || 'Sem resposta.';

   
    for (const char of answer) {
      onToken(char);
      await _sleep(8);
    }

    onDone();
  } catch (err) {
    onError(err.message);
  }
}


function _getSession() {
  //let id = sessionStorage.getItem('name_session'); //altere
  if (!id) {
    id = Math.random().toString(36).slice(2);
   //sessionStorage.setItem('name_session', id); //altere
  }
  return id;
}

function _sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
