import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from chia_liquidity_provider.services import *


@pytest.fixture
def db(tmpdir):
    return DatabaseService(state_dir=Path(tmpdir, "state"))


@pytest.fixture
def rpc(services, chia_simulator):
    return WalletRpcClientService()


@pytest.fixture(autouse=True)
def _autouse_aiomisc_loop(loop, services):
    return


@dataclass
class ChiaSimulator:
    farmer_fingerprint: int


SIMULATOR_NAME = "clp-integration-tests"

# we keep this one constant to avoid replotting
FARMER_MNEMONIC = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
FARMER_FINGERPRINT = 3781984839


@pytest.fixture
def chia_simulator_root_path():
    subprocess.run(["cdv", "sim", "-n", SIMULATOR_NAME, "create", "-m", FARMER_MNEMONIC], check=True)
    root_path = Path.home() / ".chia/simulator" / SIMULATOR_NAME
    try:
        yield root_path
    finally:
        shutil.rmtree(root_path)


@pytest.fixture
def chia_simulator(chia_simulator_root_path):
    subprocess.run(["cdv", "sim", "-n", SIMULATOR_NAME, "start", "--wallet"], check=True)
    os.environ["CHIA_ROOT"] = str(chia_simulator_root_path)
    try:
        yield ChiaSimulator(FARMER_FINGERPRINT)
    finally:
        subprocess.run(["cdv", "sim", "-n", SIMULATOR_NAME, "stop", "--wallet", "--daemon"], check=True)
