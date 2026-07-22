// Use the local Flask server during development and the hosted backend in production.
window.API_BASE = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? ""
  : "https://davidl72code-ezride-umass.hf.space";
