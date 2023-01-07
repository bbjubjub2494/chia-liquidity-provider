{self}: {pkgs, ...}: {
  systemd.services.clp-manage = {
    script = "${self.packages.${pkgs.system}.default}/bin/clp manage";
    wantedBy = ["multi-user.target"];
    after = ["network-online.target"];
    serviceConfig = {
      Type = "simple";
      User = "chia";
    };
  };

  users.users.chia.packages = [self.packages.${pkgs.system}.default];
}
