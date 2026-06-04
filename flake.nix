# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs = {
    self,
    nixpkgs,
    ...
  }: let
    forAllSystems = nixpkgs.lib.genAttrs nixpkgs.lib.systems.flakeExposed;
  in {
    # `nix fmt`
    formatter = forAllSystems (system: nixpkgs.legacyPackages.${system}.alejandra);

    # `nix develop`
    devShells = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      default = pkgs.mkShell {
        packages = [
          pkgs.python311
          pkgs.poetry
          # Required to build our python dependencies
          pkgs.libpq
          pkgs.libpq.pg_config
          pkgs.libxml2
          pkgs.libxml2.dev
          pkgs.libxslt
          pkgs.libxslt.dev

          # util for running tests locally
          pkgs.just
        ];

        shellHook = ''
          poetry env use ${pkgs.python311}/bin/python3.11
          eval $(poetry env activate)
          poetry install --no-root
        '';
      };
    });
  };
}
