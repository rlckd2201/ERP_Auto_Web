"""Issue a dedicated finance leaf certificate from an existing internal CA."""
import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("ca-cert", "ca-key", "cert", "key"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument("--ip", required=True)
    args = p.parse_args()
    if args.key.exists() or args.cert.exists():
        raise RuntimeError("Certificate output already exists")
    ca = x509.load_pem_x509_certificate(args.ca_cert.read_bytes())
    ca_key = serialization.load_pem_private_key(args.ca_key.read_bytes(), password=None)
    if not ca.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
        raise ValueError("Issuer is not a CA")
    if ca_key.public_key().public_numbers() != ca.public_key().public_numbers():
        raise ValueError("Issuer key does not match certificate")
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, args.ip)]))
        .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(min(now + timedelta(days=365), ca.not_valid_after_utc))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(args.ip))]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256()))
    args.key.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    args.cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM) + ca.public_bytes(serialization.Encoding.PEM))
    print("Issued finance server certificate for " + args.ip)


if __name__ == "__main__":
    main()
