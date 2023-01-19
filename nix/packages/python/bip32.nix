{
  fetchFromGitHub,
  buildPythonPackage,
  coincurve,
  base58,
  pytestCheckHook,
}:
buildPythonPackage rec {
  pname = "bip32";
  version = "3.4";
  src = fetchFromGitHub {
    owner = "darosior";
    repo = "python-bip32";
    rev = "1492d39312f1d9630363c292f6ab8beb8ceb16dd"; # not tagged
    hash = "sha256-o8UKR17XDWp1wTWYeDL0DJY+D11YI4mg0UuGEAPkHxE=";
  };

  propagatedBuildInputs = [base58 coincurve];

  checkInputs = [pytestCheckHook];
}
