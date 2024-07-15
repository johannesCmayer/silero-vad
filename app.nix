{ lib
, python3Packages
}:

python3Packages.buildPythonPackage rec {
  pname = "vad";
  version = "0.0.1";
  pyproject = true;
  src = ./.;
  build-system = with python3Packages; [
      setuptools
      wheel
  ];
  dependencies = with python3Packages; [
    typer
    rich
    torch
    torchaudio
  ];
  pythonImportsCheck = [
    "vad"
  ];
  preBuild = ''
    export PYTHONPATH=$PWD:$PYTHONPATH
  '';
}
