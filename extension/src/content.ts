const SUPPORTED_HOSTS = new Set(["www.amazon.com", "www.amazon.fr"]);

if (SUPPORTED_HOSTS.has(location.hostname)) {
  void chrome.runtime.sendMessage({ type: "PING" }).catch(() => undefined);
}
