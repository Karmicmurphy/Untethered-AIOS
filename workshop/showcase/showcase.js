const rooms = [...document.querySelectorAll('[data-room]')];
function openRoom(name) {
  const target = rooms.find((room) => room.dataset.room === name);
  if (!target) return;
  rooms.forEach((room) => { room.hidden = room !== target; room.classList.toggle('active', room === target); });
  target.querySelector('h1')?.focus?.({ preventScroll: true });
  window.scrollTo(0, 0);
}
document.addEventListener('click', (event) => {
  const control = event.target.closest('[data-open]');
  if (control) openRoom(control.dataset.open);
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !document.querySelector('[data-room="crossroads"]:not([hidden])')) openRoom('crossroads');
});
function updateClock() {
  const now = new Date();
  const clock = document.querySelector('#local-time');
  if (clock) { clock.dateTime = now.toISOString(); clock.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
}
updateClock();
setInterval(updateClock, 30000);
