import os
import shutil
import tempfile
from pathlib import Path
import pytest

from devmate.config import config
from devmate.safety.sandbox import (
    validate_workspace_path,
    SecurityError,
    build_sanitized_env,
    execute_sandboxed_command,
    is_sandbox_enabled,
)
from devmate.tools.filesystem_tools import read_file, write_file, update_file, delete_file


@pytest.fixture
def jail_workspace(tmp_path):
    ws = tmp_path / "sandbox_workspace"
    ws.mkdir()
    (ws / "valid.txt").write_text("safe content", encoding="utf-8")
    yield ws
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_path_traversal_blocked(jail_workspace):
    # Relative path escaping workspace
    with pytest.raises(SecurityError) as exc_info:
        validate_workspace_path("../outside.txt", workspace_root=jail_workspace)
    assert "outside workspace jail" in str(exc_info.value)

    # Deep traversal
    with pytest.raises(SecurityError):
        validate_workspace_path("../../../etc/passwd", workspace_root=jail_workspace)


def test_absolute_path_outside_jail_blocked(jail_workspace):
    outside_file = jail_workspace.parent / "outside.txt"
    outside_file.write_text("secret", encoding="utf-8")

    with pytest.raises(SecurityError):
        validate_workspace_path(str(outside_file), workspace_root=jail_workspace)


def test_valid_path_inside_jail(jail_workspace):
    valid = validate_workspace_path("valid.txt", workspace_root=jail_workspace)
    assert valid.exists()
    assert valid.name == "valid.txt"

    nested = validate_workspace_path("nested/sub.txt", workspace_root=jail_workspace)
    assert nested.parent.name == "nested"


def test_symlink_escape_blocked(jail_workspace):
    outside_file = jail_workspace.parent / "host_secret.txt"
    outside_file.write_text("super_secret", encoding="utf-8")

    symlink_path = jail_workspace / "evil_symlink.txt"
    try:
        os.symlink(str(outside_file), str(symlink_path))
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation requires elevated privileges on this Windows configuration")

    with pytest.raises(SecurityError) as exc_info:
        validate_workspace_path(str(symlink_path), workspace_root=jail_workspace)
    assert "Symlink escape blocked" in str(exc_info.value) or "Path traversal blocked" in str(exc_info.value)


def test_filesystem_tools_respect_path_jail(jail_workspace):
    orig = config.get("sandbox", {}).get("enabled", False)
    try:
        config["sandbox"]["enabled"] = True

        # read_file outside
        res_read = read_file.invoke({"path": "../../sensitive.txt"})
        assert "SecurityError" in res_read

        # write_file outside
        res_write = write_file.invoke({"path": "../unauthorized.txt", "content": "attack"})
        assert "SecurityError" in res_write

        # update_file outside
        res_update = update_file.invoke({"path": "../unauthorized.txt", "old_text": "a", "new_text": "b"})
        assert "SecurityError" in res_update

        # delete_file outside
        res_del = delete_file.invoke({"path": "../unauthorized.txt"})
        assert "SecurityError" in res_del
    finally:
        config["sandbox"]["enabled"] = orig


def test_environment_secret_scrubbing():
    os.environ["OPENAI_API_KEY"] = "sk-test-secret-key-12345"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "aws-secret-abc"
    os.environ["SAFE_PUBLIC_VAR"] = "public_value"

    clean_env = build_sanitized_env()
    assert "OPENAI_API_KEY" not in clean_env
    assert "AWS_SECRET_ACCESS_KEY" not in clean_env
    assert clean_env.get("SAFE_PUBLIC_VAR") == "public_value"
    assert clean_env.get("DEVMATE_SANDBOX") == "1"


def test_execution_timeout_enforcement():
    # Run command that exceeds timeout
    code, stdout, stderr, meta = execute_sandboxed_command(
        'python -c "import time; time.sleep(5)"',
        timeout=1,
    )
    assert code == -1
    assert "timed out" in stderr.lower()
    assert meta.get("timeout") is True

