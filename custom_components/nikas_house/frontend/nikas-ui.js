(() => {
  const BOOTSTRAP_KEY = "__nikas_house_navigation_v1_0_3_beta001_b001";
  if (window[BOOTSTRAP_KEY]) return;
  window[BOOTSTRAP_KEY] = true;

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

  function navigate(path) {
    const target = sameOriginNavigationPath(path);
    if (!target) return false;
    const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (current === target) return true;
    window.history.pushState(null, "", target);
    window.dispatchEvent(new Event("location-changed"));
    return true;
  }

  // Navigation only: never inject, replace or hide legacy YAML dashboard DOM.
  window.NikasHouseNavigation = Object.freeze({
    contractVersion: "1.3",
    navigate,
  });
})();
