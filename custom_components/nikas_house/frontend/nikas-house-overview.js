import "/nikas_house/frontend/nikas-house-hero.js?build=v1_0_3_beta001_b001";

(() => {
  const ELEMENT_NAME = "nikas-house-panel";
  const UI_VERSION = "1.0.3-beta001";
  if (customElements.get(ELEMENT_NAME)) return;

  const MIN_SCALE = 0.75;
  const MAX_SCALE = 2.0;
  const PAN_THRESHOLD = 6;
  const TAP_DURATION = 300;
  const DOUBLE_TAP_GAP = 420;
  const CLICK_GUARD = 460;
  const BOUNDARY_THRESHOLD = 4;
  const REFRESH_MINIMUM_MS = 900;
  const REFRESH_RESULT_MS = 1400;

  function shouldBlockBoundaryMove({ deltaX, deltaY, inViewport, scrollTop, scrollHeight, clientHeight }) {
    if (!Number.isFinite(deltaY) || Math.abs(deltaY) <= Math.abs(Number(deltaX) || 0)) return false;
    if (!inViewport) return true;
    const maximumScroll = Math.max(0, (Number(scrollHeight) || 0) - (Number(clientHeight) || 0));
    if (maximumScroll <= 1) return true;
    const currentScroll = Math.max(0, Number(scrollTop) || 0);
    if (deltaY > 0 && currentScroll <= 1) return true;
    return deltaY < 0 && currentScroll >= maximumScroll - 1;
  }

  function createScrollBoundaryGuard(host, viewport) {
    let touch = null;
    const startedInViewport = (event) => {
      const path = typeof event.composedPath === "function" ? event.composedPath() : [];
      return path.includes(viewport) || Boolean(viewport.contains?.(event.target));
    };
    const remember = (event) => {
      if (event.touches.length !== 1) { touch = null; return; }
      const current = event.touches[0];
      touch = { x: current.clientX, y: current.clientY, startX: current.clientX, startY: current.clientY, inViewport: startedInViewport(event), blocked: false };
    };
    const move = (event) => {
      if (event.touches.length !== 1) { touch = null; return; }
      const current = event.touches[0];
      if (!touch) { remember(event); return; }
      const deltaX = current.clientX - touch.x;
      const deltaY = current.clientY - touch.y;
      const travelX = current.clientX - touch.startX;
      const travelY = current.clientY - touch.startY;
      touch.x = current.clientX;
      touch.y = current.clientY;
      const verticalIntent = Math.abs(travelY) > BOUNDARY_THRESHOLD && Math.abs(travelY) > Math.abs(travelX);
      if (!touch.blocked && verticalIntent) {
        touch.blocked = shouldBlockBoundaryMove({
          deltaX,
          deltaY,
          inViewport: touch.inViewport,
          scrollTop: viewport.scrollTop,
          scrollHeight: viewport.scrollHeight,
          clientHeight: viewport.clientHeight,
        });
      }
      if (touch.blocked && event.cancelable) event.preventDefault();
    };
    const end = (event) => { if (event.touches.length === 1) remember(event); else touch = null; };
    const cancel = () => { touch = null; };
    host.addEventListener("touchstart", remember, { passive: false, capture: true });
    host.addEventListener("touchmove", move, { passive: false, capture: true });
    host.addEventListener("touchend", end, { passive: true, capture: true });
    host.addEventListener("touchcancel", cancel, { passive: true, capture: true });
    return () => {
      host.removeEventListener("touchstart", remember, true);
      host.removeEventListener("touchmove", move, true);
      host.removeEventListener("touchend", end, true);
      host.removeEventListener("touchcancel", cancel, true);
      touch = null;
    };
  }

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
      this._refreshResultTimer = null;
      this._refreshPending = false;
      this._refreshGeneration = 0;
      this._removeBoundaryGuard = null;
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
      if (!this._removeBoundaryGuard) {
        this._removeBoundaryGuard = createScrollBoundaryGuard(this, this._viewport());
      }
      this._observeGeometry();
      this._renderPanelConfig();
      this._applyTransform();
      this._scheduleClamp();
    }

    disconnectedCallback() {
      this._removeGestureListeners();
      this._removeBoundaryGuard?.();
      this._removeBoundaryGuard = null;
      this._refreshGeneration += 1;
      this._refreshPending = false;
      if (this._refreshResultTimer !== null) window.clearTimeout(this._refreshResultTimer);
      this._refreshResultTimer = null;
      const refresh = this.shadowRoot?.getElementById("refresh");
      const refreshIcon = refresh?.querySelector("ha-icon");
      if (refresh) {
        refresh.disabled = false;
        refresh.className = "rail";
        refresh.removeAttribute("aria-busy");
        refresh.setAttribute("aria-label", "Обновить");
      }
      refreshIcon?.setAttribute("icon", "mdi:refresh");
      const refreshStatus = this.shadowRoot?.querySelector(".refresh-status");
      if (refreshStatus) {
        refreshStatus.textContent = "";
        refreshStatus.className = "refresh-status";
      }
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
          :host{display:block;position:relative;inline-size:100%;block-size:100%;min-inline-size:0;min-block-size:0;overflow:hidden;overscroll-behavior:none;background:var(--primary-background-color,#f4f6f8);color:var(--primary-text-color,#111827);font-family:var(--paper-font-body1_-_font-family,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif)}
          *{box-sizing:border-box}
          .app{position:absolute;inset:0;inline-size:100%;block-size:100%;min-inline-size:0;min-block-size:0;display:grid;grid-template-rows:calc(60px + env(safe-area-inset-top,0px)) minmax(0,1fr) calc(64px + env(safe-area-inset-bottom,0px));overflow:hidden;overscroll-behavior:none;container:nikas-panel / inline-size;background:var(--primary-background-color,#f4f6f8)}
          .header{z-index:20;min-inline-size:0;padding:env(safe-area-inset-top,0px) calc(12px + env(safe-area-inset-right,0px)) 0 calc(12px + env(safe-area-inset-left,0px));display:grid;grid-template-columns:52px minmax(0,1fr) 52px;align-items:center;background:color-mix(in srgb,var(--primary-background-color,#f4f6f8) 97%,transparent);border-bottom:1px solid color-mix(in srgb,var(--divider-color,#dfe3e8) 70%,transparent);backdrop-filter:blur(18px) saturate(130%);-webkit-backdrop-filter:blur(18px) saturate(130%)}
          .rail{width:44px;height:44px;border:1px solid color-mix(in srgb,var(--divider-color,#dfe3e8) 72%,transparent);border-radius:16px;display:grid;place-items:center;padding:0;background:var(--card-background-color,var(--ha-card-background,#fff));color:var(--primary-text-color,#111827);box-shadow:0 7px 20px rgba(23,45,76,.08);cursor:pointer;-webkit-tap-highlight-color:transparent}
          #refresh{color:var(--primary-color,#03a9f4)}
          #refresh.busy{color:var(--primary-color,#03a9f4)}#refresh.success{color:#43a047}#refresh.error{color:#e53935}#refresh:disabled{opacity:.72;cursor:wait}
          #refresh.busy ha-icon{animation:nikas-house-refresh-spin .8s linear infinite}
          @keyframes nikas-house-refresh-spin{to{transform:rotate(360deg)}}
          .rail:focus-visible,.tab:focus-visible{outline:2px solid var(--primary-color,#03a9f4);outline-offset:1px}
          .rail ha-icon{--mdc-icon-size:25px;width:25px;height:25px}
          .heading{font:inherit;cursor:pointer;justify-self:center;width:min(360px,100%);height:52px;min-width:0;padding:5px 14px;border:1px solid color-mix(in srgb,var(--primary-color,#03a9f4) 24%,var(--divider-color,#dfe3e8));border-radius:16px;background:color-mix(in srgb,var(--primary-color,#03a9f4) 5%,var(--card-background-color,#fff));box-shadow:0 5px 16px rgba(23,45,76,.06);color:inherit;display:grid;place-content:center;text-align:center;line-height:1.08}
          .heading strong,.heading span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
          .heading:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}.heading strong{font-size:23px;font-weight:800;letter-spacing:-.02em}
          .heading span{margin-top:3px;font-size:14px;font-weight:560;line-height:1.2;color:var(--secondary-text-color,#6b7280)}
          .canvas-viewport{position:relative;min-width:0;min-height:0;overflow-x:hidden;overflow-y:auto;overscroll-behavior-x:none;overscroll-behavior-y:none;touch-action:pan-y;background:var(--primary-background-color,#f4f6f8)}
          .canvas-viewport.zoomed{overflow:hidden;overscroll-behavior:none;touch-action:none;user-select:none;-webkit-user-select:none}
          .work-canvas{position:relative;width:100%;min-width:0;min-height:100%;transform-origin:0 0;transform:translate3d(0px,0px,0) scale(1);will-change:transform;contain:layout style;visibility:visible}
          .work-content{position:relative;width:100%;max-width:1280px;min-height:100%;margin:0 auto}
          .work-canvas.ready{visibility:visible}
          nikas-house-main-hero{position:absolute;inset:12px 12px 20px;display:block;width:auto;height:auto;min-height:0}
          .bottom{z-index:20;padding:6px calc(6px + env(safe-area-inset-right,0px)) calc(6px + env(safe-area-inset-bottom,0px)) calc(6px + env(safe-area-inset-left,0px));background:var(--card-background-color,var(--ha-card-background,#fff));border-top:1px solid var(--divider-color,rgba(0,0,0,.12));box-shadow:0 -5px 22px rgba(23,45,76,.08)}
          nav{width:min(100%,720px);margin:0 auto;display:grid;grid-template-columns:repeat(var(--house-tab-count,3),minmax(0,1fr));gap:4px}
          .tab{appearance:none;border:0;background:transparent;color:var(--secondary-text-color,#5f6368);min-width:0;height:52px;padding:2px 3px 6px;border-radius:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;font:inherit;font-weight:700;line-height:1;cursor:pointer;-webkit-tap-highlight-color:transparent}
          .tab ha-icon{--mdc-icon-size:26px;width:26px;height:26px;flex:0 0 26px}.tab span{display:block;width:100%;flex:0 0 14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:center;font-size:12px;line-height:14px;font-weight:700}
          .tab.active{color:var(--primary-color,#03a9f4);background:color-mix(in srgb,var(--primary-color,#03a9f4) 11%,transparent);cursor:default}
          .scale-status{position:absolute;z-index:40;left:50%;bottom:calc(82px + env(safe-area-inset-bottom,0px));transform:translate(-50%,10px);opacity:0;pointer-events:none;padding:9px 14px;border-radius:999px;background:rgba(20,27,34,.88);color:#fff;font-size:13px;font-weight:720;white-space:nowrap;transition:opacity .14s ease,transform .14s ease}
          .scale-status.visible{opacity:1;transform:translate(-50%,0)}
          .refresh-status{position:absolute;z-index:40;right:calc(12px + env(safe-area-inset-right,0px));top:calc(66px + env(safe-area-inset-top,0px));transform:translateY(-8px);opacity:0;pointer-events:none;padding:8px 12px;border-radius:14px;background:rgba(20,27,34,.9);color:#fff;font-size:13px;font-weight:700;white-space:nowrap;transition:opacity .14s ease,transform .14s ease}
          .refresh-status.visible{opacity:1;transform:translateY(0)}
          @container nikas-panel (min-width:600px){nikas-house-main-hero{inset-inline:16px}}
          @container nikas-panel (min-width:1024px){nikas-house-main-hero{inset-inline:24px}}
          @container nikas-panel (max-width:359px){.header{grid-template-columns:48px minmax(0,1fr) 48px}.heading{width:100%;padding-inline:8px}.heading strong{font-size:21px}.heading span{font-size:13px}.tab{padding-left:2px;padding-right:2px}}
          @media(prefers-reduced-motion:reduce){.scale-status{transition:none}#refresh.busy ha-icon{animation:none;opacity:.58}}
        </style>
        <div class="app">
          <header class="header">
            <button class="rail" id="menu" type="button" aria-label="Меню Home Assistant"><ha-icon icon="mdi:menu"></ha-icon></button>
            <button class="heading" id="heading" type="button" aria-label="Дом сейчас — перейти к обзору"><strong>Дом сейчас</strong><span>Состояние · UI v${UI_VERSION}</span></button>
            <button class="rail" id="refresh" type="button" aria-label="Обновить"><ha-icon icon="mdi:refresh"></ha-icon></button>
          </header>
          <main class="canvas-viewport" aria-label="Рабочая область панели Дом">
            <div class="work-canvas"><div class="work-content"><nikas-house-main-hero></nikas-house-main-hero></div></div>
          </main>
          <div class="bottom"><nav aria-label="Основная навигация"></nav></div>
          <div class="scale-status" role="status" aria-live="polite">Масштаб 100%</div>
          <div class="refresh-status" role="status" aria-live="polite"></div>
        </div>`;

      this.shadowRoot.getElementById("menu").onclick = () => {
        this.dispatchEvent(new CustomEvent("hass-toggle-menu", {
          bubbles: true,
          composed: true,
        }));
      };
      this.shadowRoot.getElementById("heading").onclick = () => navigate("/home/overview");
      this.shadowRoot.getElementById("refresh").onclick = () => this._refresh();
    }

    async _refresh() {
      if (this._refreshPending) return;
      const button = this.shadowRoot?.getElementById("refresh");
      const icon = button?.querySelector("ha-icon");
      if (!button || !icon) return;
      if (this._refreshResultTimer !== null) window.clearTimeout(this._refreshResultTimer);
      this._refreshResultTimer = null;
      const status = this.shadowRoot?.querySelector(".refresh-status");
      if (status) {
        status.textContent = "";
        status.className = "refresh-status";
      }
      const generation = ++this._refreshGeneration;
      this._refreshPending = true;
      button.disabled = true;
      button.className = "rail busy";
      button.setAttribute("aria-busy", "true");
      button.setAttribute("aria-label", "Обновление данных");
      icon.setAttribute("icon", "mdi:refresh");
      const startedAt = performance.now();
      let success = false;
      try {
        if (!this._hass?.callService) throw new Error("Home Assistant service API is unavailable");
        const result = await this._hass.callService("nikas_house", "refresh");
        success = result !== false;
      } catch (_error) {
        success = false;
      }
      const remaining = Math.max(0, REFRESH_MINIMUM_MS - (performance.now() - startedAt));
      if (remaining > 0) await new Promise((resolve) => window.setTimeout(resolve, remaining));
      if (generation !== this._refreshGeneration) return;
      this._refreshPending = false;
      button.disabled = false;
      button.removeAttribute("aria-busy");
      button.className = `rail ${success ? "success" : "error"}`;
      const resultMessage = success ? "Запрос обновления выполнен" : "Не удалось обновить данные";
      button.setAttribute("aria-label", resultMessage);
      icon.setAttribute("icon", success ? "mdi:check" : "mdi:alert-circle-outline");
      if (status) {
        status.textContent = resultMessage;
        status.className = `refresh-status visible ${success ? "success" : "error"}`;
      }
      this._refreshResultTimer = window.setTimeout(() => {
        if (generation !== this._refreshGeneration) return;
        button.className = "rail";
        button.setAttribute("aria-label", "Обновить");
        icon.setAttribute("icon", "mdi:refresh");
        if (status) {
          status.textContent = "";
          status.className = "refresh-status";
        }
        this._refreshResultTimer = null;
      }, REFRESH_RESULT_MS);
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
