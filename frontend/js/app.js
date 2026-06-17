import { boot } from './boot.js';
import { addMessage, showTyping, removeTyping, appendToken, finalizeMessage } from './messages.js';
import { resetEmpty, bindChips } from './empty.js';
import { sendMessage, stopStream } from './api.js';

const chatForm     = document.getElementById('chat-form');
const chatInput    = document.getElementById('chat-input');
const chatMessages = document.getElementById('chat-messages');
const btnNova      = document.getElementById('btn-nova');
const btnStop      = document.getElementById('btn-stop');
const btnSend      = document.getElementById('btn-send');


let isStreaming = false;


boot();


chatInput.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 130) + 'px';
});


chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new Event('submit'));
  }
});

btnNova.addEventListener('click', () => {
  if (isStreaming) {
    stopStream();
    setStreaming(false);
  }

  const children = Array.from(chatMessages.children);
  if (!children.length) return;

  if (window.gsap) {
    gsap.to(children, {
      opacity: 0, x: -20, duration: 0.2, stagger: 0.04,
      onComplete: () => {
        chatMessages.innerHTML = '';
        resetEmpty(chatMessages);
      }
    });
  } else {
    chatMessages.innerHTML = '';
    resetEmpty(chatMessages);
  }
});

// Botão parar
btnStop.addEventListener('click', () => {
  stopStream();
  setStreaming(false);
});

// Envio
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (isStreaming) return;

  const message = chatInput.value.trim();
  if (!message) return;

  addMessage('user', message, chatMessages);
  chatInput.value = '';
  chatInput.style.height = 'auto';

  setStreaming(true);
  showTyping(chatMessages);

  const botWrapper = await new Promise(resolve => {
    
    setTimeout(() => {
      removeTyping(chatMessages);
      const wrapper = addMessage('assistant', '', chatMessages);
      resolve(wrapper);
    }, 400);
  });

  const msgEl = botWrapper.querySelector('.message');
  msgEl.classList.add('cursor-blink');

  await sendMessage(message, {
    onToken: (token) => appendToken(msgEl, token),
    onDone: () => {
      msgEl.classList.remove('cursor-blink');
      finalizeMessage(msgEl);
      setStreaming(false);
    },
    onError: (err) => {
      msgEl.classList.remove('cursor-blink');
      msgEl.textContent = 'Erro ao conectar com o servidor. Tente novamente.';
      setStreaming(false);
    },
    onStop: () => {
      msgEl.classList.remove('cursor-blink');
      const label = document.createElement('span');
      label.className = 'stopped-label';
      label.textContent = '[ resposta interrompida ]';
      msgEl.appendChild(label);
      setStreaming(false);
    }
  });
});

function setStreaming(val) {
  isStreaming = val;
  btnSend.disabled = val;
  btnStop.classList.toggle('hidden', !val);
}


window.__bindChips = (container) => {
  bindChips(container, chatInput);
};
