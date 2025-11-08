# Security Checks

## Vorbereitung
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install bandit semgrep pip-audit detect-secrets

## SAST
Im Root-Verzeichnis des Repos
bandit -r . -f json -o security_reports/bandit-report.json
semgrep --config=p/owasp-top-ten --json > security_reports/semgrep-report.json
detect-secrets scan > .secrets.baseline
cp .secrets.baseline security_reports/detect-secrets-baseline.json

## SCA
pip-audit --format json > security_reports/pip-audit.json
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --format json my-image:latest > security_reports/trivy/trivy-image.json

## DAST
docker run --rm -v $(pwd)/zap_reports:/zap/wrk/:rw owasp/zap2docker-stable zap-baseline.py -t http://localhost:8080 -r zap_reports/baseline_report.html
Full-Scan
docker run --rm -v $(pwd)/zap_reports:/zap/wrk/:rw owasp/zap2docker-stable zap-full-scan.py -t http://localhost:8080 -r zap_reports/full_scan.html 

docker run --rm sullo/nikto nikto -h http://localhost:8080 -output /nikto/nikto-report.txt
um die Datei lokal zu haben:
docker run --rm -v $(pwd)/security_reports:/nikto sullo/nikto nikto -h http://localhost:8080 -output /nikto/nikto-report.txt

docker run --rm -v $(pwd):/work jgamblin/ffuf -u http://host.docker.internal:8080/FUZZ -w /work/wordlists/common.txt -j -o /work/security_reports/ffuf.json

cp data/order.db data/order.db.bak
docker run --rm --network host -v $(pwd):/zap sqlmapproject/sqlmap -u "http://localhost:8080/api/orders?orderId=1" --batch --level=2 --risk=1 --output-dir=/zap/sqlmap-report