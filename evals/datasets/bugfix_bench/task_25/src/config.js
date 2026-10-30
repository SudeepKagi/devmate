function cloneConfig(config, overrides = {}) {
  // BUG: shallow copy spreads nested object reference
  const copy = { ...config };
  if (overrides.db) {
    Object.assign(copy.db, overrides.db);
  }
  return copy;
}
module.exports = { cloneConfig };
