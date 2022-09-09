{
  chia,
  python3Packages,
}:
python3Packages.buildPythonApplication {
  name = "dexie-liquidity-provider";
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
    click
  ];
}
