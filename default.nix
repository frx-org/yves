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
  inherit (pkgs) lib;
  workspace = uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = lib.fileset.toSource {
      root = ./.;
      fileset = lib.fileset.unions [
        ./pyproject.toml
        ./uv.lock
        ./src
        ./prompts
      ];
    };
  };
  python = pkgs.python3;
  overlay = workspace.mkPyprojectOverlay {
    sourcePreference = "wheel";
  };
  baseSet = pkgs.callPackage pyproject-nix.build.packages {
    inherit python;
  };
  pythonSet = baseSet.overrideScope (
    pkgs.lib.composeManyExtensions [
      pyproject-build-systems.default
      overlay
    ]
  );
  yves-venv = pythonSet.mkVirtualEnv "yves-venv" workspace.deps.all;
  yves =
    pkgs.runCommandNoCC "yves"
      {
        buildInputs = [ yves-venv ];
      }
      ''
        mkdir -p $out/bin
        ln -s ${yves-venv}/bin/yves $out/bin
      '';
in
{
  inherit yves;
  default = yves;
  shell = pkgs.mkShellNoCC {
    packages = with pkgs; [
      just
      nixfmt-tree
      uv
    ];
  };
}
