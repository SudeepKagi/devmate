function getUserCity(user) {
  // BUG: crashes if address is undefined
  return user.address.city;
}
module.exports = { getUserCity };
