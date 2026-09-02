(() => {
  const BOOTSTRAP_KEY = "__nikas_house_navigation_v1_0_0_b001";
  if (window[BOOTSTRAP_KEY]) return;
  window[BOOTSTRAP_KEY] = true;

  const SPECIALIZED_SOURCE_ROUTE_KEY = "nikas.specialized.source_route.v1";
  const SPECIALIZED_SOURCE_ROUTE_AT_KEY = "nikas.specialized.source_route_at.v1";
  const SPECIALIZED_PANEL_PATHS = new Set([
    "/dashboard-zont",
    "/starline",
    "/dashboard-s8-omni",
    "/dashboard-irrigation",
    "/dashboard-ups",
    "/dashboard-keenetic",
    "/dashboard-lider",
    "/dashboard-water-accounting",
    "/dashboard-access-v1",
  ]);

  function sourceBaseRoute(pathname) {
    if (pathname === "/dashboard-house-v13" || pathname.startsWith("/dashboard-house-v13/")) {
      return "/dashboard-house-v13/home";
    }
    if (pathname === "/dashboard-rooms-v11" || pathname.startsWith("/dashboard-rooms-v11/")) {
      return "/dashboard-rooms-v11/rooms";
    }
    if (pathname === "/dashboard-actions" || pathname.startsWith("/dashboard-actions/")) {
      return "/dashboard-actions/home";
    }
    if (pathname === "/dashboard-infrastructure" || pathname.startsWith("/dashboard-infrastructure/")) {
      return "/dashboard-infrastructure/overview";
    }
    return null;
  }

  function sameOriginNavigationPath(path) {
    if (typeof path !== "string" || !path.startsWith("/")) return null;
    try {
      const target = new URL(path, window.location.origin);
      if (target.origin !== window.location.origin) return null;
      return `${target.pathname}${target.search}${target.hash}`;
    } catch (_error) {
      return null;
    }
  }

  function isSpecializedPanelRoute(path) {
    const target = sameOriginNavigationPath(path);
    if (!target) return false;
    const pathname = new URL(target, window.location.origin).pathname;
    return [...SPECIALIZED_PANEL_PATHS].some(
      (root) => pathname === root || pathname.startsWith(`${root}/`)
    );
  }

  function clearSpecializedSourceRoute() {
    try {
      window.sessionStorage.removeItem(SPECIALIZED_SOURCE_ROUTE_KEY);
      window.sessionStorage.removeItem(SPECIALIZED_SOURCE_ROUTE_AT_KEY);
    } catch (_error) {
      // Storage is optional; destination panels retain their safe fallback.
    }
  }

  function rememberSpecializedSourceRoute(pathname, destination) {
    if (!isSpecializedPanelRoute(destination)) return false;
    const route = sourceBaseRoute(pathname);
    if (!route) return false;
    try {
      window.sessionStorage.setItem(SPECIALIZED_SOURCE_ROUTE_KEY, route);
      window.sessionStorage.setItem(SPECIALIZED_SOURCE_ROUTE_AT_KEY, String(Date.now()));
    } catch (_error) {
      clearSpecializedSourceRoute();
      return false;
    }
    return true;
  }

  function navigateWithSourceHandoff(path) {
    const target = sameOriginNavigationPath(path);
    if (!target) return false;
    const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (current === target) return true;
    rememberSpecializedSourceRoute(window.location.pathname, target);
    window.history.pushState(null, "", target);
    window.dispatchEvent(new Event("location-changed"));
    return true;
  }

  // Navigation only: never inject, replace or hide legacy YAML dashboard DOM.
  window.NikasHouseNavigation = Object.freeze({
    contractVersion: "1.1",
    navigate: navigateWithSourceHandoff,
  });
})();
