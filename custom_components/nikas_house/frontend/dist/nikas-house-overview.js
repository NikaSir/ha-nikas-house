const ELEMENT_NAME = "nikas-house-main-hero";
const DEFAULT_ASSET = "/nikas_house/frontend/assets/house-hero-photo-day-v3.webp?build=v1_0_0_b001";
const GLOBAL_TABBAR_ID = "nikas-house-global-tabbar";
// Verified by the irrigation panel owner as the incoming mainline pressure source.
const IRRIGATION_PRESSURE_ENTITY = "sensor.nikas_h2000_pro_voda_na_poliv_2";
const BAD_STATES = new Set(["unknown", "unavailable", "none", "null", ""]);

const WEATHER_LABELS = {
  sunny: "Ясно",
  "clear-night": "Ясно",
  partlycloudy: "Переменная облачность",
  cloudy: "Облачно",
  rainy: "Дождь",
  pouring: "Ливень",
  snowy: "Снег",
  fog: "Туман",
  windy: "Ветрено",
  lightning: "Гроза",
  "lightning-rainy": "Гроза с дождём",
};

const WEATHER_ICONS = {
  sunny: "mdi:weather-sunny",
  "clear-night": "mdi:weather-night",
  partlycloudy: "mdi:weather-partly-cloudy",
  cloudy: "mdi:weather-cloudy",
  rainy: "mdi:weather-rainy",
  pouring: "mdi:weather-pouring",
  snowy: "mdi:weather-snowy",
  fog: "mdi:weather-fog",
  windy: "mdi:weather-windy",
  lightning: "mdi:weather-lightning",
  "lightning-rainy": "mdi:weather-lightning-rainy",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function numeric(value) {
  const parsed = Number.parseFloat(String(value ?? "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

function sameTreeShape(current, desired) {
  if (!current || !desired || current.nodeType !== desired.nodeType) return false;
  if (current.nodeType === Node.ELEMENT_NODE && current.tagName !== desired.tagName) return false;
  if (current.childNodes.length !== desired.childNodes.length) return false;
  for (let index = 0; index < current.childNodes.length; index += 1) {
    if (!sameTreeShape(current.childNodes[index], desired.childNodes[index])) return false;
  }
  return true;
}

function syncTree(current, desired) {
  if (current.nodeType === Node.TEXT_NODE || current.nodeType === Node.COMMENT_NODE) {
    if (current.nodeValue !== desired.nodeValue) current.nodeValue = desired.nodeValue;
    return;
  }
  if (current.nodeType === Node.ELEMENT_NODE) {
    for (const attribute of [...current.attributes]) {
      if (!desired.hasAttribute(attribute.name)) current.removeAttribute(attribute.name);
    }
    for (const attribute of [...desired.attributes]) {
      if (current.getAttribute(attribute.name) !== attribute.value) {
        current.setAttribute(attribute.name, attribute.value);
      }
    }
  }
  for (let index = 0; index < current.childNodes.length; index += 1) {
    syncTree(current.childNodes[index], desired.childNodes[index]);
  }
}

function commitStableMarkup(root, markup) {
  if (typeof document === "undefined" || typeof document.createElement !== "function" || typeof Node === "undefined") {
    root.innerHTML = markup;
    return true;
  }
  const template = document.createElement("template");
  template.innerHTML = markup;
  const current = [...root.childNodes];
  const desired = [...template.content.childNodes];
  const compatible = current.length === desired.length && current.every((node, index) => sameTreeShape(node, desired[index]));
  if (!compatible) {
    root.replaceChildren(template.content.cloneNode(true));
    return true;
  }
  current.forEach((node, index) => syncTree(node, desired[index]));
  return false;
}

class NikasHouseHero extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
    this._timer = null;
    this._fitFrame = null;
    this._boundViewportFit = () => this._scheduleViewportFit();
  }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("nikas-house-main-hero requires a config object");
    this._config = config;
    this.toggleAttribute("standalone", config.standalone === true);
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() { return 9; }

  connectedCallback() {
    if (!this._timer) this._timer = window.setInterval(() => this._render(), 60_000);
    window.addEventListener?.("resize", this._boundViewportFit, { passive: true });
    window.visualViewport?.addEventListener?.("resize", this._boundViewportFit, { passive: true });
    this._scheduleViewportFit();
  }

  disconnectedCallback() {
    if (this._timer) window.clearInterval(this._timer);
    this._timer = null;
    window.removeEventListener?.("resize", this._boundViewportFit);
    window.visualViewport?.removeEventListener?.("resize", this._boundViewportFit);
    if (this._fitFrame !== null) {
      (window.cancelAnimationFrame || window.clearTimeout)(this._fitFrame);
      this._fitFrame = null;
    }
  }

  _scheduleViewportFit() {
    if (!this.isConnected || typeof document === "undefined") return;
    if (this._fitFrame !== null) {
      (window.cancelAnimationFrame || window.clearTimeout)(this._fitFrame);
    }
    const schedule = window.requestAnimationFrame || ((callback) => window.setTimeout(callback, 0));
    this._fitFrame = schedule(() => {
      this._fitFrame = null;
      this._fitViewport();
    });
  }

  _fitViewport() {
    if (this._config?.standalone === true) return;
    const hero = this.shadowRoot?.querySelector(".hero");
    const tabBar = document.getElementById(GLOBAL_TABBAR_ID);
    if (!hero || !tabBar || typeof hero.getBoundingClientRect !== "function" || typeof tabBar.getBoundingClientRect !== "function") {
      return;
    }
    const top = hero.getBoundingClientRect().top;
    const bottom = tabBar.getBoundingClientRect().top;
    const available = Math.floor(bottom - top);
    if (!Number.isFinite(available) || available <= 0) return;
    const value = `${available}px`;
    if (this.style.getPropertyValue("--house-hero-available-height") !== value) {
      this.style.setProperty("--house-hero-available-height", value);
    }
  }

  _entity(id) { return id && this._hass?.states?.[id] ? this._hass.states[id] : null; }
  _state(id) { return this._entity(id)?.state ?? "unknown"; }
  _available(id) { return !BAD_STATES.has(String(this._state(id)).toLowerCase()); }
  _countOn(ids) { return (Array.isArray(ids) ? ids : []).filter((id) => this._state(id) === "on").length; }
  _countUnavailable(ids) { return (Array.isArray(ids) ? ids : []).filter((id) => !this._available(id)).length; }

  _climate(ids) {
    const source = Array.isArray(ids) ? ids : [];
    let active = 0;
    let unavailable = 0;
    let resolved = 0;
    for (const id of source) {
      const entity = this._entity(id);
      if (!entity) continue;
      resolved += 1;
      const state = String(entity.state ?? "").toLowerCase();
      if (state === "unknown" || state === "unavailable") {
        unavailable += 1;
        continue;
      }
      if (["heating", "cooling"].includes(entity.attributes?.hvac_action)) active += 1;
    }
    const tone = unavailable > 0 ? "orange" : active > 0 ? "yellow" : resolved > 0 ? "green" : "grey";
    return { active, unavailable, missing: source.length - resolved, tone, value: resolved > 0 ? String(active) : "—" };
  }

  _security(ids) {
    const alarm = this._countOn(ids);
    const bad = this._countUnavailable(ids);
    if (alarm > 0) return { label: `Тревога ${alarm}`, tone: "red", icon: "mdi:shield-alert" };
    if (bad > 0) return { label: "Внимание", tone: "orange", icon: "mdi:shield-alert-outline" };
    return { label: "В норме", tone: "green", icon: "mdi:shield-check" };
  }

  _power(ids) {
    const values = (Array.isArray(ids) ? ids : []).map((id) => numeric(this._state(id)));
    if (values.length !== 3 || values.some((value) => value === null)) {
      return { label: "Нет данных", tone: "grey", detail: "Фазы недоступны", icon: "mdi:home-lightning-bolt-outline" };
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    // These three phases are measured before the LIDER PS7500W-30
    // stabilizers. Evaluate them against the stabilizer passport, not the
    // downstream ГОСТ voltage-quality policy.
    let label = "В норме";
    let tone = "green";
    if (min < 125 || max > 275) { label = "Авария"; tone = "red"; }
    else if (min < 150 || max > 265) { label = "Рабочий предел"; tone = "orange"; }
    return { label, tone, detail: `${min.toFixed(0)}–${max.toFixed(0)} В`, icon: "mdi:home-lightning-bolt" };
  }

  _irrigationPressureEntity() {
    const states = this._hass?.states ?? {};
    if (states[IRRIGATION_PRESSURE_ENTITY]) return states[IRRIGATION_PRESSURE_ENTITY];
    return Object.entries(states).find(([entityId, entity]) => {
      if (!entityId.startsWith("sensor.")) return false;
      const text = `${entityId} ${entity?.attributes?.friendly_name ?? ""}`.toLowerCase();
      const unit = String(entity?.attributes?.unit_of_measurement ?? "").toLowerCase();
      const irrigation = text.includes("voda_na_poliv") || text.includes("вода на полив")
        || ((text.includes("давлен") || text.includes("pressure")) && (text.includes("полив") || text.includes("irrig")));
      return irrigation && (unit === "bar" || unit === "бар");
    })?.[1] ?? null;
  }

  _water() {
    const entity = this._irrigationPressureEntity();
    const value = numeric(entity?.state);
    if (value === null) return { label: "Нет данных", tone: "grey", detail: "Давление неизвестно", icon: "mdi:water-alert-outline" };
    const detail = `${value.toFixed(2).replace(".", ",")} бар`;
    if (value <= 0) return { label: "Нет воды", tone: "red", detail, icon: "mdi:water-alert" };
    return { label: "Есть", tone: "green", detail, icon: "mdi:water" };
  }

  _internet(id) {
    const state = this._state(id);
    if (state === "on") return { label: "Доступен", tone: "green", detail: "", icon: "mdi:web" };
    if (state === "off") return { label: "Нет связи", tone: "red", detail: "Проверить WAN", icon: "mdi:web-off" };
    return { label: "Нет данных", tone: "grey", detail: "Статус неизвестен", icon: "mdi:web-off" };
  }

  _heating(cfg) {
    if (!cfg || typeof cfg !== "object") return { label: "Нет данных", tone: "grey", detail: "", icon: "mdi:radiator-disabled" };
    const main = this._state(cfg.main);
    const reserve = this._state(cfg.reserve);
    const circuits = [cfg.radiators, cfg.floor, cfg.circulation].filter(Boolean);
    const active = this._countOn(circuits);
    const bad = this._countUnavailable(circuits);
    const mainTemp = numeric(this._state(cfg.main_temp));
    const reserveTemp = numeric(this._state(cfg.reserve_temp));
    if (main === "on") return { label: "Активно", tone: "orange", detail: `Основной${mainTemp === null ? "" : ` · ${mainTemp.toFixed(0)} °C`}`, icon: "mdi:radiator" };
    if (reserve === "on") return { label: "Активно", tone: "orange", detail: `Резервный${reserveTemp === null ? "" : ` · ${reserveTemp.toFixed(0)} °C`}`, icon: "mdi:radiator" };
    if (active > 0) return { label: "Активно", tone: "orange", detail: "Контуры активны", icon: "mdi:radiator" };
    if (BAD_STATES.has(String(main).toLowerCase()) || BAD_STATES.has(String(reserve).toLowerCase()) || bad > 0) {
      return { label: "Нет данных", tone: "grey", detail: "Проверить отопление", icon: "mdi:radiator-disabled" };
    }
    return { label: "Ожидание", tone: "green", detail: "", icon: "mdi:radiator" };
  }

  _weather(id) {
    const entity = this._entity(id);
    if (!entity || BAD_STATES.has(String(entity.state).toLowerCase())) return { label: "Погода", detail: "Нет данных", icon: "mdi:weather-cloudy", tone: "grey" };
    const temperature = numeric(entity.attributes?.temperature);
    return {
      label: temperature === null ? WEATHER_LABELS[entity.state] ?? entity.state : `${temperature.toFixed(1)}°`,
      detail: WEATHER_LABELS[entity.state] ?? entity.state,
      icon: WEATHER_ICONS[entity.state] ?? "mdi:weather-partly-cloudy",
      tone: "blue",
    };
  }

  _camera(ids) {
    const total = Array.isArray(ids) ? ids.length : 0;
    const ok = (Array.isArray(ids) ? ids : []).filter((id) => this._available(id)).length;
    if (total === 0) return { label: "Камеры", detail: "Нет данных", tone: "grey", icon: "mdi:cctv-off" };
    return { label: `Камеры ${ok}/${total}`, detail: ok === total ? "Онлайн" : "Проверить", tone: ok === total ? "green" : ok > 0 ? "orange" : "red", icon: "mdi:cctv" };
  }

  _access(id, label, kind = "door") {
    const state = this._state(id);
    const openIcon = kind === "gate" ? "mdi:garage-open" : "mdi:door-open";
    const closedIcon = kind === "gate" ? "mdi:garage" : "mdi:door-closed";
    if (state === "on") return { label, detail: "Открыто", tone: "yellow", icon: openIcon };
    if (state === "off") return { label, detail: "Закрыто", tone: "green", icon: closedIcon };
    return { label, detail: "Нет данных", tone: "grey", icon: kind === "gate" ? "mdi:garage-alert" : "mdi:door-alert" };
  }

  _navigate(path) {
    if (!path || !String(path).startsWith("/")) return;
    window.NikasHouseNavigation?.navigate?.(path);
  }

  _bindRoutes() {
    this.shadowRoot?.querySelectorAll("[data-route]").forEach((node) => {
      if (node._nikasRouteBound) return;
      node._nikasRouteBound = true;
      node.addEventListener("click", () => this._navigate(node.dataset.route));
      node.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          this._navigate(node.dataset.route);
        }
      });
    });
  }

  _card(icon, title, value, tone, route, extra = "") {
    return `<button class="status-card ${tone}" data-route="${escapeHtml(route)}" type="button">
      <ha-icon icon="${escapeHtml(icon)}"></ha-icon>
      <span class="status-copy"><small>${escapeHtml(title)}</small><strong>${escapeHtml(value)}</strong><em${extra ? "" : " hidden"}>${escapeHtml(extra)}</em></span>
    </button>`;
  }

  _utility(title, tone, route) {
    return `<button class="utility-card ${tone}" data-route="${escapeHtml(route)}" type="button"><strong>${escapeHtml(title)}</strong></button>`;
  }

  _render() {
    if (!this._config || !this.shadowRoot) return;
    if (!this._hass) {
      if (!this.shadowRoot.firstChild) {
        this.shadowRoot.innerHTML = `<ha-card><div style="padding:24px;font-size:16px">Дом сейчас · загрузка…</div></ha-card>`;
      }
      return;
    }

    const entities = this._config.entities ?? {};
    const routes = this._config.routes ?? {};
    const accessRoute = routes.access || routes.open;
    const asset = this._config.asset || DEFAULT_ASSET;
    const security = this._security(entities.safety);
    const motion = this._countOn(entities.motion);
    const motionBad = this._countUnavailable(entities.motion);
    const lights = this._countOn(entities.lights);
    const lightBad = this._countUnavailable(entities.lights);
    const climate = this._climate(entities.climate);
    const windows = this._countOn(entities.windows);
    const windowBad = this._countUnavailable(entities.windows);
    const doors = this._countOn(entities.doors);
    const doorBad = this._countUnavailable(entities.doors);
    const gate = this._access(entities.access?.sectional, "Ворота", "gate");
    const entrance = this._access(entities.access?.entrance, "Входная");
    const weather = this._weather(entities.weather);
    const cameras = this._camera(entities.cameras);
    const power = this._power(entities.power);
    const water = this._water();
    const internet = this._internet(entities.internet);
    const heating = this._heating(entities.heating);

    const motionTone = motionBad > 0 ? "orange" : motion > 0 ? "yellow" : "green";
    const lightsTone = lightBad > 0 ? "orange" : lights > 0 ? "yellow" : "green";
    const windowTone = windows > 0 ? "yellow" : windowBad > 0 ? "orange" : "green";
    const doorTone = doors > 0 ? "yellow" : doorBad > 0 ? "orange" : "green";
    const now = new Date();
    const time = now.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
    const date = now.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });

    const markup = `<style>
      :host{display:block;--green:#2ebd59;--yellow:#ffbf00;--orange:#f28b00;--red:#e53935;--blue:#209cee;--grey:#85929b;--ink:#15202b;--muted:#4f5d69}
      ha-card{overflow:hidden;border-radius:28px;background:#edf8ff;border:1px solid rgba(255,255,255,.9);box-shadow:0 16px 40px rgba(41,82,110,.14)}
      .hero{position:relative;height:760px;min-height:calc(100svh - 166px);max-height:850px;overflow:hidden;background:linear-gradient(180deg,rgba(255,255,255,.16),rgba(255,255,255,0) 30%,rgba(255,255,255,.06) 76%,rgba(235,248,255,.18)),url("${escapeHtml(asset)}") center 50%/cover no-repeat;color:var(--ink);font-family:var(--paper-font-body1_-_font-family,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif)}
      .hero::after{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(90deg,rgba(255,255,255,.07),transparent 22%,transparent 78%,rgba(255,255,255,.07))}
      button{font:inherit;color:inherit}
      .top-grid{position:absolute;z-index:4;left:12px;right:12px;top:12px;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}
      .status-card,.float-card,.utility-card,.callout{border:1px solid rgba(255,255,255,.88);background:rgba(255,255,255,.86);backdrop-filter:blur(15px);-webkit-backdrop-filter:blur(15px);box-shadow:0 8px 24px rgba(64,91,108,.15)}
      .status-card{min-width:0;height:74px;padding:9px 8px;border-radius:18px;display:flex;gap:7px;align-items:center;cursor:pointer;text-align:left;appearance:none}
      [hidden]{display:none!important}.status-card ha-icon{width:24px;flex:0 0 24px}.status-copy{min-width:0;display:flex;flex-direction:column;line-height:1.1}.status-copy small{font-size:12px;font-weight:750;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.status-copy strong{margin-top:5px;font-size:15px;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.status-copy em{margin-top:4px;font-size:12px;font-style:normal;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .green ha-icon,.green strong{color:var(--green)}.yellow ha-icon,.yellow strong{color:var(--yellow)}.orange ha-icon,.orange strong{color:var(--orange)}.red ha-icon,.red strong{color:var(--red)}.blue ha-icon,.blue strong{color:var(--blue)}.grey ha-icon,.grey strong{color:var(--grey)}
      .info-grid{position:absolute;z-index:4;left:12px;right:12px;top:102px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
      .info-card{min-width:0;min-height:66px;border-radius:20px;padding:10px 14px;display:flex;align-items:center;gap:10px;text-align:left;appearance:none}.info-card[data-route]{cursor:pointer}.info-card ha-icon{--mdc-icon-size:25px;width:25px;height:25px;flex:0 0 25px}.info-copy{min-width:0;display:flex;flex-direction:column;line-height:1.12}.info-copy small{font-size:12px;font-weight:750;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.info-copy strong{margin-top:4px;font-size:20px;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.info-copy em{margin-top:3px;font-size:12px;font-style:normal;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .zones{position:absolute;z-index:2;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible}.zone{fill:none;stroke:var(--green);stroke-width:4;vector-effect:non-scaling-stroke;filter:drop-shadow(0 0 7px rgba(46,189,89,.34))}.zone.yellow{stroke:var(--yellow);filter:drop-shadow(0 0 7px rgba(255,191,0,.42))}.zone.orange{stroke:var(--orange);filter:drop-shadow(0 0 7px rgba(242,139,0,.42))}.zone.red{stroke:var(--red);filter:drop-shadow(0 0 7px rgba(229,57,53,.4))}.zone.grey{stroke:rgba(122,137,148,.6);filter:none}
      .callout{position:absolute;z-index:4;border-radius:17px;padding:9px 12px;cursor:pointer;min-width:108px;appearance:none}.callout b{display:block;font-size:13px;color:var(--ink)}.callout span{display:block;margin-top:3px;font-size:12px;font-weight:800}.window-callout{left:7%;top:39%}.gate-callout{left:4%;top:59%}.door-callout{right:5%;top:56%}
      .utilities{position:absolute;z-index:4;left:12px;right:12px;bottom:12px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.utility-card{border-radius:17px;padding:8px 10px;min-height:50px;cursor:pointer;appearance:none;display:grid;place-items:center;text-align:center}.utility-card strong{min-width:0;max-width:100%;font-size:17px;font-weight:850;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      [data-route]:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
      @media(max-width:600px){
        ha-card{border-radius:22px}.hero{height:var(--house-hero-available-height,calc(100dvh - 224px));min-height:0;max-height:none;background-size:cover;background-position:center 50%}
        .top-grid{gap:5px;left:8px;right:8px;top:8px}.status-card{height:68px;padding:5px 3px;gap:2px;border-radius:14px;flex-direction:column;justify-content:center;text-align:center}.status-card ha-icon{width:20px;flex:0 0 20px}.status-copy{width:100%;align-items:center}.status-copy small{font-size:12px}.status-copy strong{margin-top:2px;font-size:14px}.status-copy em{display:none}
        .info-grid{left:8px;right:8px;top:84px;gap:6px}.info-card{min-height:58px;padding:7px 9px;gap:7px;border-radius:15px}.info-card ha-icon{--mdc-icon-size:21px;width:21px;height:21px;flex-basis:21px}.info-copy small{font-size:12px}.info-copy strong{font-size:17px}.info-copy em{font-size:12px}
        .window-callout{left:5%;top:38%}.gate-callout{left:3%;top:57%}.door-callout{right:3%;top:55%}.callout{min-width:92px;padding:7px 8px}.callout b{font-size:12px}.callout span{font-size:12px}
        .utilities{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;left:8px;right:8px;bottom:8px}.utility-card{min-height:48px;padding:7px 8px}.utility-card strong{font-size:16px}
      }
      :host([standalone]){height:100%;min-height:0}
      :host([standalone]) ha-card,:host([standalone]) .hero{height:100%;min-height:0;max-height:none}
    </style>
    <ha-card><div class="hero" aria-label="${escapeHtml(this._config.title || "Дом сейчас")}">
      <div class="top-grid">
        ${this._card("mdi:window-open-variant","Окна",String(windows),windowTone,routes.open)}
        ${this._card("mdi:door-open","Двери",String(doors),doorTone,accessRoute)}
        ${this._card("mdi:lightbulb-group","Свет",String(lights),lightsTone,routes.lights)}
        ${this._card("mdi:motion-sensor","Движение",String(motion),motionTone,routes.activity)}
        ${this._card("mdi:thermostat","Климат",climate.value,climate.tone,routes.climate)}
      </div>
      <div class="info-grid">
        <button class="info-card float-card ${weather.tone}" data-route="${escapeHtml(routes.weather)}" type="button"><ha-icon icon="${escapeHtml(weather.icon)}"></ha-icon><span class="info-copy"><small>Погода</small><strong>${escapeHtml(weather.label)}</strong><em>${escapeHtml(weather.detail)}</em></span></button>
        <button class="info-card float-card ${security.tone}" data-route="${escapeHtml(routes.safety)}" type="button"><ha-icon icon="${escapeHtml(security.icon)}"></ha-icon><span class="info-copy"><small>Защита</small><strong>${escapeHtml(security.label)}</strong><em>Состояние дома</em></span></button>
        <div class="info-card float-card blue"><ha-icon icon="mdi:calendar-clock"></ha-icon><span class="info-copy"><small>Дата и время</small><strong>${escapeHtml(time)}</strong><em>${escapeHtml(date)}</em></span></div>
        <button class="info-card float-card ${cameras.tone}" data-route="${escapeHtml(routes.cameras)}" type="button"><ha-icon icon="${escapeHtml(cameras.icon)}"></ha-icon><span class="info-copy"><small>Камеры</small><strong>${escapeHtml(cameras.label)}</strong><em>${escapeHtml(cameras.detail)}</em></span></button>
      </div>
      <svg class="zones" viewBox="0 0 1024 1536" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <rect class="zone ${windowTone}" x="182" y="738" width="170" height="158" rx="14"></rect>
        <rect class="zone ${gate.tone}" x="112" y="986" width="260" height="188" rx="14"></rect>
        <rect class="zone ${entrance.tone}" x="724" y="974" width="128" height="200" rx="14"></rect>
      </svg>
      <button class="callout window-callout ${windowTone}" data-route="${escapeHtml(routes.open)}" type="button"><b>Окна</b><span>${escapeHtml(windows)} открыто</span></button>
      <button class="callout gate-callout ${gate.tone}" data-route="${escapeHtml(accessRoute)}" type="button"><b>${escapeHtml(gate.label)}</b><span>${escapeHtml(gate.detail)}</span></button>
      <button class="callout door-callout ${entrance.tone}" data-route="${escapeHtml(accessRoute)}" type="button"><b>${escapeHtml(entrance.label)}</b><span>${escapeHtml(entrance.detail)}</span></button>
      <div class="utilities">
        ${this._utility("Электросеть",power.tone,routes.electricity)}
        ${this._utility("Вода",water.tone,routes.water)}
        ${this._utility("Интернет",internet.tone,routes.network)}
        ${this._utility("Отопление",heating.tone,routes.heating)}
      </div>
    </div></ha-card>`;
    commitStableMarkup(this.shadowRoot, markup);
    // Stable state updates deliberately preserve the existing DOM tree. Route
    // handlers must therefore be reconciled independently from DOM replacement.
    // _bindRoutes is idempotent and only attaches listeners to unbound nodes.
    this._bindRoutes();
    this._scheduleViewportFit();
  }
}

if (!customElements.get(ELEMENT_NAME)) customElements.define(ELEMENT_NAME, NikasHouseHero);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === ELEMENT_NAME)) {
  window.customCards.push({ type: ELEMENT_NAME, name: "NikaS House Visual State Scene", description: "Daytime visual state scene for the NikaS Home dashboard.", preview: false });
}

(() => {
  const ELEMENT_NAME = "nikas-house-panel";
  const UI_VERSION = "1.0.0";
  if (customElements.get(ELEMENT_NAME)) return;

  const MIN_SCALE = 0.75;
  const MAX_SCALE = 2.0;
  const PAN_THRESHOLD = 6;
  const TAP_DURATION = 300;
  const DOUBLE_TAP_GAP = 420;
  const CLICK_GUARD = 460;

  function navigate(path) {
    window.NikasHouseNavigation?.navigate?.(path);
  }

  function distance(left, right) {
    return Math.hypot(right.clientX - left.clientX, right.clientY - left.clientY);
  }

  function midpoint(left, right) {
    return {
      clientX: (left.clientX + right.clientX) / 2,
      clientY: (left.clientY + right.clientY) / 2,
    };
  }

  function finite(value, fallback) {
    return Number.isFinite(Number(value)) ? Number(value) : fallback;
  }

  class NikasHouseOverview extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._hass = null;
      this._panel = null;
      this._pointers = new Map();
      this._session = null;
      this._pinch = null;
      this._lastTwoFingerTap = 0;
      this._suppressClicksUntil = 0;
      this._sendingPointerCancel = false;
      this._statusTimer = null;
      this._resizeObserver = null;
      this._frame = null;
      this._state = { scale: 1, x: 0, y: 0 };

      this._onPointerDown = (event) => this._pointerDown(event);
      this._onPointerMove = (event) => this._pointerMove(event);
      this._onPointerUp = (event) => this._pointerEnd(event, false);
      this._onPointerCancel = (event) => this._pointerEnd(event, true);
      this._onGuardedActivation = (event) => this._guardActivation(event);
      this._renderShell();
    }

    set hass(value) {
      this._hass = value;
      const hero = this.shadowRoot?.querySelector("nikas-house-main-hero");
      if (hero) hero.hass = value;
    }

    get hass() {
      return this._hass;
    }

    set panel(value) {
      this._panel = value;
      this._loadState();
      this._renderPanelConfig();
      this._applyTransform();
      this._scheduleClamp();
    }

    get panel() {
      return this._panel;
    }

    connectedCallback() {
      this._installGestureListeners();
      this._observeGeometry();
      this._renderPanelConfig();
      this._applyTransform();
      this._scheduleClamp();
    }

    disconnectedCallback() {
      this._removeGestureListeners();
      this._resizeObserver?.disconnect();
      this._resizeObserver = null;
      if (this._frame !== null) {
        (window.cancelAnimationFrame || window.clearTimeout)(this._frame);
        this._frame = null;
      }
      if (this._statusTimer !== null) window.clearTimeout(this._statusTimer);
      this._statusTimer = null;
    }

    _config() {
      return this._panel?.config || this._panel || {};
    }

    _renderShell() {
      this.shadowRoot.innerHTML = `
        <style>
          :host{display:block;width:100%;height:100dvh;min-height:100%;overflow:hidden;background:var(--primary-background-color,#f4f6f8);color:var(--primary-text-color,#111827);font-family:var(--paper-font-body1_-_font-family,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif)}
          *{box-sizing:border-box}
          .app{position:relative;width:100%;height:100dvh;min-height:100%;display:grid;grid-template-rows:auto minmax(0,1fr) auto;overflow:hidden;background:var(--primary-background-color,#f4f6f8)}
          .header{z-index:20;display:grid;grid-template-columns:52px minmax(0,1fr) 52px;align-items:center;min-height:62px;padding:max(5px,env(safe-area-inset-top,0px)) max(8px,env(safe-area-inset-right,0px)) 5px max(8px,env(safe-area-inset-left,0px));background:var(--card-background-color,var(--ha-card-background,#fff));border-bottom:1px solid var(--divider-color,rgba(0,0,0,.12));box-shadow:0 2px 12px rgba(0,0,0,.06)}
          .rail{width:44px;height:44px;border:1px solid var(--divider-color,rgba(0,0,0,.12));border-radius:16px;display:grid;place-items:center;padding:0;background:var(--card-background-color,var(--ha-card-background,#fff));color:var(--primary-text-color,#111827);box-shadow:0 7px 20px rgba(23,45,76,.08);cursor:pointer;-webkit-tap-highlight-color:transparent}
          #refresh{color:var(--primary-color,#03a9f4)}
          .rail:focus-visible,.tab:focus-visible{outline:2px solid var(--primary-color,#03a9f4);outline-offset:1px}
          .rail ha-icon{--mdc-icon-size:25px;width:25px;height:25px}
          .heading{min-width:0;align-self:center;text-align:center;line-height:1.12}
          .heading strong,.heading span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
          .heading strong{font-size:23px;font-weight:800;letter-spacing:-.02em}
          .heading span{margin-top:3px;font-size:14px;font-weight:560;line-height:1.2;color:var(--secondary-text-color,#6b7280)}
          .canvas-viewport{position:relative;min-width:0;min-height:0;overflow-x:hidden;overflow-y:auto;overscroll-behavior-x:none;overscroll-behavior-y:none;touch-action:pan-y;background:var(--primary-background-color,#f4f6f8)}
          .canvas-viewport.zoomed{overflow:hidden;overscroll-behavior:none;touch-action:none;user-select:none;-webkit-user-select:none}
          .work-canvas{position:relative;margin:8px 12px 10px;min-width:0;min-height:calc(100% - 18px);transform-origin:0 0;transform:translate3d(0px,0px,0) scale(1);will-change:transform;contain:layout style;visibility:hidden}
          .canvas-viewport.zoomed .work-canvas{position:absolute;left:12px;right:12px;top:8px;margin:0;min-height:calc(100% - 18px)}
          .work-canvas.ready{visibility:visible}
          nikas-house-main-hero{position:absolute;inset:0;display:block;width:auto;height:auto;min-height:0}
          .bottom{z-index:20;padding:6px max(8px,env(safe-area-inset-right,0px)) calc(6px + env(safe-area-inset-bottom,0px)) max(8px,env(safe-area-inset-left,0px));background:var(--card-background-color,var(--ha-card-background,#fff));border-top:1px solid var(--divider-color,rgba(0,0,0,.12));box-shadow:0 -4px 18px rgba(0,0,0,.08)}
          nav{width:min(100%,720px);margin:0 auto;display:grid;grid-template-columns:repeat(var(--house-tab-count,3),minmax(0,1fr));gap:4px}
          .tab{appearance:none;border:0;background:transparent;color:var(--secondary-text-color,#5f6368);min-width:0;min-height:52px;padding:4px 4px;border-radius:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;font:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent}
          .tab ha-icon{--mdc-icon-size:28px;width:28px;height:28px}.tab span{display:block;width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:center;font-size:12px;line-height:15px;font-weight:700}
          .tab.active{color:var(--primary-color,#03a9f4);background:color-mix(in srgb,var(--primary-color,#03a9f4) 11%,transparent);cursor:default}
          .scale-status{position:absolute;z-index:40;left:50%;bottom:calc(82px + env(safe-area-inset-bottom,0px));transform:translate(-50%,10px);opacity:0;pointer-events:none;padding:9px 14px;border-radius:999px;background:rgba(20,27,34,.88);color:#fff;font-size:13px;font-weight:720;white-space:nowrap;transition:opacity .14s ease,transform .14s ease}
          .scale-status.visible{opacity:1;transform:translate(-50%,0)}
          @media(max-width:600px){:host{position:fixed;inset:0;width:auto;height:auto;min-height:0}.app{position:absolute;inset:0;width:auto;height:auto;min-height:0}}
          @media(max-width:390px){.header{grid-template-columns:48px minmax(0,1fr) 48px;min-height:60px}.heading strong{font-size:21px}.heading span{font-size:13px}.tab{padding-left:2px;padding-right:2px}.work-canvas{margin:7px 9px 8px}.canvas-viewport.zoomed .work-canvas{left:9px;right:9px;top:7px;margin:0}}
          @media(min-width:900px){.work-canvas{margin:14px 18px 16px}.canvas-viewport.zoomed .work-canvas{left:18px;right:18px;top:14px;margin:0}}
          @media(prefers-reduced-motion:reduce){.scale-status{transition:none}}
        </style>
        <div class="app">
          <header class="header">
            <button class="rail" id="menu" type="button" aria-label="Меню Home Assistant"><ha-icon icon="mdi:menu"></ha-icon></button>
            <div class="heading"><strong>Дом сейчас</strong><span>Состояние · UI v${UI_VERSION}</span></div>
            <button class="rail" id="refresh" type="button" aria-label="Обновить"><ha-icon icon="mdi:refresh"></ha-icon></button>
          </header>
          <main class="canvas-viewport" aria-label="Рабочая область панели Дом">
            <div class="work-canvas"><nikas-house-main-hero></nikas-house-main-hero></div>
          </main>
          <div class="bottom"><nav aria-label="Основная навигация"></nav></div>
          <div class="scale-status" role="status" aria-live="polite">Масштаб 100%</div>
        </div>`;

      this.shadowRoot.getElementById("menu").onclick = () => {
        this.dispatchEvent(new CustomEvent("hass-toggle-menu", {
          bubbles: true,
          composed: true,
        }));
      };
      this.shadowRoot.getElementById("refresh").onclick = () => window.location.reload();
    }

    _renderPanelConfig() {
      const config = this._config();
      const title = this.shadowRoot?.querySelector(".heading strong");
      if (title && config.title) title.textContent = config.title;

      const hero = this.shadowRoot?.querySelector("nikas-house-main-hero");
      if (hero && config.hero && hero._nikasConfig !== config.hero) {
        hero._nikasConfig = config.hero;
        hero.setConfig({ ...config.hero, standalone: true });
      }
      if (hero && this._hass) hero.hass = this._hass;
      this._renderTabs();
    }

    _renderTabs() {
      const nav = this.shadowRoot?.querySelector("nav");
      if (!nav) return;
      const tabs = Array.isArray(this._config().tabs) ? this._config().tabs : [];
      nav.style.setProperty("--house-tab-count", String(Math.max(tabs.length, 1)));
      nav.replaceChildren();

      for (const tab of tabs) {
        const button = document.createElement("button");
        const active = tab.id === "home" || window.location.pathname === tab.path;
        button.type = "button";
        button.className = `tab${active ? " active" : ""}`;
        button.disabled = active;
        if (active) button.setAttribute("aria-current", "page");

        const icon = document.createElement("ha-icon");
        icon.setAttribute("icon", tab.icon || "mdi:view-dashboard-outline");
        const label = document.createElement("span");
        label.textContent = tab.label || tab.title || tab.id;
        button.append(icon, label);
        button.onclick = () => {
          if (!active) {
            this._resetForNavigation();
            navigate(tab.path);
          }
        };
        nav.appendChild(button);
      }
    }

    _storageKey() {
      const panelId = String(this._config().id || "house-overview").replace(/[^a-z0-9._-]/gi, "_");
      return `nikas-house:transform-canvas:v1:${panelId}`;
    }

    _loadState() {
      this._state = { scale: 1, x: 0, y: 0 };
      try {
        const stored = JSON.parse(window.localStorage.getItem(this._storageKey()) || "null");
        if (!stored || typeof stored !== "object") return;
        this._state = {
          scale: Math.min(MAX_SCALE, Math.max(MIN_SCALE, finite(stored.scale, 1))),
          x: finite(stored.x, 0),
          y: finite(stored.y, 0),
        };
        if (this._state.scale <= 1) this._state = { scale: this._state.scale, x: 0, y: 0 };
      } catch (_error) {
        // Local preference storage is optional; the in-memory transform remains usable.
      }
    }

    _persistState() {
      try {
        window.localStorage.setItem(this._storageKey(), JSON.stringify(this._state));
      } catch (_error) {
        // Keep the current session functional when storage is unavailable.
      }
    }

    _canvas() {
      return this.shadowRoot?.querySelector(".work-canvas");
    }

    _viewport() {
      return this.shadowRoot?.querySelector(".canvas-viewport");
    }

    _contentBounds(scale = this._state.scale) {
      const canvas = this._canvas();
      const viewport = this._viewport();
      if (!canvas || !viewport || scale <= 1) return { minX: 0, minY: 0 };
      const viewportWidth = Math.max(0, (viewport.clientWidth || 0) - (canvas.offsetLeft || 0));
      const viewportHeight = Math.max(0, (viewport.clientHeight || 0) - (canvas.offsetTop || 0));
      const contentWidth = Math.max(canvas.offsetWidth || 0, canvas.scrollWidth || 0);
      const contentHeight = Math.max(canvas.offsetHeight || 0, canvas.scrollHeight || 0);
      return {
        minX: Math.min(0, viewportWidth - contentWidth * scale),
        minY: Math.min(0, viewportHeight - contentHeight * scale),
      };
    }

    _clampedState(scale, x, y) {
      const safeScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, finite(scale, 1)));
      if (safeScale <= 1) return { scale: safeScale, x: 0, y: 0 };
      const bounds = this._contentBounds(safeScale);
      return {
        scale: safeScale,
        x: Math.min(0, Math.max(bounds.minX, finite(x, 0))),
        y: Math.min(0, Math.max(bounds.minY, finite(y, 0))),
      };
    }

    _setTransform(scale, x, y) {
      this._state = this._clampedState(scale, x, y);
      this._applyTransform();
    }

    _applyTransform() {
      const canvas = this._canvas();
      const viewport = this._viewport();
      if (!canvas || !viewport) return;
      const zoomed = this._state.scale > 1.0001;
      if (!zoomed) this._state = { scale: this._state.scale, x: 0, y: 0 };
      viewport.classList.toggle("zoomed", zoomed);
      const { scale, x, y } = this._state;
      canvas.style.transform = `translate3d(${x}px, ${y}px, 0) scale(${scale})`;
      canvas.classList.add("ready");
    }

    _scheduleClamp() {
      if (this._frame !== null) {
        (window.cancelAnimationFrame || window.clearTimeout)(this._frame);
      }
      const schedule = window.requestAnimationFrame || ((callback) => window.setTimeout(callback, 0));
      this._frame = schedule(() => {
        this._frame = null;
        const current = this._state;
        this._state = this._clampedState(current.scale, current.x, current.y);
        this._applyTransform();
        this._persistState();
      });
    }

    _observeGeometry() {
      if (this._resizeObserver || typeof ResizeObserver !== "function") return;
      this._resizeObserver = new ResizeObserver(() => this._scheduleClamp());
      const viewport = this._viewport();
      const canvas = this._canvas();
      if (viewport) this._resizeObserver.observe(viewport);
      if (canvas) this._resizeObserver.observe(canvas);
    }

    _installGestureListeners() {
      const viewport = this._viewport();
      if (!viewport || viewport.dataset.gesturesInstalled === "true") return;
      viewport.dataset.gesturesInstalled = "true";
      viewport.addEventListener("pointerdown", this._onPointerDown, { passive: false });
      viewport.addEventListener("pointermove", this._onPointerMove, { passive: false });
      viewport.addEventListener("pointerup", this._onPointerUp, { passive: false });
      viewport.addEventListener("pointercancel", this._onPointerCancel, { passive: false });
      viewport.addEventListener("click", this._onGuardedActivation, true);
      viewport.addEventListener("contextmenu", this._onGuardedActivation, true);
    }

    _removeGestureListeners() {
      const viewport = this._viewport();
      if (!viewport || viewport.dataset.gesturesInstalled !== "true") return;
      delete viewport.dataset.gesturesInstalled;
      viewport.removeEventListener("pointerdown", this._onPointerDown);
      viewport.removeEventListener("pointermove", this._onPointerMove);
      viewport.removeEventListener("pointerup", this._onPointerUp);
      viewport.removeEventListener("pointercancel", this._onPointerCancel);
      viewport.removeEventListener("click", this._onGuardedActivation, true);
      viewport.removeEventListener("contextmenu", this._onGuardedActivation, true);
    }

    _pointerRecord(event) {
      return {
        id: event.pointerId,
        clientX: event.clientX,
        clientY: event.clientY,
        startX: event.clientX,
        startY: event.clientY,
        holdTarget: event.composedPath?.()[0] || event.target,
      };
    }

    _pointerDown(event) {
      if (event.pointerType !== "touch") return;
      const record = this._pointerRecord(event);
      this._pointers.set(event.pointerId, record);
      if (this._state.scale > 1) this._capturePointer(event.pointerId);

      if (this._pointers.size === 1) {
        this._session = {
          startedAt: performance.now(),
          maxPointers: 1,
          moved: false,
          multi: false,
          cancelledHold: false,
          startState: { ...this._state },
          startX: record.clientX,
          startY: record.clientY,
        };
      } else if (this._pointers.size === 2 && this._session) {
        for (const pointer of this._pointers.values()) this._capturePointer(pointer.id);
        this._session.multi = true;
        this._session.maxPointers = 2;
        this._cancelPendingHolds();
        this._suppressClicksUntil = Date.now() + CLICK_GUARD;
        this._beginPinch();
        event.preventDefault();
      } else if (this._session) {
        this._session.maxPointers = Math.max(this._session.maxPointers, this._pointers.size);
        this._session.moved = true;
        this._cancelPendingHolds();
        event.preventDefault();
      }
    }

    _beginPinch() {
      const points = [...this._pointers.values()].slice(0, 2);
      if (points.length !== 2) return;
      const mid = midpoint(points[0], points[1]);
      const canvas = this._canvas();
      const viewport = this._viewport();
      if (!canvas || !viewport) return;
      const rect = viewport.getBoundingClientRect();
      const localX = mid.clientX - rect.left - canvas.offsetLeft;
      const localY = mid.clientY - rect.top - canvas.offsetTop;
      const nativeScrollY = this._state.scale <= 1 ? viewport.scrollTop : 0;
      this._pinch = {
        distance: Math.max(1, distance(points[0], points[1])),
        scale: this._state.scale,
        contentX: (localX - this._state.x) / this._state.scale,
        contentY: (localY + nativeScrollY - this._state.y) / this._state.scale,
        startMidX: mid.clientX,
        startMidY: mid.clientY,
      };
    }

    _pointerMove(event) {
      if (event.pointerType !== "touch") return;
      const record = this._pointers.get(event.pointerId);
      if (!record || !this._session) return;
      record.clientX = event.clientX;
      record.clientY = event.clientY;

      if (this._session.multi) {
        if (this._pointers.size < 2 || !this._pinch) return;
        const points = [...this._pointers.values()].slice(0, 2);
        const currentDistance = Math.max(1, distance(points[0], points[1]));
        const mid = midpoint(points[0], points[1]);
        const distanceDelta = Math.abs(currentDistance - this._pinch.distance);
        const midpointDelta = Math.hypot(
          mid.clientX - this._pinch.startMidX,
          mid.clientY - this._pinch.startMidY,
        );
        if (!this._session.moved && distanceDelta < PAN_THRESHOLD && midpointDelta < PAN_THRESHOLD) {
          return;
        }
        this._session.moved = true;
        const canvas = this._canvas();
        const viewport = this._viewport();
        if (!canvas || !viewport) return;
        const rect = viewport.getBoundingClientRect();
        const localX = mid.clientX - rect.left - canvas.offsetLeft;
        const localY = mid.clientY - rect.top - canvas.offsetTop;
        const scale = this._pinch.scale * currentDistance / this._pinch.distance;
        const boundedScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
        const x = localX - this._pinch.contentX * boundedScale;
        const y = localY - this._pinch.contentY * boundedScale;
        if (boundedScale > 1) viewport.scrollTop = 0;
        this._setTransform(boundedScale, x, y);
        this._suppressClicksUntil = Date.now() + CLICK_GUARD;
        event.preventDefault();
        return;
      }

      if (this._state.scale <= 1) return;
      const deltaX = event.clientX - this._session.startX;
      const deltaY = event.clientY - this._session.startY;
      if (!this._session.moved && Math.hypot(deltaX, deltaY) < PAN_THRESHOLD) return;
      if (!this._session.moved) {
        this._session.moved = true;
        this._cancelPendingHolds();
      }
      this._setTransform(
        this._session.startState.scale,
        this._session.startState.x + deltaX,
        this._session.startState.y + deltaY,
      );
      this._suppressClicksUntil = Date.now() + CLICK_GUARD;
      event.preventDefault();
    }

    _pointerEnd(event, cancelled) {
      if (this._sendingPointerCancel || event.pointerType !== "touch") return;
      const session = this._session;
      if (!session || !this._pointers.has(event.pointerId)) return;
      this._pointers.delete(event.pointerId);
      try {
        this._viewport()?.releasePointerCapture?.(event.pointerId);
      } catch (_error) {
        // The browser may already have released capture.
      }

      if (cancelled) session.moved = true;
      if (session.multi && this._pointers.size < 2 && this._pinch) {
        this._pinch = null;
        if (session.moved && this._state.scale >= 0.97 && this._state.scale <= 1.03) {
          this._resetTransform(true);
        } else {
          this._persistState();
        }
      }

      if (this._pointers.size !== 0) return;
      const elapsed = performance.now() - session.startedAt;
      const twoFingerTap = !cancelled
        && session.multi
        && session.maxPointers === 2
        && !session.moved
        && elapsed <= TAP_DURATION;

      if (twoFingerTap) {
        const now = performance.now();
        if (now - this._lastTwoFingerTap <= DOUBLE_TAP_GAP) {
          this._lastTwoFingerTap = 0;
          this._resetTransform(true);
        } else {
          this._lastTwoFingerTap = now;
        }
      } else if (session.moved || session.multi) {
        this._persistState();
      }

      if (session.moved || session.multi) {
        this._suppressClicksUntil = Date.now() + CLICK_GUARD;
      }
      this._session = null;
      this._pinch = null;
    }

    _cancelPendingHolds() {
      if (!this._session || this._session.cancelledHold) return;
      this._session.cancelledHold = true;
      this._sendingPointerCancel = true;
      try {
        for (const pointer of this._pointers.values()) {
          const target = pointer.holdTarget;
          if (!target?.dispatchEvent) continue;
          const init = {
            bubbles: true,
            composed: true,
            cancelable: false,
            pointerId: pointer.id,
            pointerType: "touch",
          };
          const cancelEvent = typeof PointerEvent === "function"
            ? new PointerEvent("pointercancel", init)
            : new Event("pointercancel", init);
          target.dispatchEvent(cancelEvent);
        }
      } finally {
        this._sendingPointerCancel = false;
      }
    }

    _guardActivation(event) {
      if (Date.now() >= this._suppressClicksUntil && !this._session?.moved && !this._session?.multi) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation?.();
    }

    _resetTransform(showStatus) {
      this._state = { scale: 1, x: 0, y: 0 };
      const viewport = this._viewport();
      if (viewport) viewport.scrollTop = 0;
      this._applyTransform();
      this._persistState();
      if (showStatus) this._showScaleStatus();
    }

    _resetForNavigation() {
      const viewport = this._viewport();
      if (viewport) viewport.scrollTop = 0;
      const current = this._state;
      this._state = this._clampedState(current.scale, 0, 0);
      this._applyTransform();
      this._persistState();
    }

    _capturePointer(pointerId) {
      try {
        this._viewport()?.setPointerCapture?.(pointerId);
      } catch (_error) {
        // Pointer capture is an optimization, not a state dependency.
      }
    }

    _showScaleStatus() {
      const status = this.shadowRoot?.querySelector(".scale-status");
      if (!status) return;
      if (this._statusTimer !== null) window.clearTimeout(this._statusTimer);
      status.classList.add("visible");
      this._statusTimer = window.setTimeout(() => {
        status.classList.remove("visible");
        this._statusTimer = null;
      }, 1100);
    }
  }

  customElements.define(ELEMENT_NAME, NikasHouseOverview);
})();
