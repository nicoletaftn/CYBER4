#!/usr/bin/env python3
"""
Tests for the out-of-scope domain / subdomain filter built into _ToolRouterHook.

Each test simulates the AI making a tool call "as the agent" and verifies
whether the call is blocked/rewritten (out-of-scope domain) or passed through
unchanged (in-scope / normal routing).

Current out_of_scope.txt [DOMAINS] entries:
    admin.juice-shop.com
    staging.juice-shop.com
    internal.juice-shop.local
"""

import types
from pathlib import Path

import pytest

from modules.agents import cyber_autoagent as ca


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

# Mirrors the three entries currently in the [DOMAINS] section of out_of_scope.txt
SAMPLE_DOMAINS = [
    "admin.juice-shop.com",
    "staging.juice-shop.com",
    "internal.juice-shop.local",
]

# Minimal valid file content with section headers for use in tmp-file tests
_OOS_FILE_CONTENT = (
    "# comment\n"
    "\n"
    "[ENDPOINTS]\n"
    "/contact\n"
    "\n"
    "[DOMAINS]\n"
    "admin.juice-shop.com\n"
    "  staging.juice-shop.com  \n"
    "internal.juice-shop.local\n"
)


def _make_hook(domains: list[str] | None = None) -> ca._ToolRouterHook:
    """Return a hook pre-loaded with *domains* (bypasses file I/O)."""
    sentinel_shell = object()
    hook = ca._ToolRouterHook(shell_tool=sentinel_shell)
    hook._out_of_scope_endpoints = []
    hook._out_of_scope_domains = domains if domains is not None else list(SAMPLE_DOMAINS)
    hook._shell_tool = sentinel_shell
    return hook


def _make_event(
    tool_name: str,
    tool_input: dict,
    selected_tool=None,
) -> types.SimpleNamespace:
    event = types.SimpleNamespace()
    event.selected_tool = selected_tool
    event.tool_use = {"name": tool_name, "input": tool_input}
    return event


# ---------------------------------------------------------------------------
# _load_out_of_scope_domains unit tests
# ---------------------------------------------------------------------------


class TestLoadOutOfScopeDomains:
    def test_returns_empty_list_for_missing_file(self, tmp_path):
        result = ca._load_out_of_scope_domains(tmp_path / "nonexistent.txt")
        assert result == []

    def test_parses_domains_correctly(self, tmp_path):
        f = tmp_path / "oos.txt"
        f.write_text(_OOS_FILE_CONTENT)
        result = ca._load_out_of_scope_domains(f)
        assert result == ["admin.juice-shop.com", "staging.juice-shop.com", "internal.juice-shop.local"]

    def test_ignores_blank_lines_and_comments(self, tmp_path):
        f = tmp_path / "oos.txt"
        f.write_text("[DOMAINS]\n# only comments\n\n# another comment\n")
        assert ca._load_out_of_scope_domains(f) == []

    def test_returns_empty_list_for_empty_file(self, tmp_path):
        f = tmp_path / "oos.txt"
        f.write_text("")
        assert ca._load_out_of_scope_domains(f) == []

    def test_does_not_bleed_into_endpoints_section(self, tmp_path):
        f = tmp_path / "oos.txt"
        f.write_text(
            "[ENDPOINTS]\n"
            "/contact\n"
            "[DOMAINS]\n"
            "admin.juice-shop.com\n"
        )
        result = ca._load_out_of_scope_domains(f)
        assert result == ["admin.juice-shop.com"]
        assert "/contact" not in result

    def test_no_domains_section_returns_empty(self, tmp_path):
        f = tmp_path / "oos.txt"
        f.write_text("[ENDPOINTS]\n/contact\n")
        assert ca._load_out_of_scope_domains(f) == []


# ---------------------------------------------------------------------------
# _find_out_of_scope_domain unit tests
# ---------------------------------------------------------------------------


class TestFindOutOfScopeDomain:
    def test_finds_admin_subdomain_in_full_url(self):
        url = "http://admin.juice-shop.com/api/admin"
        result = ca._find_out_of_scope_domain(url, SAMPLE_DOMAINS)
        assert result == "admin.juice-shop.com"

    def test_finds_staging_subdomain_inside_curl_command(self):
        cmd = "curl -s 'https://staging.juice-shop.com/rest/products'"
        result = ca._find_out_of_scope_domain(cmd, SAMPLE_DOMAINS)
        assert result == "staging.juice-shop.com"

    def test_finds_internal_subdomain(self):
        cmd = "nmap -sV internal.juice-shop.local"
        result = ca._find_out_of_scope_domain(cmd, SAMPLE_DOMAINS)
        assert result == "internal.juice-shop.local"

    def test_returns_none_for_in_scope_domain(self):
        url = "http://localhost:3000/api/products"
        result = ca._find_out_of_scope_domain(url, SAMPLE_DOMAINS)
        assert result is None

    def test_returns_none_with_empty_domains_list(self):
        result = ca._find_out_of_scope_domain("http://admin.juice-shop.com", [])
        assert result is None

    def test_returns_first_matching_domain(self):
        # Command contains two out-of-scope domains; first in list should win
        cmd = "curl http://admin.juice-shop.com && curl http://staging.juice-shop.com"
        result = ca._find_out_of_scope_domain(cmd, SAMPLE_DOMAINS)
        assert result == "admin.juice-shop.com"

    def test_does_not_match_partial_domain_name(self):
        # "shop.com" alone should not match "admin.juice-shop.com"
        result = ca._find_out_of_scope_domain("http://shop.com", SAMPLE_DOMAINS)
        assert result is None


# ---------------------------------------------------------------------------
# _ToolRouterHook – out-of-scope domain blocking (known tools)
# ---------------------------------------------------------------------------


class TestOutOfScopeDomainBlocking:
    """Simulate the AI sending tool calls that target out-of-scope domains."""

    # ── shell tool ──────────────────────────────────────────────────────────

    def test_shell_curl_to_admin_subdomain_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "curl -s https://admin.juice-shop.com/dashboard"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert cmd.startswith("echo 'OUT_OF_SCOPE")
        assert "admin.juice-shop.com" in cmd

    def test_shell_wget_to_staging_subdomain_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "wget https://staging.juice-shop.com/rest/user/whoami -O -"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "staging.juice-shop.com" in cmd

    def test_shell_nmap_against_internal_host_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "nmap -sV internal.juice-shop.local"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "internal.juice-shop.local" in cmd

    # ── http_request tool ───────────────────────────────────────────────────

    def test_http_request_to_admin_subdomain_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "https://admin.juice-shop.com/api/users", "method": "GET"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "admin.juice-shop.com" in cmd
        assert event.selected_tool is hook._shell_tool

    def test_http_request_to_staging_subdomain_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "https://staging.juice-shop.com/rest/products", "method": "GET"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]

    def test_http_request_to_internal_host_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "http://internal.juice-shop.local/admin", "method": "POST"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]

    # ── unknown tool routed through hook ────────────────────────────────────

    def test_unknown_tool_with_out_of_scope_domain_target_is_blocked(self):
        """AI calls an unknown tool like 'gobuster' with an out-of-scope domain."""
        hook = _make_hook()
        event = _make_event(
            tool_name="gobuster",
            tool_input={"options": "dir", "target": "https://admin.juice-shop.com"},
            selected_tool=None,
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "admin.juice-shop.com" in cmd

    def test_unknown_tool_with_out_of_scope_domain_url_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="sqlmap",
            tool_input={"url": "https://staging.juice-shop.com/search?q=1"},
            selected_tool=None,
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]

    def test_unknown_tool_with_out_of_scope_host_field_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="nikto",
            tool_input={"host": "internal.juice-shop.local", "options": "-p 80"},
            selected_tool=None,
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "internal.juice-shop.local" in cmd

    # ── python_repl ─────────────────────────────────────────────────────────

    def test_python_repl_with_out_of_scope_domain_in_code_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="python_repl",
            tool_input={"code": "import requests\nrequests.get('https://admin.juice-shop.com/api')"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]

    # ── blocked call redirected to shell ────────────────────────────────────

    def test_blocked_call_selected_tool_is_always_shell(self):
        """Regardless of the original tool, a blocked domain call must be routed to shell."""
        hook = _make_hook()
        original_tool = object()
        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "https://admin.juice-shop.com/"},
            selected_tool=original_tool,
        )
        hook._on_before_tool(event)

        assert event.selected_tool is hook._shell_tool
        assert event.selected_tool is not original_tool

    def test_block_message_labels_kind_as_domain(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "curl https://staging.juice-shop.com/rest/whoami"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "domain" in event.tool_use["input"]["command"]


# ---------------------------------------------------------------------------
# _ToolRouterHook – in-scope calls must NOT be blocked
# ---------------------------------------------------------------------------


class TestInScopeDomainCallsPassThrough:
    def test_in_scope_shell_command_not_blocked(self):
        hook = _make_hook()
        original_tool = object()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "curl http://localhost:3000/api/products"},
            selected_tool=original_tool,
        )
        hook._on_before_tool(event)

        assert event.tool_use["input"]["command"] == "curl http://localhost:3000/api/products"
        assert event.selected_tool is original_tool

    def test_in_scope_http_request_not_blocked(self):
        hook = _make_hook()
        original_tool = object()
        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "http://juice-shop.com/rest/products", "method": "GET"},
            selected_tool=original_tool,
        )
        hook._on_before_tool(event)

        assert event.tool_use["input"]["url"] == "http://juice-shop.com/rest/products"
        assert event.selected_tool is original_tool

    def test_nmap_against_in_scope_host_not_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "nmap -sV localhost"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" not in event.tool_use["input"]["command"]

    def test_no_domains_loaded_never_blocks(self):
        hook = _make_hook(domains=[])
        original_input = {"command": "curl https://admin.juice-shop.com/api"}
        event = _make_event(
            tool_name="shell",
            tool_input=dict(original_input),
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert event.tool_use["input"] == original_input


# ---------------------------------------------------------------------------
# _ToolRouterHook – editor tool write-time interception 
# ---------------------------------------------------------------------------


class TestEditorWriteTimeDomainInterception:
    """Verify that out-of-scope domains embedded in scripts are blocked at write
    time via the editor tool's ``content`` field, before the file reaches disk."""

    def test_editor_create_with_out_of_scope_domain_in_content_is_blocked(self):
        """Agent writes a Python script containing an out-of-scope domain via editor."""
        hook = _make_hook()
        event = _make_event(
            tool_name="editor",
            tool_input={
                "command": "create",
                "path": "/tmp/script.py",
                "content": "import requests\nr = requests.get('https://admin.juice-shop.com/api/users')\nprint(r.text)",
            },
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "admin.juice-shop.com" in cmd

    def test_editor_create_with_staging_domain_in_content_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="editor",
            tool_input={
                "command": "create",
                "path": "/tmp/probe.py",
                "content": "import urllib.request\nurllib.request.urlopen('https://staging.juice-shop.com/rest/whoami')",
            },
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]

    def test_editor_create_with_internal_host_in_multiline_script_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="editor",
            tool_input={
                "command": "create",
                "path": "/tmp/recon.py",
                "content": (
                    "#!/usr/bin/env python3\n"
                    "import requests\n"
                    "HOST = 'internal.juice-shop.local'\n"
                    "r = requests.get(f'http://{HOST}/admin')\n"
                    "print(r.status_code)\n"
                ),
            },
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]

    def test_editor_write_blocked_domain_tool_is_redirected_to_shell(self):
        """A blocked editor write must be routed to shell, same as other blocks."""
        hook = _make_hook()
        original_tool = object()
        event = _make_event(
            tool_name="editor",
            tool_input={
                "command": "create",
                "path": "/tmp/s.py",
                "content": "requests.get('https://admin.juice-shop.com/')",
            },
            selected_tool=original_tool,
        )
        hook._on_before_tool(event)

        assert event.selected_tool is hook._shell_tool
        assert event.selected_tool is not original_tool

    def test_editor_create_with_in_scope_content_is_not_blocked(self):
        """A script that only accesses in-scope domains must pass through."""
        hook = _make_hook()
        original_tool = object()
        event = _make_event(
            tool_name="editor",
            tool_input={
                "command": "create",
                "path": "/tmp/legit.py",
                "content": "import requests\nr = requests.get('http://localhost:3000/api/products')\nprint(r.json())",
            },
            selected_tool=original_tool,
        )
        hook._on_before_tool(event)

        assert event.selected_tool is original_tool
        assert "OUT_OF_SCOPE" not in str(event.tool_use["input"])

    def test_editor_update_existing_file_with_out_of_scope_domain_is_blocked(self):
        """Editing (not just creating) a file with an out-of-scope domain is also blocked."""
        hook = _make_hook()
        event = _make_event(
            tool_name="editor",
            tool_input={
                "command": "str_replace",
                "path": "/tmp/existing.py",
                "content": "url = 'https://staging.juice-shop.com/rest/products'",
            },
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]


# ---------------------------------------------------------------------------
# _ToolRouterHook – endpoint check runs before domain check
# ---------------------------------------------------------------------------


class TestEndpointTakesPriorityOverDomain:
    """When both an endpoint and a domain match, endpoint block fires first."""

    def test_endpoint_blocked_before_domain_when_both_present(self):
        sentinel_shell = object()
        hook = ca._ToolRouterHook(shell_tool=sentinel_shell)
        hook._out_of_scope_endpoints = ["/contact"]
        hook._out_of_scope_domains = ["admin.juice-shop.com"]
        hook._shell_tool = sentinel_shell

        event = _make_event(
            tool_name="shell",
            tool_input={"command": "curl https://admin.juice-shop.com/#/contact"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "/contact" in cmd  # endpoint blocked first


# ---------------------------------------------------------------------------
# File-based integration: hook loads domains from an actual tmp file
# ---------------------------------------------------------------------------


class TestFileBasedDomainIntegration:
    def test_hook_loads_and_blocks_domain_from_file(self, tmp_path):
        oos_file = tmp_path / "out_of_scope.txt"
        oos_file.write_text(
            "# comment\n"
            "[ENDPOINTS]\n"
            "/contact\n"
            "[DOMAINS]\n"
            "admin.juice-shop.com\n"
            "staging.juice-shop.com\n"
            "internal.juice-shop.local\n"
        )

        sentinel_shell = object()
        hook = ca._ToolRouterHook(shell_tool=sentinel_shell, out_of_scope_file=oos_file)

        assert len(hook._out_of_scope_domains) == 3

        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "https://admin.juice-shop.com/api/users"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]
        assert event.selected_tool is sentinel_shell

    def test_hook_does_not_block_domain_when_file_missing(self, tmp_path):
        sentinel_shell = object()
        hook = ca._ToolRouterHook(
            shell_tool=sentinel_shell,
            out_of_scope_file=tmp_path / "nonexistent.txt",
        )
        assert hook._out_of_scope_domains == []

        original_input = {"url": "https://admin.juice-shop.com/api"}
        event = _make_event(
            tool_name="http_request",
            tool_input=dict(original_input),
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert event.tool_use["input"] == original_input

    def test_hook_loads_both_sections_independently(self, tmp_path):
        oos_file = tmp_path / "out_of_scope.txt"
        oos_file.write_text(
            "[ENDPOINTS]\n"
            "/contact\n"
            "/about\n"
            "[DOMAINS]\n"
            "admin.juice-shop.com\n"
        )

        sentinel_shell = object()
        hook = ca._ToolRouterHook(shell_tool=sentinel_shell, out_of_scope_file=oos_file)

        assert len(hook._out_of_scope_endpoints) == 2
        assert len(hook._out_of_scope_domains) == 1
