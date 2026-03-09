/**
 * Whoop + Tapo Dashboard — Frontend
 */

const API = "/api";

function kelvinToRgb(k) {
  k = Math.max(2500, Math.min(6500, k)) / 100;
  let r, g, b;
  if (k <= 66) {
    r = 255;
    g = k <= 19 ? 0 : 99.4708025861 * Math.log(k) - 161.1195681661;
    b = k <= 19 ? 0 : 138.5177312231 * Math.log(k - 10) - 305.0447927307;
  } else {
    r = 329.698727446 * Math.pow(k - 60, -0.1332047592);
    g = 288.1221695283 * Math.pow(k - 60, -0.0755148492);
    b = 255;
  }
  return [
    Math.round(Math.max(0, Math.min(255, r))),
    Math.round(Math.max(0, Math.min(255, g))),
    Math.round(Math.max(0, Math.min(255, b))),
  ];
}

function formatRecoveryColor(rec) {
  if (rec == null) return "";
  if (rec >= 66) return "green";
  if (rec >= 34) return "yellow";
  return "red";
}

function fmt(val, suffix = "") {
  return val != null ? `${val}${suffix}` : "—";
}

async function fetchState() {
  const res = await fetch(`${API}/state`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch state");
  return res.json();
}

async function refresh() {
  const res = await fetch(`${API}/refresh`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to refresh");
  return fetchState();
}

async function sendCommand(message) {
  const res = await fetch(`${API}/command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Command failed");
  }
  return res.json();
}

async function lightSet(colorTemp, brightness) {
  const res = await fetch(`${API}/light/set`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ color_temp: colorTemp, brightness }),
  });
  if (!res.ok) throw new Error("Light set failed");
  return res.json();
}

async function lightOn() {
  const res = await fetch(`${API}/light/on`, { method: "POST" });
  if (!res.ok) throw new Error("Light on failed");
  return res.json();
}

async function lightOff() {
  const res = await fetch(`${API}/light/off`, { method: "POST" });
  if (!res.ok) throw new Error("Light off failed");
  return res.json();
}

async function bedtimeSignal() {
  const res = await fetch(`${API}/bedtime-signal`, { method: "POST" });
  if (!res.ok) throw new Error("Bedtime signal failed");
  return res.json();
}

async function setMood(mood) {
  const res = await fetch(`${API}/mood`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mood }),
  });
  if (!res.ok) throw new Error("Mood set failed");
  return res.json();
}

function computeSchedulerMode() {
  const now = new Date();
  const h = now.getHours();
  const m = now.getMinutes();
  const mins = h * 60 + m;
  if (mins >= 20 * 60 && mins < 22 * 60) return "SLEEP_PREP";
  if (mins >= 22 * 60 || mins < 5 * 60 + 30) return "SLEEPING";
  if (mins >= 5 * 60 + 30 && mins < 5 * 60 + 45) return "SUNRISE";
  return "AWAKE";
}

function updateConnectionStatus(connections) {
  const whoop = document.getElementById("conn-whoop");
  const light = document.getElementById("conn-light");
  if (whoop) {
    whoop.className = "connection-dot connection-whoop " + (connections?.whoop ? "connected" : "disconnected");
  }
  if (light) {
    light.className = "connection-dot connection-light " + (connections?.light ? "connected" : "disconnected");
  }
}

function updateOrbFromSliders(cct, brightness) {
  const orb = document.getElementById("light-orb");
  const glow = document.getElementById("light-orb-glow");
  const [r, g, b] = kelvinToRgb(cct);
  const bNorm = brightness / 100;
  const rgb = `rgb(${Math.round(r * bNorm)}, ${Math.round(g * bNorm)}, ${Math.round(b * bNorm)})`;
  orb.style.background = rgb;
  glow.style.background = rgb;
  glow.style.opacity = 0.4 * bNorm;
  orb.classList.remove("off");
  const brightnessSlider = document.getElementById("slider-brightness");
  if (brightnessSlider) {
    brightnessSlider.style.setProperty("--track-end", rgb);
  }
}

function initSliders() {
  const cctSlider = document.getElementById("slider-cct");
  const brightnessSlider = document.getElementById("slider-brightness");
  const cctValue = document.getElementById("cct-value");
  const brightnessValue = document.getElementById("brightness-value");
  const btnApply = document.getElementById("btn-apply");

  let pendingApply = false;

  function onSliderChange() {
    const cct = parseInt(cctSlider.value, 10);
    const brightness = parseInt(brightnessSlider.value, 10);
    cctValue.textContent = cct + "K";
    brightnessValue.textContent = brightness + "%";
    updateOrbFromSliders(cct, brightness);
    pendingApply = true;
    btnApply.style.display = "block";
  }

  cctSlider?.addEventListener("input", onSliderChange);
  brightnessSlider?.addEventListener("input", onSliderChange);

  btnApply?.addEventListener("click", async () => {
    const cct = parseInt(cctSlider.value, 10);
    const brightness = parseInt(brightnessSlider.value, 10);
    btnApply.textContent = "Applying...";
    try {
      await lightSet(cct, brightness);
      btnApply.textContent = "Applied";
      pendingApply = false;
      setTimeout(() => { btnApply.style.display = "none"; }, 1500);
      loadAndRender();
    } catch (e) {
      btnApply.textContent = "Error";
    }
  });
}

function syncSlidersFromState(light, lastRx) {
  const cct = light?.color_temp ?? lastRx?.color_temp ?? 4000;
  const brightness = light?.brightness ?? lastRx?.brightness ?? 70;
  const cctSlider = document.getElementById("slider-cct");
  const brightnessSlider = document.getElementById("slider-brightness");
  const cctValue = document.getElementById("cct-value");
  const brightnessValue = document.getElementById("brightness-value");
  if (cctSlider) { cctSlider.value = cct; }
  if (brightnessSlider) { brightnessSlider.value = brightness; }
  if (cctValue) { cctValue.textContent = cct + "K"; }
  if (brightnessValue) { brightnessValue.textContent = brightness + "%"; }
}

function renderTimeline(schedule, timeIst) {
  const wrap = document.getElementById("timeline-wrap");
  if (!wrap) return;
  const [h, m] = (timeIst || "00:00").split(":").map(Number);
  const nowMins = (h || 0) * 60 + (m || 0);
  const nowPct = (nowMins / 1440) * 100;

  let nextJob = null;
  let nextMins = 9999;

  const items = (schedule || []).filter((s) => s.time_ist);
  const dots = items.map((s) => {
    const [sh, sm] = (s.time_ist || "00:00").split(":").map(Number);
    const mins = (sh || 0) * 60 + (sm || 0);
    const pct = (mins / 1440) * 100;
    const isPast = mins < nowMins || (mins === 0 && nowMins > 1200);
    if (!isPast && mins < nextMins) {
      nextMins = mins;
      nextJob = s;
    }
    return { ...s, pct, isPast };
  });

  wrap.innerHTML = `
    <div class="timeline-line"></div>
    <div class="timeline-now" style="left: ${nowPct}%"></div>
    ${dots.map((d) => `
      <div class="timeline-dot ${d.isPast ? "past" : ""} ${d === nextJob ? "next" : ""} type-${d.type || "hourly"}"
           style="left: ${d.pct}%"
           title="${d.job || ""}: ${d.desc || ""}"></div>
    `).join("")}
  `;
}

function renderBedtimePanel(data) {
  const bt = data.bedtime_decision || {};
  const rec = bt.recommended ?? "22:45";
  const latest = bt.latest ?? "23:30";
  const pressure = bt.sleep_pressure || "medium";
  const reasoning = bt.reasoning || "";

  const recMins = (() => {
    const [h, m] = rec.split(":").map(Number);
    return (h || 22) * 60 + (m || 45);
  })();
  const wakeMins = 5 * 60 + 45;
  const projectedMins = wakeMins > recMins ? (24 * 60 - recMins) + wakeMins : wakeMins - recMins;
  const projected = `${Math.floor(projectedMins / 60)}h ${projectedMins % 60}m`;

  const recEl = document.getElementById("bedtime-rec");
  const latestEl = document.getElementById("bedtime-latest");
  if (recEl) recEl.textContent = rec;
  if (latestEl) latestEl.textContent = latest;
  document.getElementById("bedtime-projected").textContent = projected;
  document.getElementById("bedtime-reasoning").textContent = reasoning;

  const pressureLevel = { high: 5, medium: 3, low: 1 }[pressure] || 3;
  document.getElementById("sleep-pressure-dots").innerHTML = Array(5)
    .fill(0)
    .map((_, i) => `<span class="dot ${i < pressureLevel ? "filled" : ""}"></span>`)
    .join("");

  const now = new Date();
  const nowMins = now.getHours() * 60 + now.getMinutes();
  const latestMins = (() => {
    const [h, m] = latest.split(":").map(Number);
    return (h || 23) * 60 + (m || 30);
  })();
  const recMinsVal = (() => {
    const [h, m] = rec.split(":").map(Number);
    return (h || 22) * 60 + (m || 45);
  })();

  const panel = document.getElementById("bedtime-panel");
  panel?.classList.remove("overdue", "past-recommended");
  if (nowMins >= latestMins) panel?.classList.add("overdue");
  else if (nowMins >= recMinsVal) panel?.classList.add("past-recommended");
}

function renderMetricRings(today, baselines) {
  const rec = today.recovery_score;
  const wrap = document.getElementById("recovery-ring-wrap");
  if (!wrap) return;
  const pct = rec != null ? rec : 0;
  const color = formatRecoveryColor(rec) === "green" ? "var(--recovery-green)" : formatRecoveryColor(rec) === "yellow" ? "var(--recovery-yellow)" : "var(--recovery-red)";
  const avg = baselines.recovery_mean ?? 50;
  const delta = rec != null && avg != null ? rec - avg : null;
  const deltaStr = delta != null ? (delta >= 0 ? `+${delta}% above avg` : `${delta}% below avg`) : "";

  wrap.innerHTML = `
    <svg width="64" height="64" class="metric-ring">
      <circle cx="32" cy="32" r="28" fill="none" stroke="var(--bg-deep)" stroke-width="4"/>
      <circle cx="32" cy="32" r="28" fill="none" stroke="${color}" stroke-width="4"
              stroke-dasharray="${(pct / 100) * 176} 176" stroke-linecap="round"
              transform="rotate(-90 32 32)" style="transition: stroke-dasharray 0.4s"/>
    </svg>
  `;

  const recCard = document.getElementById("card-recovery");
  recCard?.classList.remove("border-green", "border-yellow", "border-red");
  recCard?.classList.add("border-" + (formatRecoveryColor(rec) || "yellow"));

  const ctxEl = document.getElementById("recovery-context");
  if (ctxEl) ctxEl.textContent = deltaStr || (baselines.recovery_mean != null ? `avg ${Math.round(baselines.recovery_mean)}%` : "—");
}

function renderSparkline(history, field) {
  const vals = (history || []).map((h) => h[field]).filter((v) => v != null);
  if (vals.length < 2) return "";
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const w = 60;
  const h = 24;
  const points = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  }).join(" ");
  return `<svg class="sparkline" viewBox="0 0 ${w} ${h}"><polyline fill="none" stroke="var(--accent)" stroke-width="1" points="${points}"/></svg>`;
}

function renderJobLog(jobs, prevJobCount) {
  const list = document.getElementById("jobs-list");
  if (!list) return;
  const newCount = (jobs || []).length;
  if (newCount > (prevJobCount || 0)) {
    list.classList.add("job-flash");
    setTimeout(() => list.classList.remove("job-flash"), 500);
  }

  const getIcon = (msg) => {
    if (msg.includes("SUNRISE") || msg.includes("ALARM")) return "[W]";
    if (msg.includes("WIND") || msg.includes("DEEP") || msg.includes("EVENING")) return "[S]";
    if (msg.includes("HOURLY") || msg.includes("PLAN")) return "[H]";
    if (msg.includes("CLI_CMD") || msg.includes("BEDTIME")) return "[C]";
    return "·";
  };

  const extractRx = (msg) => {
    const m = msg.match(/(\d{4})K\s*·\s*(\d+)%|→\s*(\d{4})K,\s*(\d+)%/);
    return m ? { k: parseInt(m[1] || m[3], 10), b: parseInt(m[2] || m[4], 10) } : null;
  };

  list.innerHTML = (jobs || []).map((j) => {
    const rx = extractRx(j.message);
    const pill = rx ? `<span class="job-prescription-pill" style="background: rgb(${kelvinToRgb(rx.k).join(",")}); color: #000">${rx.k}K · ${rx.b}%</span>` : "";
    return `<div class="job-entry"><span class="job-time">${j.time}</span><span class="job-msg">${getIcon(j.message)} ${j.message}${pill}</span></div>`;
  }).join("");
  list.scrollTop = list.scrollHeight;
}

function startCountdownTimer() {
  function update() {
    const ctrl = document.getElementById("alarm-countdown");
    if (!ctrl) return;
    const now = new Date();
    const h = now.getHours();
    const m = now.getMinutes();
    const nowMins = h * 60 + m;
    if (nowMins >= 5 * 60 + 30 && nowMins < 5 * 60 + 45) {
      ctrl.textContent = "Sunrise in progress";
    } else if (nowMins >= 5 * 60 + 45 && nowMins < 6 * 60) {
      ctrl.textContent = "Alarm just fired";
    } else {
      let minsToAlarm;
      if (nowMins < 5 * 60 + 30) {
        minsToAlarm = (5 * 60 + 45) - nowMins;
      } else {
        minsToAlarm = (24 * 60 - nowMins) + (5 * 60 + 45);
      }
      const hrs = Math.floor(minsToAlarm / 60);
      const mins = minsToAlarm % 60;
      ctrl.textContent = `Next alarm in ${hrs}h ${mins}m`;
    }
  }
  update();
  setInterval(update, 30000);
}

function renderState(data) {
  const today = data.today || {};
  const baselines = data.baselines || {};
  const light = data.light_state || {};
  const history = data.history || [];

  // Time & date
  document.getElementById("time-badge").textContent = data.time_ist_full || data.time_ist || "—";
  document.getElementById("date-badge").textContent = data.date || "—";
  document.getElementById("profile-name").textContent = data.profile?.name || "—";

  updateConnectionStatus(data.connections);
  const mode = data.last_soma_mode || data.scheduler_mode || computeSchedulerMode();
  const modeEl = document.getElementById("mode-badge");
  if (modeEl) {
    modeEl.textContent = mode;
    modeEl.className = "mode-badge mode-" + String(mode).toLowerCase().replace("_", "-");
  }

  // Mood buttons active state
  const moodOverride = data.mood_override;
  document.querySelectorAll(".mood-btn").forEach((btn) => {
    btn.classList.toggle("mood-active", btn.dataset.mood === moodOverride);
  });

  // Light orb & status
  const orb = document.getElementById("light-orb");
  const glow = document.getElementById("light-orb-glow");
  const statusEl = document.getElementById("status-pill");
  const specEl = document.getElementById("light-spec");

  const lastRx = data.last_prescription || {};
  const colorTemp = light.color_temp || lastRx.color_temp || 4000;
  const brightnessVal = light.brightness ?? lastRx.brightness ?? 50;

  syncSlidersFromState(light, lastRx);

  if (statusEl) {
    statusEl.className = "status-pill ";
    if (light.is_on && data.connections?.light) statusEl.classList.add("status-on");
    else if (!data.connections?.light) statusEl.classList.add("status-error");
    else statusEl.classList.add("status-off");
  }

  if (light.is_on && (light.color_temp || lastRx.color_temp)) {
    const [r, g, b] = kelvinToRgb(colorTemp);
    const brightness = brightnessVal / 100;
    const rgb = `rgb(${Math.round(r * brightness)}, ${Math.round(g * brightness)}, ${Math.round(b * brightness)})`;
    orb.style.background = rgb;
    orb.classList.remove("off");
    glow.style.background = rgb;
    glow.style.opacity = 0.4 * brightness;
    specEl.textContent = `${colorTemp}K · ${brightnessVal}%`;
  } else if (lastRx.color_temp) {
    const [r, g, b] = kelvinToRgb(lastRx.color_temp);
    const brightness = ((lastRx.brightness || 50) / 100) * 0.3;
    const rgb = `rgb(${Math.round(r * brightness)}, ${Math.round(g * brightness)}, ${Math.round(b * brightness)})`;
    orb.style.background = rgb;
    orb.classList.remove("off");
    glow.style.background = rgb;
    glow.style.opacity = 0.15;
    specEl.textContent = `Last: ${lastRx.color_temp}K · ${lastRx.brightness || 50}%`;
  } else {
    orb.style.background = "#2a2a2a";
    orb.classList.add("off");
    glow.style.background = "#2a2a2a";
    glow.style.opacity = 0;
    specEl.textContent = "—";
  }

  // Toggle button
  const btnToggle = document.getElementById("btn-light-toggle");
  if (btnToggle) {
    btnToggle.textContent = light.is_on ? "Turn Off" : "Turn On";
  }

  // Presets
  const h = new Date().getHours();
  const m = new Date().getMinutes();
  const mins = h * 60 + m;
  const presets = [
    { k: 5500, b: 95, range: [9 * 60, 13 * 60] },
    { k: 5000, b: 85, range: [13 * 60, 17 * 60] },
    { k: 3200, b: 55, range: [17 * 60, 20 * 60] },
    { k: 2700, b: 25, range: [20 * 60, 22 * 60] },
    { k: 2500, b: 8, range: [22 * 60, 24 * 60], alt: [0, 5 * 60 + 30] },
  ];
  document.querySelectorAll(".preset-btn").forEach((btn, i) => {
    const p = presets[i];
    if (!p) return;
    const inRange = (mins >= p.range[0] && mins < p.range[1]) || (p.alt && mins >= p.alt[0] && mins < p.alt[1]);
    btn.classList.toggle("preset-active", !!inRange);
  });

  // Metrics
  const rec = today.recovery_score;
  const recCard = document.getElementById("card-recovery");
  recCard?.classList.remove("recovery-yellow", "recovery-red");
  if (rec != null) {
    if (rec >= 66) recCard?.classList.remove("recovery-yellow", "recovery-red");
    else if (rec >= 34) recCard?.classList.add("recovery-yellow");
    else recCard?.classList.add("recovery-red");
  }

  document.getElementById("recovery-value").textContent = fmt(rec, "%");
  renderMetricRings(today, baselines);

  // HRV bar
  const hrv = today.hrv;
  const hrvMean = baselines.hrv_mean ?? 60;
  const hrvStd = baselines.hrv_std ?? 15;
  const hrvMin = Math.max(0, hrvMean - 2 * hrvStd);
  const hrvMax = hrvMean + 2 * hrvStd;
  const hrvBar = document.getElementById("hrv-bar");
  if (hrvBar) {
    const pct = hrv != null && (hrvMax - hrvMin) > 0 ? ((hrv - hrvMin) / (hrvMax - hrvMin)) * 100 : 50;
    const dotColor = hrv != null ? (hrv >= hrvMean ? "var(--recovery-green)" : hrv >= hrvMean - hrvStd ? "var(--recovery-yellow)" : "var(--recovery-red)") : "var(--text-muted)";
    hrvBar.innerHTML = `<div class="dot" style="left: ${Math.max(0, Math.min(100, pct))}%; transform: translate(-50%, -50%); background: ${dotColor}"></div>`;
  }
  document.getElementById("hrv-value").textContent = fmt(hrv, "ms");
  document.getElementById("hrv-context").textContent = baselines.hrv_mean != null ? `avg ${Math.round(baselines.hrv_mean)}ms` : "—";

  const sleepPerf = today.sleep_performance;
  const sleepHrs = today.sleep_duration_hrs;
  const remHrs = today.rem_hrs;
  const deepHrs = today.deep_hrs;
  const lightHrs = sleepHrs != null && remHrs != null && deepHrs != null ? Math.max(0, (sleepHrs || 0) - remHrs - deepHrs) : 0;
  const stagesEl = document.getElementById("sleep-stages");
  if (stagesEl && remHrs != null && deepHrs != null) {
    const total = remHrs + deepHrs + (lightHrs || 0);
    if (total > 0) {
      stagesEl.innerHTML = `
        <span class="stage stage-rem" style="flex: ${remHrs / total}"></span>
        <span class="stage stage-deep" style="flex: ${deepHrs / total}"></span>
        <span class="stage stage-light" style="flex: ${(lightHrs || 0) / total}"></span>
      `;
    } else stagesEl.innerHTML = "";
  } else if (stagesEl) stagesEl.innerHTML = "";
  document.getElementById("sleep-value").textContent = sleepPerf != null ? `${sleepPerf}%` : (sleepHrs != null ? `${sleepHrs}h` : "—");
  document.getElementById("sleep-context").textContent = baselines.sleep_mean != null ? `avg ${baselines.sleep_mean}h` : "—";

  const strain = today.day_strain;
  const strainGauge = document.getElementById("strain-gauge");
  if (strainGauge && strain != null) {
    const pct = Math.min(100, (strain / 21) * 100);
    strainGauge.innerHTML = `<div style="position:absolute;bottom:0;left:0;right:${100 - pct}%;height:4px;background:var(--text);border-radius:2px"></div>`;
  }
  document.getElementById("strain-value").textContent = fmt(strain);
  document.getElementById("strain-context").textContent = baselines.avg_strain != null ? `avg ${baselines.avg_strain.toFixed(1)}` : "—";

  document.getElementById("rhr-value").textContent = fmt(today.resting_hr, "bpm");
  document.getElementById("rhr-context").textContent = baselines.rhr_mean != null ? `avg ${Math.round(baselines.rhr_mean)}bpm` : "—";

  // Baselines
  document.getElementById("baseline-hrv").textContent = baselines.hrv_mean != null ? `${Math.round(baselines.hrv_mean)}ms` : "—";
  document.getElementById("baseline-recovery").textContent = baselines.recovery_mean != null ? `${Math.round(baselines.recovery_mean)}%` : "—";
  document.getElementById("baseline-sleep").textContent = baselines.sleep_mean != null ? `${baselines.sleep_mean}h` : "—";
  document.getElementById("baseline-strain").textContent = baselines.avg_strain != null ? baselines.avg_strain.toFixed(1) : "—";

  // Weather & plan
  const weather = data.weather || {};
  const wParts = [];
  if (weather.temp_c != null) wParts.push(`${weather.temp_c}°C`);
  if (weather.condition) wParts.push(weather.condition);
  document.getElementById("weather-value").textContent = wParts.length ? wParts.join(" · ") : "—";
  document.getElementById("plan-value").textContent = data.plan || "—";

  // Timeline
  renderTimeline(data.schedule, data.time_ist);

  // Schedule (fallback if API returns empty)
  const schedule = data.schedule && data.schedule.length > 0 ? data.schedule : [
    { time: "05:30", time_ist: "05:30", job: "Sunrise start", desc: "2500K, 1%", type: "wake" },
    { time: "05:45", time_ist: "05:45", job: "Alarm pulse", desc: "3 flashes", type: "alarm" },
    { time: "20:00", time_ist: "20:00", job: "Evening start", desc: "Wind-down", type: "winddown" },
    { time: "22:00", time_ist: "22:00", job: "Deep wind-down", desc: "2500K, 10%", type: "winddown" },
    { time: "22:30", time_ist: "22:30", job: "Bedtime decision", desc: "AI recommends", type: "bedtime" },
  ];
  const scheduleList = document.getElementById("schedule-list");
  if (scheduleList) {
    scheduleList.innerHTML = schedule
      .map((s) => `<div class="schedule-item"><span class="schedule-time">${s.time || ""}</span><div><span class="schedule-job">${s.job || ""}</span><div class="schedule-desc">${s.desc || ""}</div></div></div>`)
      .join("");
  }

  // Bedtime
  renderBedtimePanel(data);

  // Alarm
  const alarm = data.alarm || {};
  document.getElementById("alarm-time").textContent = alarm.time || "05:45 IST";
  const hold = alarm.hold_by_recovery || {};
  document.getElementById("alarm-hold").innerHTML = Object.entries(hold)
    .map(([k, v]) => `<div class="alarm-hold-item"><span>${k}</span><span>${v}</span></div>`)
    .join("");

  const rampSteps = [
    [2500, 1], [2700, 10], [3000, 25], [3500, 40], [4000, 55], [4500, 70], [5000, 85], [5500, 95],
  ];
  document.getElementById("sunrise-ramp").innerHTML = rampSteps
    .map(([k, b]) => `${k}K ${b}%`)
    .map((label, i) => `<span class="step" title="${label}" style="background: rgb(${kelvinToRgb(rampSteps[i][0]).join(",")})"></span>`)
    .join("");

  // Recent jobs
  renderJobLog(data.recent_jobs, window._lastJobCount);
  window._lastJobCount = (data.recent_jobs || []).length;

  // History
  const tbody = document.getElementById("history-table-body");
  const todayStr = data.date || "";
  tbody.innerHTML = history.map((r, idx) => {
    const recVal = r.recovery_score;
    const recClass = recVal != null ? (recVal >= 66 ? "recovery-green" : recVal >= 34 ? "recovery-yellow" : "recovery-red") : "";
    const hrvVal = r.hrv;
    const hrvClass = hrvVal != null && baselines.hrv_mean != null ? (hrvVal >= baselines.hrv_mean ? "recovery-green" : "recovery-red") : "";
    const sleepVal = r.sleep_duration_hrs ?? r.sleep_performance;
    const sleepClass = sleepVal != null && baselines.sleep_mean != null ? (sleepVal >= baselines.sleep_mean ? "recovery-green" : "recovery-red") : "";
    const strainVal = r.day_strain;
    const strainClass = strainVal != null ? (strainVal < 8 ? "recovery-green" : strainVal < 14 ? "recovery-yellow" : "recovery-red") : "";
    const spark = renderSparkline(history.slice(idx, idx + 14), "recovery_score");
    const isToday = r.date === todayStr;
    return `<tr class="${isToday ? "today-row" : ""}">
      <td>${r.date || "—"}</td>
      <td class="${recClass}">${fmt(recVal, "%")}</td>
      <td class="${hrvClass}">${fmt(hrvVal, "ms")}</td>
      <td class="${sleepClass}">${fmt(r.sleep_performance, "%")}</td>
      <td class="${strainClass}">${strainVal != null ? strainVal.toFixed(1) : "—"}</td>
      <td>${spark}</td>
    </tr>`;
  }).join("");
}

async function loadAndRender() {
  try {
    const data = await fetchState();
    renderState(data);
    document.body.classList.remove("api-error");
  } catch (e) {
    console.error("Failed to load state:", e);
    document.body.classList.add("api-error");
    showConnectionError();
  }
}

function showConnectionError() {
  const msg = "Could not connect to API. Run the server: ./run_dashboard.sh";
  const existing = document.getElementById("api-error-banner");
  if (existing) return;
  const banner = document.createElement("div");
  banner.id = "api-error-banner";
  banner.style.cssText = "position:fixed;top:0;left:0;right:0;background:#ef4444;color:white;padding:0.5rem 1rem;text-align:center;z-index:9999;font-size:0.9rem";
  banner.textContent = msg;
  document.body.prepend(banner);
}

async function handleSend() {
  const input = document.getElementById("command-input");
  const replyEl = document.getElementById("command-reply");
  const msg = input.value.trim();
  if (!msg) return;

  replyEl.textContent = "Thinking...";
  input.disabled = true;
  document.getElementById("btn-send").disabled = true;

  try {
    const result = await sendCommand(msg);
    replyEl.textContent = result.reply || (result.command_executed ? "Done." : "No action taken.");
    input.value = "";
    await new Promise((r) => setTimeout(r, 500));
    await loadAndRender();
  } catch (e) {
    replyEl.textContent = `Error: ${e.message}`;
  } finally {
    input.disabled = false;
    document.getElementById("btn-send").disabled = false;
  }
}

function init() {
  initSliders();
  startCountdownTimer();

  loadAndRender();

  document.getElementById("btn-refresh").addEventListener("click", async () => {
    try {
      await refresh();
      await loadAndRender();
    } catch (e) {
      console.error(e);
    }
  });

  document.getElementById("btn-send").addEventListener("click", handleSend);
  document.getElementById("command-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleSend();
  });

  document.getElementById("btn-light-refresh").addEventListener("click", () => loadAndRender());

  document.getElementById("btn-light-toggle").addEventListener("click", async () => {
    try {
      const data = await fetchState();
      if (data.light_state?.is_on) {
        await lightOff();
      } else {
        await lightOn();
      }
      await loadAndRender();
    } catch (e) {
      console.error(e);
    }
  });

  document.querySelectorAll(".preset-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const k = parseInt(btn.dataset.k, 10);
      const b = parseInt(btn.dataset.b, 10);
      try {
        await lightSet(k, b);
        await loadAndRender();
      } catch (e) {
        console.error(e);
      }
    });
  });

  document.querySelectorAll(".mood-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const mood = btn.dataset.mood;
      if (!mood) return;
      try {
        await setMood(mood);
        await loadAndRender();
        document.querySelectorAll(".mood-btn").forEach((b) => b.classList.remove("mood-active"));
        btn.classList.add("mood-active");
      } catch (e) {
        console.error(e);
      }
    });
  });

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const msg = chip.dataset.msg;
      if (msg) {
        document.getElementById("command-input").value = msg;
        handleSend();
      }
    });
  });

  document.getElementById("btn-bedtime-signal").addEventListener("click", async () => {
    try {
      await bedtimeSignal();
      await loadAndRender();
    } catch (e) {
      console.error(e);
    }
  });

  setInterval(loadAndRender, 10000);
}

init();
