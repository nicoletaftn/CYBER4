#!/usr/bin/env python3
"""
Tests for the out-of-scope endpoint filter built into _ToolRouterHook.

Each test simulates the AI making a tool call "as the agent" and verifies
whether the call is blocked/rewritten (out-of-scope) or passed through
unchanged (in-scope / normal routing).

Current out_of_scope_endpoints.txt entries:
    /#/contact
    /#/about
    /#/photo-wall
"""

import types
from pathlib import Path

import pytest

from modules.agents import cyber_autoagent as ca


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

# Mirrors the three entries currently in out_of_scope_endpoints.txt
SAMPLE_ENDPOINTS = [
    "/#/contact",
    "/#/about",
    "/#/photo-wall",
]


def _make_hook(endpoints: list[str] | None = None) -> ca._ToolRouterHook:
    """Return a hook pre-loaded with *endpoints* (bypasses file I/O)."""
    sentinel_shell = object()
    hook = ca._ToolRouterHook(shell_tool=sentinel_shell)
    hook._out_of_scope_endpoints = endpoints if endpoints is not None else list(SAMPLE_ENDPOINTS)
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
# Helper function unit tests
# ---------------------------------------------------------------------------


class TestLoadOutOfScopeEndpoints:
    def test_returns_empty_list_for_missing_file(self, tmp_path):
        result = ca._load_out_of_scope_endpoints(tmp_path / "nonexistent.txt")
        assert result == []

    def test_parses_endpoints_correctly(self, tmp_path):
        f = tmp_path / "oos.txt"
        f.write_text(
            "# comment\n"
            "\n"
            "/#/contact\n"
            "  /#/about  \n"
            "/#/photo-wall\n"
        )
        result = ca._load_out_of_scope_endpoints(f)
        assert result == ["/#/contact", "/#/about", "/#/photo-wall"]

    def test_ignores_blank_lines_and_comments(self, tmp_path):
        f = tmp_path / "oos.txt"
        f.write_text("# only comments\n\n# another comment\n")
        assert ca._load_out_of_scope_endpoints(f) == []

    def test_returns_empty_list_for_empty_file(self, tmp_path):
        f = tmp_path / "oos.txt"
        f.write_text("")
        assert ca._load_out_of_scope_endpoints(f) == []


class TestFindOutOfScopeEndpoint:
    def test_finds_contact_path_in_full_url(self):
        url = "http://localhost:3000/#/contact"
        result = ca._find_out_of_scope_endpoint(url, SAMPLE_ENDPOINTS)
        assert result == "/#/contact"

    def test_finds_about_inside_curl_command(self):
        cmd = "curl -s 'http://juice-shop.local:3000/#/about'"
        result = ca._find_out_of_scope_endpoint(cmd, SAMPLE_ENDPOINTS)
        assert result == "/#/about"

    def test_finds_photo_wall_path(self):
        cmd = "curl http://localhost:3000/#/photo-wall"
        result = ca._find_out_of_scope_endpoint(cmd, SAMPLE_ENDPOINTS)
        assert result == "/#/photo-wall"

    def test_returns_none_for_clean_url(self):
        url = "http://localhost:3000/api/products"
        result = ca._find_out_of_scope_endpoint(url, SAMPLE_ENDPOINTS)
        assert result is None

    def test_returns_none_with_empty_endpoints_list(self):
        result = ca._find_out_of_scope_endpoint("http://localhost:3000/#/contact", [])
        assert result is None

    def test_returns_first_matching_endpoint(self):
        # Command contains two out-of-scope endpoints; first in list should win
        cmd = "curl http://localhost:3000/#/contact && curl http://localhost:3000/#/about"
        result = ca._find_out_of_scope_endpoint(cmd, SAMPLE_ENDPOINTS)
        assert result == "/#/contact"


# ---------------------------------------------------------------------------
# _ToolRouterHook – out-of-scope blocking (known tools)
# ---------------------------------------------------------------------------


class TestOutOfScopeBlocking:
    """Simulate the AI sending tool calls that target out-of-scope endpoints."""

    # ── shell tool ──────────────────────────────────────────────────────────

    def test_shell_curl_to_contact_page_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "curl -s http://localhost:3000/#/contact"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert cmd.startswith("echo 'OUT_OF_SCOPE")
        assert "/#/contact" in cmd

    def test_shell_wget_to_about_page_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "wget http://juice-shop:3000/#/about -O -"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "/#/about" in cmd

    def test_shell_curl_to_photo_wall_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "curl http://localhost:3000/#/photo-wall"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "/#/photo-wall" in cmd

    # ── http_request tool ───────────────────────────────────────────────────

    def test_http_request_to_contact_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "http://localhost:3000/#/contact", "method": "GET"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "/#/contact" in cmd
        assert event.selected_tool is hook._shell_tool

    def test_http_request_to_about_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "http://localhost:3000/#/about", "method": "GET"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]

    def test_http_request_to_photo_wall_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "http://localhost:3000/#/photo-wall", "method": "GET"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]

    # ── unknown tool routed through hook ────────────────────────────────────

    def test_unknown_tool_with_out_of_scope_target_is_blocked(self):
        """AI calls an unknown tool like 'gobuster' with an out-of-scope target."""
        hook = _make_hook()
        event = _make_event(
            tool_name="gobuster",
            tool_input={"options": "dir", "target": "http://localhost:3000/#/about"},
            selected_tool=None,
        )
        hook._on_before_tool(event)

        cmd = event.tool_use["input"]["command"]
        assert "OUT_OF_SCOPE" in cmd
        assert "/#/about" in cmd

    def test_unknown_tool_with_out_of_scope_url_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="sqlmap",
            tool_input={"url": "http://localhost:3000/#/contact?id=1"},
            selected_tool=None,
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]

    # ── python_repl ─────────────────────────────────────────────────────────

    def test_python_repl_with_out_of_scope_url_in_code_is_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="python_repl",
            tool_input={"code": "import requests\nrequests.get('http://localhost:3000/#/photo-wall')"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]

    # ── blocked call redirected to shell ────────────────────────────────────

    def test_blocked_call_selected_tool_is_always_shell(self):
        """Regardless of the original tool, a blocked call must be routed to shell."""
        hook = _make_hook()
        original_tool = object()
        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "http://localhost:3000/#/contact"},
            selected_tool=original_tool,
        )
        hook._on_before_tool(event)

        assert event.selected_tool is hook._shell_tool
        assert event.selected_tool is not original_tool


# ---------------------------------------------------------------------------
# _ToolRouterHook – in-scope calls must NOT be blocked
# ---------------------------------------------------------------------------


class TestInScopeCallsPassThrough:
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
            tool_input={"url": "http://localhost:3000/api/users", "method": "GET"},
            selected_tool=original_tool,
        )
        hook._on_before_tool(event)

        assert event.tool_use["input"]["url"] == "http://localhost:3000/api/users"
        assert event.selected_tool is original_tool

    def test_nmap_scan_not_blocked(self):
        hook = _make_hook()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "nmap -sV localhost"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" not in event.tool_use["input"]["command"]

    def test_no_endpoints_loaded_never_blocks(self):
        hook = _make_hook(endpoints=[])
        original_input = {"command": "curl http://localhost:3000/#/contact"}
        event = _make_event(
            tool_name="shell",
            tool_input=dict(original_input),
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert event.tool_use["input"] == original_input


# ---------------------------------------------------------------------------
# _ToolRouterHook – existing unknown-tool routing still works
# ---------------------------------------------------------------------------


class TestUnknownToolRoutingUnchanged:
    """Ensure the original routing behaviour is preserved for in-scope calls."""

    def test_unknown_tool_still_routed_to_shell(self):
        hook = _make_hook(endpoints=[])
        sentinel_shell = hook._shell_tool

        event = _make_event(
            tool_name="nmap",
            tool_input={"options": "-sC -sV", "target": "10.0.0.1"},
            selected_tool=None,
        )
        hook._on_before_tool(event)

        assert event.selected_tool is sentinel_shell
        cmd = event.tool_use["input"]["command"]
        assert cmd.startswith("nmap")
        assert "-sC" in cmd and "-sV" in cmd and "10.0.0.1" in cmd

    def test_known_tool_not_rerouted_when_in_scope(self):
        hook = _make_hook(endpoints=[])
        original_tool = object()
        event = _make_event(
            tool_name="shell",
            tool_input={"command": "echo hello"},
            selected_tool=original_tool,
        )
        hook._on_before_tool(event)

        assert event.selected_tool is original_tool
        assert event.tool_use["input"]["command"] == "echo hello"


# ---------------------------------------------------------------------------
# File-based integration: hook loads endpoints from an actual tmp file
# ---------------------------------------------------------------------------


class TestFileBasedIntegration:
    def test_hook_loads_and_blocks_from_file(self, tmp_path):
        oos_file = tmp_path / "out_of_scope_endpoints.txt"
        oos_file.write_text(
            "# comment\n"
            "/#/contact\n"
            "/#/about\n"
            "/#/photo-wall\n"
        )

        sentinel_shell = object()
        hook = ca._ToolRouterHook(shell_tool=sentinel_shell, out_of_scope_file=oos_file)

        assert len(hook._out_of_scope_endpoints) == 3

        event = _make_event(
            tool_name="http_request",
            tool_input={"url": "http://localhost:3000/#/contact"},
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert "OUT_OF_SCOPE" in event.tool_use["input"]["command"]
        assert event.selected_tool is sentinel_shell

    def test_hook_does_not_block_when_file_missing(self, tmp_path):
        sentinel_shell = object()
        hook = ca._ToolRouterHook(
            shell_tool=sentinel_shell,
            out_of_scope_file=tmp_path / "nonexistent.txt",
        )
        assert hook._out_of_scope_endpoints == []

        original_input = {"url": "http://localhost:3000/#/contact"}
        event = _make_event(
            tool_name="http_request",
            tool_input=dict(original_input),
            selected_tool=object(),
        )
        hook._on_before_tool(event)

        assert event.tool_use["input"] == original_input
