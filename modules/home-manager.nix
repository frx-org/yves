{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.yves;
  inherit
    (import ../default.nix {
      inherit pkgs;
    })
    yves
    ;
in
{
  options = {
    services.yves = {
      enable = lib.mkEnableOption ''
        Yves (Your Valuable Efficient Summarizer): automatic work report every day.
      '';
      package = lib.mkOption {
        type = lib.types.package;
        default = yves;
        description = ''
          Package for `yves`.
        '';
      };
      configPath = lib.mkOption {
        type = lib.types.str;
        default = "${config.xdg.configHome}/yves/config";
        description = ''
          Path to configuration file.
        '';
      };
      extraPackages = lib.mkOption {
        default = [ ];
        example = lib.literalExpression ''
          [
            pkgs.prettier
          ]
        '';
        description = ''
          Extra packages to install with the service (e.g. formatter).
        '';
      };
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ cfg.package ] ++ cfg.extraPackages;
    systemd.user.services = {
      yves = {
        Unit = {
          Description = "Yves (Your Valuable Efficient Summarizer): automatic work report every day";
          After = [ "network.target" ];
        };
        Service = {
          ExecStart = "${cfg.package}/bin/yves record --config ${cfg.configPath}";
          Environment = [
            "PATH=${config.home.profileDirectory}/bin:/run/current-system/sw/bin:/usr/bin:/bin"
          ];
          Restart = "on-failure";
          LockPersonality = true;
          MemoryDenyWriteExecute = true;
          NoNewPrivileges = true;
          PrivateUsers = true;
          RestrictNamespaces = true;
          SystemCallArchitectures = "native";
          SystemCallFilter = "@system-service";
        };
        Install = {
          WantedBy = [ "default.target" ];
        };
      };
    };
  };
}
