# The flake file is the entry point for nix commands
{
  description = "Hybrid liquidity farming with Chia offers";

  # Inputs are how Nix can use code from outside the flake during evaluation.
  inputs.devshell.url = "github:numtide/devshell";
  inputs.fup.url = "github:gytis-ivaskevicius/flake-utils-plus/v1.3.1";
  inputs.flake-compat.url = "github:edolstra/flake-compat";
  inputs.flake-compat.flake = false;
  inputs.nixpkgs.url = "nixpkgs/nixos-unstable";
  inputs.chiaNix.url = "github:bbjubjub2494/chia.nix";
  inputs.chiaNix.inputs.nixpkgs.follows = "nixpkgs";

  # Outputs are the public-facing interface to the flake.
  outputs = inputs @ {
    self,
    devshell,
    fup,
    nixpkgs,
    chiaNix,
    ...
  }:
    fup.lib.mkFlake {
      inherit self inputs;

      sharedOverlays = [
        devshell.overlay
        chiaNix.overlays.default
      ];

      nixosModules.default = import nixos/modules/default.nix {inherit self;};

      outputsBuilder = channels: let
        inherit (channels.nixpkgs.chiaNix) chia python3Packages;
        bip32 = python3Packages.callPackage nix/packages/python/bip32.nix {};
      in {
        packages.default = channels.nixpkgs.callPackage nix/package.nix {
          inherit chia python3Packages bip32;
        };
        devShells.default = channels.nixpkgs.callPackage nix/devshell.nix {};
        formatter = channels.nixpkgs.alejandra;
      };

      herculesCI.ciSystems = ["x86_64-linux"];
    };
}
