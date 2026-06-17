// Renderiza markdown básico
function renderMarkdown(text) {
  return text
    .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^\- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>');
}

export function addMessage(role, text, container) {
  // Remove empty state se existir
  const empty = document.getElementById('empty-state');
  if (empty) {
    if (window.gsap) {
      gsap.to(empty, { opacity: 0, y: -10, duration: 0.3, onComplete: () => empty.remove() });
    } else {
      empty.remove();
    }
  }

  const wrapper = document.createElement('div');
  wrapper.className = `message-wrapper ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'assistant' ? '𝓩' : '👤';

  const message = document.createElement('div');
  message.className = 'message';

  if (text) {
    message.innerHTML = role === 'assistant' ? renderMarkdown(text) : escapeHtml(text);
  }

  wrapper.appendChild(avatar);
  wrapper.appendChild(message);
  container.appendChild(wrapper);

  if (window.gsap) {
    gsap.fromTo(wrapper,
      { opacity: 0, y: 16 },
      { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' }
    );
  }

  container.scrollTop = container.scrollHeight;
  return wrapper;
}

export function showTyping(container) {
  const wrapper = document.createElement('div');
  wrapper.className = 'message-wrapper assistant typing';
  wrapper.id = 'typing-indicator';
  wrapper.innerHTML = `
    <div class="avatar">𝓩</div>
    <div class="message">
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    </div>
  `;
  container.appendChild(wrapper);

  if (window.gsap) {
    gsap.fromTo(wrapper, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.25 });
  }

  container.scrollTop = container.scrollHeight;
}

export function removeTyping(container) {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

// Acumula texto bruto e vai renderizando
let _rawBuffer = '';

export function appendToken(msgEl, token) {
  _rawBuffer += token;
  msgEl.innerHTML = renderMarkdown(_rawBuffer);
  const container = msgEl.closest('#chat-messages');
  if (container) container.scrollTop = container.scrollHeight;
}

export function finalizeMessage(msgEl) {
  msgEl.innerHTML = renderMarkdown(_rawBuffer);
  _rawBuffer = '';
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');
}
