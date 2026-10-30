"""
Generator script for the Devmate Bug-Fix Benchmark (25 tasks).
Creates 25 self-contained task folders in evals/datasets/bugfix_bench/
"""

import json
import os
from pathlib import Path

BASE_DIR = Path("evals/datasets/bugfix_bench")


def create_task(task_id: str, language: str, category: str, description: str, files: dict, existing_test: str, failing_test: str, hidden_test: str, test_cmd: str):
    task_dir = BASE_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    src_dir = task_dir / "src"
    src_dir.mkdir(exist_ok=True)
    tests_dir = task_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    for filename, content in files.items():
        (src_dir / filename).write_text(content.strip() + "\n", encoding="utf-8")

    test_ext = ".py" if language == "python" else ".js"
    (tests_dir / f"test_existing{test_ext}").write_text(existing_test.strip() + "\n", encoding="utf-8")
    (tests_dir / f"test_failing{test_ext}").write_text(failing_test.strip() + "\n", encoding="utf-8")
    (tests_dir / f"test_hidden{test_ext}").write_text(hidden_test.strip() + "\n", encoding="utf-8")

    meta = {
        "task_id": task_id,
        "language": language,
        "category": category,
        "description": description,
        "test_command": test_cmd,
        "failing_test": f"tests/test_failing{test_ext}",
        "existing_test": f"tests/test_existing{test_ext}",
        "hidden_test": f"tests/test_hidden{test_ext}",
        "target_file": list(files.keys())[0],
    }
    (task_dir / "task.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def generate_all():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Off-by-one in pagination
    create_task(
        "task_01", "python", "off_by_one",
        "paginate_items returns 1 extra item on every page due to an off-by-one end slice.",
        {"pagination.py": """
def paginate(items, page=1, page_size=10):
    if page < 1 or page_size < 1:
        return []
    start = (page - 1) * page_size
    end = start + page_size + 1  # BUG: extra +1
    return items[start:end]
"""},
        """
from src.pagination import paginate
def test_empty():
    assert paginate([], 1, 5) == []
def test_invalid_page():
    assert paginate([1, 2, 3], 0, 5) == []
""",
        """
from src.pagination import paginate
def test_page_size():
    items = list(range(20))
    res = paginate(items, page=1, page_size=5)
    assert len(res) == 5, f"Expected 5 items, got {len(res)}"
""",
        """
from src.pagination import paginate
def test_hidden_second_page():
    items = list(range(20))
    assert paginate(items, page=2, page_size=5) == [5, 6, 7, 8, 9]
def test_hidden_last_page():
    items = list(range(7))
    assert paginate(items, page=2, page_size=5) == [5, 6]
""",
        "python -m pytest tests/test_failing.py"
    )

    # 2. Mutable default argument
    create_task(
        "task_02", "python", "mutable_default",
        "RoleManager.add_role mutates default roles list across instances.",
        {"roles.py": """
class RoleManager:
    def __init__(self, initial_roles=[]):  # BUG: mutable default
        self.roles = initial_roles

    def add_role(self, role):
        self.roles.append(role)
        return self.roles
"""},
        """
from src.roles import RoleManager
def test_explicit_roles():
    mgr = RoleManager(["admin"])
    assert mgr.roles == ["admin"]
""",
        """
from src.roles import RoleManager
def test_instance_isolation():
    mgr1 = RoleManager()
    mgr1.add_role("editor")
    mgr2 = RoleManager()
    assert mgr2.roles == [], f"Expected empty roles, got {mgr2.roles}"
""",
        """
from src.roles import RoleManager
def test_hidden_multiple():
    m1 = RoleManager()
    m2 = RoleManager()
    m1.add_role("viewer")
    assert "viewer" not in m2.roles
    assert len(m2.roles) == 0
""",
        "python -m pytest tests/test_failing.py"
    )

    # 3. Wrong operator in discount calculator
    create_task(
        "task_03", "python", "wrong_operator",
        "Discount calculator uses > instead of >= for the tier boundary at 100.",
        {"discounts.py": """
def calculate_discount(total):
    if total > 100:  # BUG: should be >= 100
        return total * 0.10
    return 0.0
"""},
        """
from src.discounts import calculate_discount
def test_small_total():
    assert calculate_discount(50) == 0.0
def test_large_total():
    assert calculate_discount(200) == 20.0
""",
        """
from src.discounts import calculate_discount
def test_boundary_tier():
    assert calculate_discount(100) == 10.0, "Total of 100 should qualify for 10% discount"
""",
        """
from src.discounts import calculate_discount
def test_hidden_zero():
    assert calculate_discount(0) == 0.0
def test_hidden_fraction():
    assert calculate_discount(99.99) == 0.0
    assert calculate_discount(100.01) == pytest.approx(10.001)
import pytest
""",
        "python -m pytest tests/test_failing.py"
    )

    # 4. Missing None check in nested dict lookup
    create_task(
        "task_04", "python", "missing_null_check",
        "get_user_setting crashes with AttributeError when user profile is None.",
        {"settings.py": """
def get_user_setting(user, setting_name, default=None):
    profile = user.get("profile")
    # BUG: profile can be None
    return profile.get("settings", {}).get(setting_name, default)
"""},
        """
from src.settings import get_user_setting
def test_valid_profile():
    user = {"profile": {"settings": {"theme": "dark"}}}
    assert get_user_setting(user, "theme") == "dark"
""",
        """
from src.settings import get_user_setting
def test_none_profile():
    user = {"profile": None}
    assert get_user_setting(user, "theme", "light") == "light"
""",
        """
from src.settings import get_user_setting
def test_hidden_missing_profile_key():
    assert get_user_setting({}, "theme", "blue") == "blue"
def test_hidden_empty_settings():
    assert get_user_setting({"profile": {"settings": None}}, "k", "def") == "def"
""",
        "python -m pytest tests/test_failing.py"
    )

    # 5. Dict key error on missing optional field
    create_task(
        "task_05", "python", "dict_key_error",
        "parse_headers raises KeyError when Authorization header is absent.",
        {"headers.py": """
def get_auth_token(headers):
    # BUG: direct indexing without check
    val = headers["Authorization"]
    if val.startswith("Bearer "):
        return val[7:]
    return val
"""},
        """
from src.headers import get_auth_token
def test_valid_bearer():
    assert get_auth_token({"Authorization": "Bearer secret123"}) == "secret123"
""",
        """
from src.headers import get_auth_token
def test_missing_auth():
    assert get_auth_token({}) is None
""",
        """
from src.headers import get_auth_token
def test_hidden_case_insensitive():
    # If case sensitivity or plain token
    assert get_auth_token({"Authorization": "token_abc"}) == "token_abc"
def test_hidden_none_headers():
    assert get_auth_token({"Content-Type": "application/json"}) is None
""",
        "python -m pytest tests/test_failing.py"
    )

    # 6. Wrong sort order in priority queue
    create_task(
        "task_06", "python", "wrong_sort_order",
        "PriorityQueue sorts lowest number first instead of highest priority first.",
        {"queue.py": """
class PriorityQueue:
    def __init__(self):
        self._items = []

    def push(self, item, priority):
        self._items.append((priority, item))
        # BUG: ascending order instead of descending
        self._items.sort(key=lambda x: x[0])

    def pop(self):
        if not self._items:
            return None
        return self._items.pop(0)[1]
"""},
        """
from src.queue import PriorityQueue
def test_single_item():
    pq = PriorityQueue()
    pq.push("task", 5)
    assert pq.pop() == "task"
""",
        """
from src.queue import PriorityQueue
def test_priority_order():
    pq = PriorityQueue()
    pq.push("low", 1)
    pq.push("high", 10)
    assert pq.pop() == "high"
""",
        """
from src.queue import PriorityQueue
def test_hidden_multiple():
    pq = PriorityQueue()
    pq.push("mid", 5)
    pq.push("high", 10)
    pq.push("low", 1)
    assert pq.pop() == "high"
    assert pq.pop() == "mid"
    assert pq.pop() == "low"
    assert pq.pop() is None
""",
        "python -m pytest tests/test_failing.py"
    )

    # 7. Unawaited coroutine in async cache
    create_task(
        "task_07", "python", "bad_async_handling",
        "fetch_with_cache returns coroutine object instead of resolved value.",
        {"async_cache.py": """
import asyncio

async def fetch_data(key):
    await asyncio.sleep(0.01)
    return f"data_for_{key}"

async def get_cached(cache, key):
    if key in cache:
        return cache[key]
    val = fetch_data(key)  # BUG: missing await
    cache[key] = val
    return val
"""},
        """
import pytest
from src.async_cache import get_cached

@pytest.mark.asyncio
async def test_cache_hit():
    cache = {"a": "cached_a"}
    assert await get_cached(cache, "a") == "cached_a"
""",
        """
import pytest
from src.async_cache import get_cached

@pytest.mark.asyncio
async def test_cache_miss_resolved():
    cache = {}
    val = await get_cached(cache, "b")
    assert isinstance(val, str), f"Expected str, got {type(val)}"
    assert val == "data_for_b"
""",
        """
import pytest
from src.async_cache import get_cached

@pytest.mark.asyncio
async def test_hidden_cache_population():
    cache = {}
    val1 = await get_cached(cache, "c")
    assert val1 == "data_for_c"
    assert cache["c"] == "data_for_c"
""",
        "python -m pytest tests/test_failing.py"
    )

    # 8. Boundary condition in date/range filtering
    create_task(
        "task_08", "python", "boundary_condition",
        "in_range excludes maximum value due to < instead of <=.",
        {"validator.py": """
def in_range(val, min_val, max_val):
    # BUG: val < max_val excludes max_val
    return min_val <= val < max_val
"""},
        """
from src.validator import in_range
def test_middle():
    assert in_range(5, 1, 10) is True
def test_below():
    assert in_range(0, 1, 10) is False
""",
        """
from src.validator import in_range
def test_max_boundary():
    assert in_range(10, 1, 10) is True, "Upper boundary should be inclusive"
""",
        """
from src.validator import in_range
def test_hidden_min_boundary():
    assert in_range(1, 1, 10) is True
def test_hidden_above():
    assert in_range(11, 1, 10) is False
""",
        "python -m pytest tests/test_failing.py"
    )

    # 9. Type coercion in query parameters
    create_task(
        "task_09", "python", "type_coercion",
        "parse_port leaves port as string instead of int.",
        {"config.py": """
def parse_port(params, default=8000):
    val = params.get("port")
    if val is None:
        return default
    # BUG: forgets to cast str to int
    return val
"""},
        """
from src.config import parse_port
def test_default():
    assert parse_port({}) == 8000
""",
        """
from src.config import parse_port
def test_port_is_integer():
    p = parse_port({"port": "9000"})
    assert isinstance(p, int), f"Expected int, got {type(p)}"
    assert p == 9000
""",
        """
from src.config import parse_port
def test_hidden_invalid():
    # already int
    assert parse_port({"port": 3000}) == 3000
""",
        "python -m pytest tests/test_failing.py"
    )

    # 10. Regex boundary anchor missing
    create_task(
        "task_10", "python", "regex_boundary",
        "is_valid_uuid accepts invalid strings containing a UUID substring.",
        {"uuid_validator.py": """
import re

UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

def is_valid_uuid(s):
    # BUG: re.search without ^ and $ anchors
    return bool(UUID_PATTERN.search(s))
"""},
        """
from src.uuid_validator import is_valid_uuid
def test_valid():
    assert is_valid_uuid("12345678-1234-1234-1234-123456789abc") is True
""",
        """
from src.uuid_validator import is_valid_uuid
def test_invalid_prefix():
    assert is_valid_uuid("prefix-12345678-1234-1234-1234-123456789abc-suffix") is False
""",
        """
from src.uuid_validator import is_valid_uuid
def test_hidden_short():
    assert is_valid_uuid("1234") is False
    assert is_valid_uuid("") is False
""",
        "python -m pytest tests/test_failing.py"
    )

    # 11. State leak in singleton metrics aggregator
    create_task(
        "task_11", "python", "state_leak",
        "Aggregator.reset() fails to clear counts dictionary.",
        {"aggregator.py": """
class Aggregator:
    _counts = {}

    def record(self, key):
        self._counts[key] = self._counts.get(key, 0) + 1

    def get_count(self, key):
        return self._counts.get(key, 0)

    def reset(self):
        # BUG: rebinds local variable instead of clearing class dict
        self._counts = {}
"""},
        """
from src.aggregator import Aggregator
def test_record():
    a = Aggregator()
    a.record("a")
    assert a.get_count("a") >= 1
""",
        """
from src.aggregator import Aggregator
def test_reset():
    a = Aggregator()
    a.record("x")
    a.reset()
    assert a.get_count("x") == 0
""",
        """
from src.aggregator import Aggregator
def test_hidden_new_instance():
    a1 = Aggregator()
    a1.reset()
    a1.record("k")
    a2 = Aggregator()
    a2.reset()
    assert a1.get_count("k") == 0
""",
        "python -m pytest tests/test_failing.py"
    )

    # 12. LRU cache invalidation order
    create_task(
        "task_12", "python", "cache_invalidation",
        "LRUCache does not mark hit item as recently used.",
        {"lru.py": """
class LRUCache:
    def __init__(self, capacity=2):
        self.capacity = capacity
        self.cache = {}
        self.order = []

    def get(self, key):
        if key not in self.cache:
            return None
        # BUG: missing self.order.remove(key); self.order.append(key)
        return self.cache[key]

    def put(self, key, val):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        self.cache[key] = val
        self.order.append(key)
"""},
        """
from src.lru import LRUCache
def test_basic_put_get():
    c = LRUCache(2)
    c.put("a", 1)
    assert c.get("a") == 1
""",
        """
from src.lru import LRUCache
def test_access_updates_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")  # "a" accessed, so "b" is now oldest
    c.put("c", 3)  # should evict "b", keeping "a" and "c"
    assert c.get("b") is None
    assert c.get("a") == 1
""",
        """
from src.lru import LRUCache
def test_hidden_evict():
    c = LRUCache(2)
    c.put("x", 10)
    c.put("y", 20)
    c.put("z", 30)
    assert c.get("x") is None
    assert c.get("y") == 20
    assert c.get("z") == 30
""",
        "python -m pytest tests/test_failing.py"
    )

    # 13. Float precision in financial sum
    create_task(
        "task_13", "python", "float_precision",
        "calculate_tax produces unrounded floating point representation.",
        {"tax.py": """
def calculate_tax(subtotal, rate=0.07):
    # BUG: raw float product without round
    return subtotal * rate
"""},
        """
from src.tax import calculate_tax
def test_simple_tax():
    assert calculate_tax(100.0) == 7.0
""",
        """
from src.tax import calculate_tax
def test_precision_rounding():
    # 19.99 * 0.07 = 1.3993 -> should round to 2 decimals 1.40
    res = calculate_tax(19.99, 0.07)
    assert res == 1.40
""",
        """
from src.tax import calculate_tax
def test_hidden_zero():
    assert calculate_tax(0) == 0.0
def test_hidden_cents():
    assert calculate_tax(10.55, 0.05) == 0.53
""",
        "python -m pytest tests/test_failing.py"
    )

    # 14. Deep copy missing in template cloner
    create_task(
        "task_14", "python", "deep_copy_missing",
        "create_config mutates shared nested template dict.",
        {"cloner.py": """
BASE_TEMPLATE = {
    "version": "1.0",
    "features": {"logging": True, "auth": True}
}

def create_config(overrides=None):
    # BUG: shallow copy of dict containing nested dict
    conf = BASE_TEMPLATE.copy()
    if overrides:
        conf["features"].update(overrides)
    return conf
"""},
        """
from src.cloner import create_config
def test_base_config():
    c = create_config()
    assert c["version"] == "1.0"
""",
        """
from src.cloner import create_config, BASE_TEMPLATE
def test_isolated_templates():
    c1 = create_config({"auth": False})
    assert BASE_TEMPLATE["features"]["auth"] is True, "BASE_TEMPLATE was corrupted!"
""",
        """
from src.cloner import create_config
def test_hidden_independent():
    c1 = create_config({"auth": False})
    c2 = create_config()
    assert c2["features"]["auth"] is True
""",
        "python -m pytest tests/test_failing.py"
    )

    # 15. String slicing in slug generator
    create_task(
        "task_15", "python", "string_slice",
        "slugify leaves trailing hyphens when trimming.",
        {"slug.py": """
import re

def slugify(text):
    text = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", text)
    # BUG: wrong slice or missing strip('-')
    if slug.startswith("-"):
        slug = slug[1:]
    return slug
"""},
        """
from src.slug import slugify
def test_normal():
    assert slugify("Hello World") == "hello-world"
""",
        """
from src.slug import slugify
def test_trailing_punctuation():
    assert slugify("Hello World!") == "hello-world"
""",
        """
from src.slug import slugify
def test_hidden_both_ends():
    assert slugify("---Test Title---") == "test-title"
def test_hidden_symbols():
    assert slugify("Special @#$ Chars") == "special-chars"
""",
        "python -m pytest tests/test_failing.py"
    )

    # 16. Circular buffer index wrap
    create_task(
        "task_16", "python", "index_out_of_bounds",
        "CircularBuffer read past capacity causes IndexError.",
        {"buffer.py": """
class CircularBuffer:
    def __init__(self, size=3):
        self.size = size
        self.data = [None] * size
        self.write_idx = 0
        self.count = 0

    def append(self, val):
        self.data[self.write_idx] = val
        self.write_idx = (self.write_idx + 1) % self.size
        if self.count < self.size:
            self.count += 1

    def get_all(self):
        # BUG: doesn't handle read order when wrapped
        if self.count < self.size:
            return self.data[:self.count]
        # When full, oldest item is at write_idx
        res = []
        for i in range(self.size):
            idx = (self.write_idx + i) % self.size
            res.append(self.data[idx])
        return res
"""},
        """
from src.buffer import CircularBuffer
def test_partial():
    b = CircularBuffer(3)
    b.append(1)
    b.append(2)
    assert b.get_all() == [1, 2]
""",
        """
from src.buffer import CircularBuffer
def test_wrapped_order():
    b = CircularBuffer(3)
    b.append(1)
    b.append(2)
    b.append(3)
    b.append(4)  # overwrites 1, buffer now [4, 2, 3], write_idx=1 -> oldest is 2
    assert b.get_all() == [2, 3, 4]
""",
        """
from src.buffer import CircularBuffer
def test_hidden_multiple_wraps():
    b = CircularBuffer(2)
    b.append("a")
    b.append("b")
    b.append("c")
    assert b.get_all() == ["b", "c"]
""",
        "python -m pytest tests/test_failing.py"
    )

    # 17. List mutation during iteration
    create_task(
        "task_17", "python", "list_mutation_during_iter",
        "remove_evens skips adjacent even numbers due to mutating list during iteration.",
        {"filter.py": """
def remove_evens(nums):
    # BUG: mutating list while iterating over it
    for n in nums:
        if n % 2 == 0:
            nums.remove(n)
    return nums
"""},
        """
from src.filter import remove_evens
def test_single():
    assert remove_evens([1, 2, 3]) == [1, 3]
""",
        """
from src.filter import remove_evens
def test_adjacent_evens():
    assert remove_evens([2, 4, 6, 8]) == []
""",
        """
from src.filter import remove_evens
def test_hidden_odds():
    assert remove_evens([1, 3, 5]) == [1, 3, 5]
def test_hidden_mixed():
    assert remove_evens([1, 2, 2, 3, 4, 4, 5]) == [1, 3, 5]
""",
        "python -m pytest tests/test_failing.py"
    )

    # 18. Reversed boolean logic in permission checker
    create_task(
        "task_18", "python", "reversed_boolean_logic",
        "is_ip_allowed returns True for blacklisted IPs.",
        {"firewall.py": """
BLACKLIST = {"192.168.1.100", "10.0.0.5"}

def is_ip_allowed(ip):
    # BUG: reversed condition
    if ip in BLACKLIST:
        return True
    return False
"""},
        """
from src.firewall import is_ip_allowed
def test_normal_ip():
    # This was passing only because logic was inverted
    pass
""",
        """
from src.firewall import is_ip_allowed
def test_blocked_ip():
    assert is_ip_allowed("192.168.1.100") is False
""",
        """
from src.firewall import is_ip_allowed
def test_hidden_allowed():
    assert is_ip_allowed("8.8.8.8") is True
def test_hidden_second_blacklist():
    assert is_ip_allowed("10.0.0.5") is False
""",
        "python -m pytest tests/test_failing.py"
    )

    # 19. JSON serialization failure on datetime
    create_task(
        "task_19", "python", "json_serialization_failure",
        "serialize_event raises TypeError when event contains datetime.",
        {"serializer.py": """
import json
from datetime import datetime

def serialize_event(data):
    # BUG: doesn't provide custom default serializer
    return json.dumps(data)
"""},
        """
from src.serializer import serialize_event
def test_plain_data():
    assert serialize_event({"msg": "hello"}) == '{"msg": "hello"}'
""",
        """
from datetime import datetime
from src.serializer import serialize_event
def test_datetime_serialization():
    dt = datetime(2026, 1, 1, 12, 0, 0)
    res = serialize_event({"timestamp": dt})
    assert "2026-01-01" in res
""",
        """
from datetime import date
from src.serializer import serialize_event
def test_hidden_date():
    res = serialize_event({"day": date(2026, 5, 10)})
    assert "2026-05-10" in res
""",
        "python -m pytest tests/test_failing.py"
    )

    # 20. Zero division error on empty array
    create_task(
        "task_20", "python", "unhandled_exception",
        "calculate_average raises ZeroDivisionError on empty list.",
        {"stats.py": """
def calculate_average(numbers):
    # BUG: no check for empty list
    return sum(numbers) / len(numbers)
"""},
        """
from src.stats import calculate_average
def test_normal_list():
    assert calculate_average([10, 20, 30]) == 20.0
""",
        """
from src.stats import calculate_average
def test_empty_list():
    assert calculate_average([]) == 0.0
""",
        """
from src.stats import calculate_average
def test_hidden_single():
    assert calculate_average([5]) == 5.0
def test_hidden_negative():
    assert calculate_average([-5, 5]) == 0.0
""",
        "python -m pytest tests/test_failing.py"
    )

    # 21. JS Array Sort lexicographical bug
    create_task(
        "task_21", "javascript", "js_array_sort",
        "sortNumbers sorts numerically instead of lexicographically.",
        {"sorter.js": """
function sortNumbers(arr) {
  // BUG: arr.sort() without comparator sorts as strings: [10, 2, 5] -> [10, 2, 5]
  return arr.sort();
}
module.exports = { sortNumbers };
"""},
        """
const assert = require("assert");
const { test } = require("node:test");
const { sortNumbers } = require("../src/sorter.js");

test("single element", () => {
  assert.deepStrictEqual(sortNumbers([1]), [1]);
});
""",
        """
const assert = require("assert");
const { test } = require("node:test");
const { sortNumbers } = require("../src/sorter.js");

test("numerical sort order", () => {
  assert.deepStrictEqual(sortNumbers([10, 2, 5]), [2, 5, 10]);
});
""",
        """
const assert = require("assert");
const { test } = require("node:test");
const { sortNumbers } = require("../src/sorter.js");

test("hidden negatives and large numbers", () => {
  assert.deepStrictEqual(sortNumbers([100, -5, 20, 0]), [-5, 0, 20, 100]);
});
""",
        "node --test tests/test_failing.js"
    )

    # 22. JS missing await
    create_task(
        "task_22", "javascript", "js_async_await",
        "getUserDisplayName returns [object Promise] instead of resolved string.",
        {"user.js": """
async function fetchUserName(id) {
  return "Alice";
}

async function getUserDisplayName(id) {
  // BUG: missing await
  const name = fetchUserName(id);
  return `User: ${name}`;
}
module.exports = { getUserDisplayName };
"""},
        """
const assert = require("assert");
const { test } = require("node:test");
test("placeholder", () => { assert.strictEqual(1, 1); });
""",
        """
const assert = require("assert");
const { test } = require("node:test");
const { getUserDisplayName } = require("../src/user.js");

test("displayName resolves value", async () => {
  const res = await getUserDisplayName(1);
  assert.strictEqual(res, "User: Alice");
});
""",
        """
const assert = require("assert");
const { test } = require("node:test");
const { getUserDisplayName } = require("../src/user.js");

test("hidden check not containing promise", async () => {
  const res = await getUserDisplayName(99);
  assert.ok(!res.includes("[object Promise]"));
});
""",
        "node --test tests/test_failing.js"
    )

    # 23. JS null/undefined property access
    create_task(
        "task_23", "javascript", "js_null_undefined",
        "getUserCity crashes when address is undefined.",
        {"address.js": """
function getUserCity(user) {
  // BUG: crashes if address is undefined
  return user.address.city;
}
module.exports = { getUserCity };
"""},
        """
const assert = require("assert");
const { test } = require("node:test");
const { getUserCity } = require("../src/address.js");

test("valid user", () => {
  assert.strictEqual(getUserCity({ address: { city: "Paris" } }), "Paris");
});
""",
        """
const assert = require("assert");
const { test } = require("node:test");
const { getUserCity } = require("../src/address.js");

test("missing address returns undefined", () => {
  assert.strictEqual(getUserCity({}), undefined);
});
""",
        """
const assert = require("assert");
const { test } = require("node:test");
const { getUserCity } = require("../src/address.js");

test("hidden null address", () => {
  assert.strictEqual(getUserCity({ address: null }), undefined);
});
""",
        "node --test tests/test_failing.js"
    )

    # 24. JS scope closure bug
    create_task(
        "task_24", "javascript", "js_scope_closure",
        "createCallbacks creates closures all returning final loop value.",
        {"callbacks.js": """
function createCallbacks(n) {
  var cbs = [];
  // BUG: var i is function scoped
  for (var i = 0; i < n; i++) {
    cbs.push(() => i);
  }
  return cbs;
}
module.exports = { createCallbacks };
"""},
        """
const assert = require("assert");
const { test } = require("node:test");
const { createCallbacks } = require("../src/callbacks.js");

test("length", () => {
  assert.strictEqual(createCallbacks(3).length, 3);
});
""",
        """
const assert = require("assert");
const { test } = require("node:test");
const { createCallbacks } = require("../src/callbacks.js");

test("closure values", () => {
  const cbs = createCallbacks(3);
  assert.strictEqual(cbs[0](), 0);
  assert.strictEqual(cbs[1](), 1);
  assert.strictEqual(cbs[2](), 2);
});
""",
        """
const assert = require("assert");
const { test } = require("node:test");
const { createCallbacks } = require("../src/callbacks.js");

test("hidden single", () => {
  const cbs = createCallbacks(1);
  assert.strictEqual(cbs[0](), 0);
});
""",
        "node --test tests/test_failing.js"
    )

    # 25. JS shallow spread mutation
    create_task(
        "task_25", "javascript", "js_deep_clone",
        "cloneConfig shallow clone mutates nested options object.",
        {"config.js": """
function cloneConfig(config, overrides = {}) {
  // BUG: shallow copy spreads nested object reference
  const copy = { ...config };
  if (overrides.db) {
    Object.assign(copy.db, overrides.db);
  }
  return copy;
}
module.exports = { cloneConfig };
"""},
        """
const assert = require("assert");
const { test } = require("node:test");
const { cloneConfig } = require("../src/config.js");

test("shallow copy", () => {
  assert.strictEqual(cloneConfig({ env: "prod" }).env, "prod");
});
""",
        """
const assert = require("assert");
const { test } = require("node:test");
const { cloneConfig } = require("../src/config.js");

test("isolated nested db", () => {
  const original = { db: { port: 5432 } };
  const cloned = cloneConfig(original, { db: { port: 5433 } });
  assert.strictEqual(original.db.port, 5432, "Original was modified!");
  assert.strictEqual(cloned.db.port, 5433);
});
""",
        """
const assert = require("assert");
const { test } = require("node:test");
const { cloneConfig } = require("../src/config.js");

test("hidden multi level", () => {
  const orig = { db: { host: "localhost" } };
  const cl = cloneConfig(orig, { db: { host: "remote" } });
  assert.strictEqual(orig.db.host, "localhost");
});
""",
        "node --test tests/test_failing.js"
    )

    print("Successfully generated 25 benchmark tasks in", BASE_DIR)


if __name__ == "__main__":
    generate_all()

