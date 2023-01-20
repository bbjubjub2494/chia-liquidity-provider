import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from chia_liquidity_provider.services import DatabaseService, WalletRpcClientService


@pytest.fixture
def db(tmpdir):
    return DatabaseService(state_dir=Path(tmpdir, "state"))


@pytest.fixture
def rpc(chia_simulator):
    return WalletRpcClientService()


@pytest.fixture(autouse=True)
def _autouse_aiomisc_loop(loop, services):
    return


@dataclass
class ChiaSimulator:
    farmer_fingerprint: int


# we keep this one constant to avoid replotting
FARMER_MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
)
FARMER_FINGERPRINT = 3781984839


@pytest.fixture(scope="session")
def chia_simulator():
    # keep stuff in this directory for hygiene
    import tests

    os.environ["HOME"] = os.path.dirname(tests.__file__)

    simulator_root_path = Path.home() / ".chia/simulator"
    subprocess.run(["cdv", "sim", "create", "-m", FARMER_MNEMONIC], check=True)
    subprocess.run(["cdv", "sim", "start", "--wallet"], check=True)
    root_path = simulator_root_path / "main"
    os.environ["CHIA_ROOT"] = str(root_path)
    try:
        yield ChiaSimulator(FARMER_FINGERPRINT)
    finally:
        subprocess.run(["cdv", "sim", "stop", "--wallet"], check=True)
