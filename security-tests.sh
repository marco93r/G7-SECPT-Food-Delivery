#!/bin/bash

# Script for running automated security tests on the codebase and Docker images

# Setup a Python virtual environment and install security testing tools
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install bandit semgrep pip-audit detect-secrets

# Running SAST tests
bandit -r . -f json -o security_reports/bandit-report.json
semgrep --config=p/owasp-top-ten --json > security_reports/semgrep-report.json
detect-secrets scan > .secrets.baseline
mv .secrets.baseline security_reports/detect-secrets-baseline.json

## Trivy
IMAGES=$(docker image ls --format "{{.Repository}}:{{.Tag}}" | grep mifos/*)
for I in "$IMAGES"; do
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --format json "$I" > security_reports/trivy/trivy-image.json
done

# SCA
pip-audit --format json > security_reports/pip-audit.json