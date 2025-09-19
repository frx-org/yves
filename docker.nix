{
  nix2container,
  cacert,
  yves,
}:

nix2container.buildImage {
  name = "yves";
  tag = "0.1.0";
  copyToRoot = [
    yves
  ];
  config = {
    Cmd = [ "bash" ];
    Env = [
      "SSL_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt"
    ];
    entrypoint = [ "${yves}/bin/yves record" ];
  };
}
