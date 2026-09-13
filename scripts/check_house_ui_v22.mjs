import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const bundlePath = new URL(
  "../custom_components/nikas_house/frontend/dist/nikas-house-overview.js",
  import.meta.url,
);
const source = fs.readFileSync(bundlePath, "utf8");

class FakeIcon {
  constructor() {
    this.attributes = new Map([["icon", "mdi:refresh"]]);
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }
}

class FakeButton {
  constructor() {
    this.attributes = new Map();
    this.className = "rail";
    this.disabled = false;
    this.icon = new FakeIcon();
    this.onclick = null;
  }

  querySelector(selector) {
    return selector === "ha-icon" ? this.icon : null;
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  removeAttribute(name) {
    this.attributes.delete(name);
  }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }
}

class FakeStatus {
  constructor() {
    this.textContent = "";
    this.className = "refresh-status";
  }
}

class FakeShadowRoot {
  constructor() {
    this.menu = new FakeButton();
    this.heading = new FakeButton();
    this.refresh = new FakeButton();
    this.status = new FakeStatus();
    this._innerHTML = "";
  }

  set innerHTML(value) {
    this._innerHTML = value;
  }

  get innerHTML() {
    return this._innerHTML;
  }

  getElementById(id) {
    if (id === "menu") return this.menu;
    if (id === "heading") return this.heading;
    if (id === "refresh") return this.refresh;
    return null;
  }

  querySelector(selector) {
    if (selector === ".refresh-status") return this.status;
    return null;
  }
}

globalThis.HTMLElement = class {
  attachShadow() {
    this.shadowRoot = new FakeShadowRoot();
    return this.shadowRoot;
  }

  toggleAttribute() {}
  addEventListener() {}
  removeEventListener() {}
  dispatchEvent() { return true; }
};

const registry = new Map();
globalThis.customElements = {
  define(name, constructor) { registry.set(name, constructor); },
  get(name) { return registry.get(name); },
};
globalThis.Event = class Event {};
globalThis.CustomEvent = class CustomEvent {};

let now = 0;
let nextTimerId = 1;
const timers = new Map();
const scheduledDelays = [];
globalThis.performance = { now: () => now };
globalThis.window = {
  customCards: [],
  location: { pathname: "/dashboard-house-v13/home" },
  history: { pushState() {} },
  dispatchEvent() {},
  localStorage: { getItem() { return null; }, setItem() {} },
  setInterval() { return 1; },
  clearInterval() {},
  setTimeout(callback, delay) {
    const id = nextTimerId++;
    timers.set(id, { callback, delay });
    scheduledDelays.push(delay);
    return id;
  },
  clearTimeout(id) { timers.delete(id); },
};

function runTimerWithDelay(delay) {
  const match = [...timers.entries()].find(([, timer]) => timer.delay === delay);
  assert.ok(match, `expected a ${delay} ms timer`);
  const [id, timer] = match;
  timers.delete(id);
  now += delay;
  timer.callback();
}

async function flushMicrotasks() {
  await Promise.resolve();
  await Promise.resolve();
}

vm.runInThisContext(source, { filename: bundlePath.pathname });
const Panel = customElements.get("nikas-house-panel");
assert.ok(Panel, "production bundle must register nikas-house-panel");

let serviceCalls = 0;
const panel = new Panel();
panel.hass = {
  async callService(domain, service) {
    serviceCalls += 1;
    assert.equal(domain, "nikas_house");
    assert.equal(service, "refresh");
  },
};

const navigationTargets = [];
window.NikasHouseNavigation = { navigate: path => navigationTargets.push(path) };
window.location.search = "?return_to=/dashboard-actions/home";
assert.equal(typeof panel.shadowRoot.heading.onclick, "function", "House title must be actionable");
assert.match(panel.shadowRoot.innerHTML, /<button[^>]*id="heading"[^>]*type="button"/);
panel.shadowRoot.heading.onclick();
assert.deepEqual(navigationTargets, ["/home/overview"], "House title must navigate one level to overview");

const successfulRefresh = panel._refresh();
await flushMicrotasks();
void panel._refresh();
assert.equal(serviceCalls, 1, "refresh must be single-flight");
assert.equal(panel.shadowRoot.refresh.disabled, true);
assert.equal(panel.shadowRoot.refresh.className, "rail busy");
assert.equal(panel.shadowRoot.refresh.getAttribute("aria-busy"), "true");
runTimerWithDelay(900);
await successfulRefresh;
assert.equal(panel.shadowRoot.refresh.disabled, false);
assert.equal(panel.shadowRoot.refresh.className, "rail success");
assert.equal(panel.shadowRoot.refresh.icon.getAttribute("icon"), "mdi:check");
assert.equal(panel.shadowRoot.status.textContent, "Запрос обновления выполнен");
runTimerWithDelay(1400);
assert.equal(panel.shadowRoot.refresh.className, "rail");
assert.equal(panel.shadowRoot.refresh.icon.getAttribute("icon"), "mdi:refresh");

const failedPanel = new Panel();
failedPanel.hass = { async callService() { throw new Error("offline"); } };
const failedRefresh = failedPanel._refresh();
await flushMicrotasks();
runTimerWithDelay(900);
await failedRefresh;
assert.equal(failedPanel.shadowRoot.refresh.className, "rail error");
assert.equal(
  failedPanel.shadowRoot.refresh.icon.getAttribute("icon"),
  "mdi:alert-circle-outline",
);
assert.equal(failedPanel.shadowRoot.status.textContent, "Не удалось обновить данные");

const retry = failedPanel._refresh();
await flushMicrotasks();
assert.ok(
  ![...timers.values()].some((timer) => timer.delay === 1400),
  "retry must cancel the previous result timer",
);
runTimerWithDelay(900);
await retry;
assert.equal(failedPanel.shadowRoot.refresh.className, "rail error");

let finishSlowRefresh;
const slowPanel = new Panel();
slowPanel.hass = {
  callService() {
    return new Promise((resolve) => { finishSlowRefresh = resolve; });
  },
};
const slowRefresh = slowPanel._refresh();
await flushMicrotasks();
assert.equal(slowPanel.shadowRoot.refresh.className, "rail busy");
now += 1000;
finishSlowRefresh();
await slowRefresh;
assert.equal(slowPanel.shadowRoot.refresh.className, "rail success");
assert.ok(
  ![...timers.values()].some((timer) => timer.delay > 0 && timer.delay < 900),
  "slow requests must not add an artificial busy delay",
);

let finishDisconnectedRefresh;
const disconnectedPanel = new Panel();
disconnectedPanel.hass = {
  callService() {
    return new Promise((resolve) => { finishDisconnectedRefresh = resolve; });
  },
};
const disconnectedRefresh = disconnectedPanel._refresh();
await flushMicrotasks();
disconnectedPanel.disconnectedCallback();
finishDisconnectedRefresh();
await flushMicrotasks();
runTimerWithDelay(900);
await disconnectedRefresh;
assert.equal(disconnectedPanel.shadowRoot.refresh.className, "rail");
assert.equal(disconnectedPanel.shadowRoot.status.textContent, "");

assert.ok(scheduledDelays.includes(900), "minimum busy interval must be tested");
assert.ok(scheduledDelays.includes(1400), "result presentation interval must be tested");
assert.ok(source.includes("--mdc-icon-size:26px"));
assert.ok(source.includes("grid-template-rows:calc(60px + env(safe-area-inset-top,0px))"));
assert.ok(source.includes("calc(64px + env(safe-area-inset-bottom,0px))"));
assert.ok(source.includes('addEventListener("touchmove", move, { passive: false, capture: true })'));
assert.ok(!source.includes("height:100dvh"));
assert.ok(!source.includes("position:fixed"));
assert.ok(!source.includes("window.location.reload"));

console.log("House UI 2.2 production regression OK");
