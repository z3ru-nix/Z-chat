export function boot() {
  window.addEventListener('load', () => {
    setTimeout(() => {
      const screen = document.getElementById('boot-screen');
      if (!screen) return;

      if (window.gsap) {
        gsap.to(screen, {
          opacity: 0, duration: 0.5,
          onComplete: () => screen.remove()
        });
      } else {
        screen.style.opacity = '0';
        screen.style.transition = 'opacity 0.5s';
        setTimeout(() => screen.remove(), 500);
      }
    }, 1900);
  });
}
