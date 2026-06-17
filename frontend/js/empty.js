export function resetEmpty(container) {
  const empty = document.createElement('div');
  empty.className = 'empty-state';
  empty.id = 'empty-state';
  empty.innerHTML = `
    <div class="empty-icon">💬</div>
    <h2>COMO POSSO AJUDAR?</h2>
    <p>Especialista em Linux, programação e tecnologia.</p>
    
  `;
  container.appendChild(empty);

  if (window.gsap) {
    gsap.fromTo(empty, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.35 });
  }

  
  if (window.__bindChips) {
    window.__bindChips(empty);
  }
}

export function bindChips(container, inputEl) {
  container.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      inputEl.value = chip.textContent;
      inputEl.dispatchEvent(new Event('input'));
      inputEl.focus();
    });
  });
}
