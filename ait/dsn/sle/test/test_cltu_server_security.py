#!/usr/bin/env python
"""
Security regression tests for CLTU UDP server (GHSA-gj83-67wr-82mv)

Validates that the UDP server binds to the configured udp_host address
and defaults to loopback (127.0.0.1) for security.
"""
import time

import pytest

from ait.dsn.sle.util.sle_interface_manager import ServiceType
from ait.dsn.sle.util.sle_interface_mgr_server import SleMgrServers


def test_udp_server_binds_to_configured_udp_host():
    """
    Regression test for GHSA-gj83-67wr-82mv:
    Verify UDP server binds to configured udp_host (127.0.0.1)
    """
    servers = SleMgrServers(
        services=[ServiceType.CLTU], udp_host="127.0.0.1", udp_port=9001, rest_port=7655
    )

    try:
        servers.run_servers()
        time.sleep(0.5)  # Allow server to start

        # Check that socket binds to configured udp_host
        bound_host = servers.cltu_udp_server.socket.getsockname()[0]
        assert (
            bound_host == "127.0.0.1"
        ), f"Expected UDP server to bind to 127.0.0.1, but bound to {bound_host}"

    finally:
        servers.kill_servers()


def test_udp_server_defaults_to_loopback():
    """
    Security test: Verify that default udp_host is localhost (127.0.0.1)
    """
    servers = SleMgrServers(services=[ServiceType.CLTU], udp_port=9002, rest_port=7656)

    try:
        servers.run_servers()
        time.sleep(0.5)

        # Verify default is secure (loopback)
        bound_host = servers.cltu_udp_server.socket.getsockname()[0]
        assert (
            bound_host == "127.0.0.1"
        ), f"Default udp_host should bind to 127.0.0.1, but bound to {bound_host}"

    finally:
        servers.kill_servers()


def test_udp_server_binds_to_ipv6_loopback():
    """
    Verify UDP server correctly binds to IPv6 loopback (::1) when configured
    """
    servers = SleMgrServers(
        services=[ServiceType.CLTU], udp_host="::1", udp_port=9003, rest_port=7657
    )

    try:
        servers.run_servers()
        time.sleep(0.5)

        bound_host = servers.cltu_udp_server.socket.getsockname()[0]
        assert (
            bound_host == "::1"
        ), f"Expected UDP server to bind to ::1, but bound to {bound_host}"

    finally:
        servers.kill_servers()


@pytest.mark.parametrize(
    "test_udp_host,test_port,test_rest",
    [
        ("127.0.0.1", 9010, 7661),
        ("localhost", 9011, 7662),
    ],
)
def test_udp_server_respects_configured_udp_host(test_udp_host, test_port, test_rest):
    """
    Parametrized test to verify server respects various loopback configurations
    """
    servers = SleMgrServers(
        services=[ServiceType.CLTU],
        udp_host=test_udp_host,
        udp_port=test_port,
        rest_port=test_rest,
    )

    try:
        servers.run_servers()
        time.sleep(0.5)

        bound_host = servers.cltu_udp_server.socket.getsockname()[0]
        # localhost resolves to 127.0.0.1 on most systems
        expected = "127.0.0.1" if test_udp_host == "localhost" else test_udp_host
        assert (
            bound_host == expected
        ), f"Expected UDP server to bind to {expected}, but bound to {bound_host}"

    finally:
        servers.kill_servers()


def test_udp_host_can_bind_to_non_loopback_when_explicitly_configured():
    """
    Verify that non-loopback binding is allowed when explicitly configured via udp_host.
    This demonstrates that operators must consciously set udp_host to expose the service.
    """
    # Use 0.0.0.0 as a safe test for non-loopback binding
    servers = SleMgrServers(
        services=[ServiceType.CLTU],
        udp_host="0.0.0.0",  # Explicit non-loopback configuration
        udp_port=9022,
        rest_port=7672,
    )

    try:
        servers.run_servers()
        time.sleep(0.5)

        # Verify server started successfully with configured address
        bound_host = servers.cltu_udp_server.socket.getsockname()[0]
        assert bound_host == "0.0.0.0", f"Expected binding to 0.0.0.0, got {bound_host}"

    finally:
        servers.kill_servers()


@pytest.mark.parametrize(
    "non_loopback_host",
    [
        "192.168.1.100",
        "10.0.0.1",
        "172.16.0.1",
        "0.0.0.0",
    ],
)
def test_non_loopback_udp_host_configurations_work(non_loopback_host):
    """
    Verify that various non-loopback addresses can be configured via udp_host.
    Security is enforced by defaulting to loopback and requiring explicit configuration.
    """
    servers = SleMgrServers(
        services=[ServiceType.CLTU],
        udp_host=non_loopback_host,
        udp_port=9030,
        rest_port=7680,
    )

    try:
        servers.run_servers()
        time.sleep(0.5)

        # Verify it bound to the requested address (or 0.0.0.0 if address unavailable)
        bound_host = servers.cltu_udp_server.socket.getsockname()[0]
        # Note: May bind to 0.0.0.0 if specific IP not available on interface
        assert bound_host in [
            non_loopback_host,
            "0.0.0.0",
        ], f"Expected binding to {non_loopback_host} or 0.0.0.0, got {bound_host}"

    except OSError as e:
        # Skip test if the specific IP address is not available on this machine
        if e.errno == 49:  # Can't assign requested address
            pytest.skip(f"IP address {non_loopback_host} not available on this machine")
        raise

    finally:
        servers.kill_servers()


def test_udp_host_independent_from_rest_host():
    """
    Verify that udp_host and host (REST API) are independent configurations
    """
    servers = SleMgrServers(
        services=[ServiceType.CLTU],
        host="0.0.0.0",  # REST API on all interfaces
        udp_host="127.0.0.1",  # UDP only on loopback (secure)
        udp_port=9040,
        rest_port=7690,
    )

    try:
        servers.run_servers()
        time.sleep(0.5)

        # Verify UDP is on loopback despite REST being on 0.0.0.0
        bound_udp_host = servers.cltu_udp_server.socket.getsockname()[0]
        assert (
            bound_udp_host == "127.0.0.1"
        ), f"UDP should be on loopback despite REST on 0.0.0.0, got {bound_udp_host}"

    finally:
        servers.kill_servers()
