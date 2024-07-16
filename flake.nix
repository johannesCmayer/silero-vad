#{
#  description = "A Nix-flake-based Python development environment";
#
#  inputs.nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1.*.tar.gz";
#  inputs.flake-utils.url = "github:numtide/flake-utils";
#
#  outputs = { self, nixpkgs, flake-utils, ... }:
#    {
#    #  eachDefaultSystem (system: {
#    #    default = pkgs.python311Packages.buildPythonPackage rec {
#    #      name = "vad";
#    #      src = ./.;
#    #      propagatedBuildInputs = with pkgs;
#    #        (with pkgs.python311Packages; [
#    #          pysilero-vad
#    #          typer
#    #          rich
#    #          torch
#    #          torchaudio
#    #        ]);
#    #    };
#    #  });
#    #  devShells = forEachSupportedSystem ({ pkgs }: {
#    #    default = pkgs.mkShell {
#    #      packages = with pkgs;
#    #        (with pkgs.python311Packages; [
#    #          pysilero-vad
#    #          typer
#    #          rich
#    #          torch
#    #          torchaudio
#    #        ]);
#    #    };
#    #  });
#    #};
#    flake-utils.lib.eachDefaultSystem (system:
#      let pkgs = nixpkgs.legacyPackages.${system}; in
#      {
#        packages = rec {
#          hello = pkgs.hello;
#          default = hello;
#        };
#        apps = rec {
#          hello = flake-utils.lib.mkApp { drv = self.packages.${system}.hello; };
#          default = hello;
#        };
#      }
#    );
#}

{
  description = "Flake utils demo";

  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system}; in
      {
        packages = rec {
          silero-vad = pkgs.python3Packages.buildPythonPackage rec {
            pname = "vad";
            version = "0.0.1";
            pyproject = true;
            src = ./.;
            build-system = with pkgs.python3Packages; [
                setuptools
                wheel
            ];
            dependencies = with pkgs.python3Packages; [
              typer
              rich
              torch
              torchaudio
            ];
            pythonImportsCheck = [
              "vad"
            ];
          };
          default = silero-vad;
        };
        devShells = {
          default = pkgs.mkShell {
            packages = with pkgs;
              (with pkgs.python311Packages; [
                pkgs.python3
                typer
                rich
                torch
                torchaudio
              ]);
          };
        };
      }
    );
}
