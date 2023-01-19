{
  chia,
  python3Packages,
  bip32,
}:
python3Packages.buildPythonApplication {
  name = "chia_liquidity_provider";
  src = builtins.path {
    path = ../.;
    name = "source";
  };
  format = "pyproject";

  nativeBuildInputs = with python3Packages; [
    poetry-core
  ];

  propagatedBuildInputs = with python3Packages; [
    chia
    aiohttp
    aiosqlite
    aiomisc
    click
    bip32
    xdg
  ];

  checkInputs = with python3Packages; [
    pytestCheckHook
  ];

  disabledTests = [
    "engine_test.py"
  ];
}
