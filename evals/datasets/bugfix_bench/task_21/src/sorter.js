function sortNumbers(arr) {
  // BUG: arr.sort() without comparator sorts as strings: [10, 2, 5] -> [10, 2, 5]
  return arr.sort();
}
module.exports = { sortNumbers };
