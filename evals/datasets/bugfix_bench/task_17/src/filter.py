def remove_evens(nums):
    # BUG: mutating list while iterating over it
    for n in nums:
        if n % 2 == 0:
            nums.remove(n)
    return nums
