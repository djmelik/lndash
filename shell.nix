with import <nixpkgs> {};

let
  myPython = python3.withPackages(p: [p.click p.flask p.flask-caching p.googleapis_common_protos p.grpcio p.grpcio-tools p.gunicorn p.itsdangerous p.jinja2 p.markupsafe p.protobuf p.werkzeug ] ++ [ p.black ]);
in
  stdenv.mkDerivation {
    name = "lndash-dev";
    buildInputs = [ myPython ];
  }
