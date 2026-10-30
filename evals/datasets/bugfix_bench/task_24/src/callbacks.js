function createCallbacks(n) {
  var cbs = [];
  // BUG: var i is function scoped
  for (var i = 0; i < n; i++) {
    cbs.push(() => i);
  }
  return cbs;
}
module.exports = { createCallbacks };
