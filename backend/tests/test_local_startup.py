"""Launcher failure paths must stop only children created by this invocation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import start_local


class Child:
    def __init__(self):
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -1

    def wait(self, timeout):
        return self.returncode


@pytest.fixture
def launcher(monkeypatch):
    children = []

    def spawn(*args, **kwargs):
        child = Child()
        children.append(child)
        return child

    monkeypatch.setattr(start_local, "check_setup", lambda: ("node", Path("vite.js")))
    monkeypatch.setattr(start_local, "check_ports", lambda ports: None)
    monkeypatch.setattr(start_local.subprocess, "Popen", spawn)
    return children


def test_backend_failure_stops_owned_child_before_frontend_start(launcher, monkeypatch):
    def failed(*args):
        raise RuntimeError("not ready")

    monkeypatch.setattr(start_local, "wait_ready", failed)
    with pytest.raises(RuntimeError, match="not ready"), start_local.services():
        pytest.fail("Failed startup must not yield services")
    assert len(launcher) == 1
    assert launcher[0].terminated


def test_frontend_failure_stops_both_owned_children(launcher, monkeypatch):
    def failed(url, children):
        if len(children) == 2:
            raise RuntimeError("frontend unavailable")

    monkeypatch.setattr(start_local, "wait_ready", failed)
    with pytest.raises(RuntimeError, match="frontend unavailable"), start_local.services():
        pytest.fail("Failed startup must not yield services")
    assert len(launcher) == 2
    assert all(child.terminated for child in launcher)


def test_keyboard_interrupt_stops_both_owned_children(launcher, monkeypatch):
    monkeypatch.setattr(start_local, "wait_ready", lambda *args: None)
    with pytest.raises(KeyboardInterrupt), start_local.services():
        raise KeyboardInterrupt
    assert len(launcher) == 2
    assert all(child.terminated for child in launcher)


@pytest.mark.parametrize("ports", [(8000, 8000), (0, 5173), (8000, 65536)])
def test_invalid_ports_rejected_before_start(ports):
    with pytest.raises(RuntimeError, match="distinct"):
        start_local.check_ports(ports)
