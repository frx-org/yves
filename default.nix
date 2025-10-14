{
  system ? builtins.currentSystem,
  source ? import ./npins,
  pkgs ? import source.nixpkgs {
    overlays = [ ];
    config = { };
    inherit system;
  },
  pyproject-nix ? import source.pyproject-nix {
    inherit (pkgs) lib;
  },
  uv2nix ? import source.uv2nix {
    inherit (pkgs) lib;
    inherit pyproject-nix;
  },
  pyproject-build-systems ? import source.pyproject-build-systems {
    inherit (pkgs) lib;
    inherit pyproject-nix uv2nix;
  },
}:

let
  yves = import ./pkgs/yves.nix {
    inherit
      pkgs
      pyproject-nix
      uv2nix
      pyproject-build-systems
      ;
  };
in
{
  inherit yves;

  default = yves;

  homeModules = {
    default = ./modules/home-manager.nix;
  };

  shell = pkgs.mkShellNoCC {
    packages = with pkgs; [
      just
      nixfmt-tree
      uv
    ];
  };
}
