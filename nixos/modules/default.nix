{ self }:
{ pkgs, ... }:

{
  systemd.services.chia-wallet = {
    script = "${pkgs.chia}/bin/chia start wallet";
    preStop = "${pkgs.chia}/bin/chia stop all";
    wantedBy = ["multi-user.target"];
    serviceConfig = {
      RestartSec = "1s";
      Restart = "always";
      Type = "forking";
      User = "chia";
    };
  };

  systemd.services.liquidity-manage = {
    script = "${self.packages.${pkgs.system}.default}/bin/liquidity manage";
    wantedBy = ["multi-user.target"];
    after = [ "chia-wallet.target"];
    serviceConfig = {
      Type = "simple";
      User = "chia";
    };
  };

  users.users.chia.packages = [ self.packages.${pkgs.system}.default ];
}
