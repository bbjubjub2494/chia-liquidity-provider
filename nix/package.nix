{
  chia,
  chia-dev-tools,
  python3Packages,
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
    xdg
  ];

  checkInputs = with python3Packages; [
    chia
    chia-dev-tools
    pytestCheckHook
  ];
}
