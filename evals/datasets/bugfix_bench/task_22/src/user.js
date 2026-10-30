async function fetchUserName(id) {
  return "Alice";
}

async function getUserDisplayName(id) {
  // BUG: missing await
  const name = fetchUserName(id);
  return `User: ${name}`;
}
module.exports = { getUserDisplayName };
