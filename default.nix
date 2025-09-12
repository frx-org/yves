{
  system ? builtins.currentSystem,
  source ? import ./npins,
  pkgs ? import source.nixpkgs {
    overlays = [ ];
    config = { };
    inherit system;
  },
}:

{
  shell = pkgs.mkShellNoCC {
    packages = with pkgs; [
      just
      nixfmt-tree
      uv
    ];
  };
}
