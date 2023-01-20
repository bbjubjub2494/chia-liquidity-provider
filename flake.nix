# The flake file is the entry point for nix commands
{
  description = "Hybrid liquidity farming with Chia offers";

  # Inputs are how Nix can use code from outside the flake during evaluation.
  inputs.fup.url = "github:gytis-ivaskevicius/flake-utils-plus/v1.3.1";
  inputs.flake-compat.url = "github:edolstra/flake-compat";
  inputs.flake-compat.flake = false;
  inputs.nixpkgs.url = "nixpkgs/nixos-unstable";
  inputs.chiaNix.url = "github:lourkeur/chia.nix";
  inputs.chiaNix.inputs.nixpkgs.follows = "nixpkgs";
  inputs.pre-commit-hooks.url = "github:lourkeur/pre-commit-hooks.nix/mypy";
  inputs.pre-commit-hooks.inputs.nixpkgs.follows = "nixpkgs";

  # Outputs are the public-facing interface to the flake.
  outputs = inputs @ {
    self,
    fup,
    nixpkgs,
    chiaNix,
    pre-commit-hooks,
    ...
  }:
    fup.lib.mkFlake {
      inherit self inputs;

      supportedSystems = [ "x86_64-linux" "aarch64-linux" ];

      sharedOverlays = [
        chiaNix.overlays.default
      ];

      nixosModules.default = import nixos/modules/default.nix {inherit self;};

      outputsBuilder = channels: let
        inherit (channels.nixpkgs) system;
        python3' = channels.nixpkgs.python3.withPackages (_:
        let p = channels.nixpkgs.chiaNix.python3Packages; in [
          # runtime deps
          (p.toPythonModule channels.nixpkgs.chiaNix.chia)
          p.aiohttp
          p.click
          p.aiomisc
          p.aiosqlite
          p.xdg
          # test dependencies
          p.pytest
          channels.nixpkgs.chiaNix.chia-dev-tools
          # tools 
          p.flake8
          p.mypy
        ]);
      in {
        packages.default = channels.nixpkgs.callPackage nix/package.nix {
          inherit (channels.nixpkgs.chiaNix) chia python3Packages;
        };
        checks.pre-commit-check = pre-commit-hooks.lib.${system}.run {
            src = ./.;
              hooks.black.enable = true;
              hooks.isort.enable = true;
              hooks.flake8.enable = true;
              settings.flake8.binPath = "${python3'}/bin/flake8";
              hooks.mypy.enable = true;
              settings.mypy.binPath = "${python3'}/bin/mypy";
          };
        devShells.default = channels.nixpkgs.mkShell {
          inherit (self.checks.${system}.pre-commit-check) shellHook;
          buildInputs = [python3'];
          PYTHONPATH="src";
        };
        formatter = channels.nixpkgs.alejandra;
      };

      herculesCI.ciSystems = ["x86_64-linux"];
    };
}
