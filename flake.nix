# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0
{
  description = "Application packaged using poetry2nix";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    poetry2nix,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      inherit (poetry2nix.lib.mkPoetry2Nix {inherit pkgs;}) mkPoetryApplication defaultPoetryOverrides;
    in {
      packages = {
        seguro = mkPoetryApplication {
          projectDir = ./.;
          preferWheels = true;
          groups = ["dev"];
          overrides =
            defaultPoetryOverrides.extend
            (self: super: {
              aws-logging-handlers =
                super.aws-logging-handlers.overridePythonAttrs
                (
                  old: {
                    buildInputs = (old.buildInputs or []) ++ [super.setuptools];
                  }
                );
            });
        };
        default = self.packages.${system}.seguro;
      };

      devShells.default = pkgs.mkShell {
        inputsFrom = [self.packages.${system}.seguro];
        packages = [pkgs.poetry];
        shellHook = ''
          export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
        '';
      };
    });
}
