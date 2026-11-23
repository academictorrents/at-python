import os
import pytest


def pytest_addoption(parser):
    parser.addoption("--network", action="store_true", default=False,
                     help="run integration tests that use live servers")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--network") or os.environ.get("AT_NETWORK_TESTS"):
        return
    skip = pytest.mark.skip(reason="needs --network (or AT_NETWORK_TESTS=1)")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _offline_discovery(request, monkeypatch):
    """Keep offline tests off the real DHT, public trackers and academictorrents.com."""
    if "network" in request.keywords:
        return
    from academictorrents import DHT, sources

    def no_site(info_hash, cache_path):
        raise IOError("offline test: academictorrents.com disabled")
    monkeypatch.setattr(DHT, "BOOTSTRAP", [])
    monkeypatch.setattr(sources, "PUBLIC_TRACKERS", [])
    monkeypatch.setattr(sources, "fetch_from_academictorrents", no_site)
