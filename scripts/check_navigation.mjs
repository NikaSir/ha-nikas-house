import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const storage = new Map();
const pushed = [];
const events = [];

globalThis.Event = class Event {
  constructor(type) {
    this.type = type;
  }
};

globalThis.window = {
  location: {
    origin: "https://ha.local",
    pathname: "/dashboard-house-v13/home",
    search: "",
    hash: "",
  },
  sessionStorage: {
    getItem(key) {
      return storage.has(key) ? storage.get(key) : null;
    },
    setItem(key, value) {
      storage.set(key, String(value));
    },
    removeItem(key) {
      storage.delete(key);
    },
  },
  history: {
    pushState(_state, _title, path) {
      pushed.push(path);
      const url = new URL(path, window.location.origin);
      window.location.pathname = url.pathname;
      window.location.search = url.search;
      window.location.hash = url.hash;
    },
  },
  dispatchEvent(event) {
    events.push(event.type);
  },
};

const source = fs.readFileSync(
  "custom_components/nikas_house/frontend/nikas-ui.js",
  "utf8",
);
vm.runInThisContext(source, { filename: "nikas-ui.js" });

assert.equal(window.NikasHouseNavigation.contractVersion, "1.1");
assert.equal(
  window.NikasHouseNavigation.navigate("/dashboard-access-v1/home"),
  true,
);
assert.deepEqual(pushed, ["/dashboard-access-v1/home"]);
assert.deepEqual(events, ["location-changed"]);
assert.equal(
  storage.get("nikas.specialized.source_route.v1"),
  "/dashboard-house-v13/home",
);
assert.match(storage.get("nikas.specialized.source_route_at.v1"), /^\d+$/);

window.location.pathname = "/dashboard-house-v13/home";
storage.clear();
assert.equal(
  window.NikasHouseNavigation.navigate("/dashboard-rooms-v11/rooms"),
  true,
);
assert.equal(pushed.at(-1), "/dashboard-rooms-v11/rooms");
assert.equal(events.at(-1), "location-changed");
assert.equal(storage.size, 0);

const pushCount = pushed.length;
assert.equal(
  window.NikasHouseNavigation.navigate("/dashboard-rooms-v11/rooms"),
  true,
);
assert.equal(pushed.length, pushCount);
assert.equal(window.NikasHouseNavigation.navigate("https://example.com"), false);
assert.equal(pushed.length, pushCount);

console.log("NikaS House one-tap navigation smoke test OK");
