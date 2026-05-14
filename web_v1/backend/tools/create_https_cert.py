from __future__ import annotations

import ipaddress
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: create_https_cert.py <output_dir> <ip_or_dns> [alt_name ...]", file=sys.stderr)
        return 2

    out_dir = Path(sys.argv[1])
    names = list(dict.fromkeys(sys.argv[2:]))
    out_dir.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "KR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Accounting Automation WEB"),
            x509.NameAttribute(NameOID.COMMON_NAME, names[0]),
        ]
    )

    san_items: list[x509.GeneralName] = []
    for name in names:
        try:
            san_items.append(x509.IPAddress(ipaddress.ip_address(name)))
        except ValueError:
            san_items.append(x509.DNSName(name))

    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(san_items), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            key_cert_sign=True,
            key_agreement=False,
            content_commitment=False,
            data_encipherment=False,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False,
        ), critical=True)
        .sign(key, hashes.SHA256())
    )

    key_path = out_dir / "web_v1.key.pem"
    cert_path = out_dir / "web_v1.cert.pem"
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    print(cert_path)
    print(key_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
