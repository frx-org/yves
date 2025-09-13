{
  pkgs,
  pyproject-nix,
  uv2nix,
  pyproject-build-systems,
}:

let
  inherit (pkgs) lib;
  workspace = uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = lib.fileset.toSource {
      root = ./..;
      fileset = lib.fileset.unions [
        ../pyproject.toml
        ../uv.lock
        ../src
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
in
pkgs.runCommandNoCC "yves"
  {
    buildInputs = [ yves-venv ];
  }
  ''
    mkdir -p $out/bin
    ln -s ${yves-venv}/bin/yves $out/bin
  ''
