# The flake file is the entry point for nix commands
{
  description = "Hybrid liquidity farming with Chia offers";

  # Inputs are how Nix can use code from outside the flake during evaluation.
  inputs.devshell.url = "github:numtide/devshell";
  inputs.fup.url = "github:gytis-ivaskevicius/flake-utils-plus/v1.3.1";
  inputs.flake-compat.url = "github:edolstra/flake-compat";
  inputs.flake-compat.flake = false;
  inputs.nixpkgs.url = "nixpkgs/nixos-unstable";
  inputs.chiaNix.url = "github:lourkeur/chia.nix";

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

      nixosModules.default = import nixos/modules/default.nix { inherit self; };

      outputsBuilder = channels: {
        packages.default = channels.nixpkgs.callPackage nix/package.nix {
          inherit (channels.nixpkgs.chiaNix) chia;
        };
        devShells.default = channels.nixpkgs.callPackage nix/devshell.nix {};
      };
    };
}
