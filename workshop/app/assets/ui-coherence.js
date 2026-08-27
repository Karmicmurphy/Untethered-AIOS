(() => {
  "use strict";

  const pad = value => String(value).padStart(2, "0");
  const formatTime = date => `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  const formatDate = date => new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(date);

  function installOperationalClock() {
    const topbarActions = document.querySelector(".topbar > div:last-child");
    if (!topbarActions || document.querySelector("#operationalTime")) return;
    const clock = document.createElement("div");
    clock.className = "operational-clock";
    clock.setAttribute("aria-label", "Local operational time");
    clock.innerHTML = '<span>LOCAL TIME</span><time id="operationalTime">--:--:--</time><small id="operationalDate">Browser clock</small>';
    topbarActions.prepend(clock);
  }

  function installMachineClock() {
    const deck = document.querySelector("#recoverControlDeck .shell-screen-head");
    if (!deck || document.querySelector("#machineTime")) return;
    const rail = document.createElement("div");
    rail.className = "machine-time-rail";
    rail.innerHTML = '<span>RECEIPT CHRONOLOGY · LOCAL TIME</span><time id="machineTime">--:--:--</time><span>NEWEST VERIFIED EVENTS FIRST</span>';
    deck.insertAdjacentElement("afterend", rail);
  }

  function updateClocks() {
    const now = new Date();
    const time = formatTime(now);
    const date = formatDate(now);
    for (const id of ["sanctuaryTime", "crossroadsTime", "operationalTime", "machineTime"]) {
      const node = document.getElementById(id);
      if (node) {
        node.textContent = time;
        node.setAttribute("datetime", now.toISOString());
      }
    }
    const sanctuaryDate = document.getElementById("sanctuaryDate");
    const operationalDate = document.getElementById("operationalDate");
    if (sanctuaryDate) sanctuaryDate.textContent = date;
    if (operationalDate) operationalDate.textContent = date;

    const seconds = now.getSeconds();
    const minutes = now.getMinutes() + seconds / 60;
    const hours = (now.getHours() % 12) + minutes / 60;
    const hour = document.querySelector(".clock-hour");
    const minute = document.querySelector(".clock-minute");
    const second = document.querySelector(".clock-second");
    if (hour) hour.style.transform = `rotate(${hours * 30}deg)`;
    if (minute) minute.style.transform = `rotate(${minutes * 6}deg)`;
    if (second) second.style.transform = `rotate(${seconds * 6}deg)`;
  }

  function init() {
    document.documentElement.classList.add("ui-coherence");
    installOperationalClock();
    installMachineClock();
    updateClocks();
    window.setInterval(updateClocks, 1000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
