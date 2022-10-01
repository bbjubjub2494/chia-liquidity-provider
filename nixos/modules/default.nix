{ self }:
{ pkgs, ... }:

{
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
