import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from chia.util.errors import KeychainFingerprintExists
from chia.util.keychain import Keychain, KeyData

from chia_liquidity_provider.services import *


@pytest.fixture
def db(tmpdir):
    return DatabaseService(state_dir=Path(tmpdir, "state"))


@pytest.fixture
def rpc(services, chia_simulator):
    return WalletRpcClientService()


@pytest.fixture
async def persistence(db):
    return PersistenceService(db)


@pytest.fixture(autouse=True)
def _autouse_aiomisc_loop(loop, services):
    return


@dataclass
class ChiaSimulator:
    farmer_fingerprint: int


# we keep this one constant to avoid replotting
FARMER_MNEMONIC = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
FARMER_FINGERPRINT = 3781984839


@pytest.fixture(scope="session")
def chia_simulator():
    # TODO: fix this
    """
    # keep stuff in this directory for hygiene
    import tests
    os.environ['HOME'] = os.path.dirname(tests.__file__)
    """
    subprocess.run(["chia", "init"])
    try:
        Keychain().add_private_key(FARMER_MNEMONIC, "simulator_farmer")
    except KeychainFingerprintExists:
        pass
    simulator_root_path = Path.home() / ".chia/simulator"
    subprocess.run(["cdv", "sim", "create", "-f", str(FARMER_FINGERPRINT)], check=True)
    subprocess.run(["cdv", "sim", "start", "--wallet"], check=True)
    root_path = simulator_root_path / "main"
    os.environ["CHIA_ROOT"] = str(root_path)
    try:
        yield ChiaSimulator(FARMER_FINGERPRINT)
    finally:
        subprocess.run(["cdv", "sim", "stop", "--wallet"], check=True)


@pytest.fixture
def random_key():
    kd = KeyData.generate()
    Keychain().add_private_key(kd.mnemonic_str())
    try:
        yield kd
    finally:
        Keychain().delete_key_by_fingerprint(kd.fingerprint)
