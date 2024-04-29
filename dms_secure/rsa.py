import base64
import hashlib
import secrets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends.openssl.backend import backend as openssl_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Creato da Nunzio D'Amore

# Il file contiene tutto il necessario per la generazione delle chiavi RSA in modo sicuro
# pubbliche e private, decriptaggio delle chiavi e criptaggio e decriptaggio delle chiavi simmetriche.
# La chiave privata è criptata con la password dell'utente.


# La funzione generate_RSA_private_key genera una chiave RSA privata
# in modo randomico criptata con la password specificata.
# Il sale viene generato randomicamente con una lunghezza di 32 bit
# e restituito insieme alla chiave privata generata.
def generate_RSA_private_key(password):
    # Genera sale di 32 bit
    salt = secrets.token_bytes(32)

    # Deriva la chiave utilizzando PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password)

    # Genera la chiave privata RSA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Cripta la chiave privata RSA con la chiave derivata
    encrypted_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(key)
    )

    return encrypted_private_key, salt

# La funzione _decrypt_private_key permette di decriptare la chiave
# privata. Necessita, quindi, della password e del sale.
def _decrypt_private_key(encrypted_private_key, password, salt):
    # Deriva la chiave utilizzando PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000, 
        backend=default_backend()
    )
    key = kdf.derive(password)

    # Decifra la chiave privata RSA
    private_key = serialization.load_pem_private_key(
        encrypted_private_key,
        password=key,
        backend=default_backend()
    )

    return private_key

# La funzione generate_RSA_public_key restituisce la chiave pubblica generata
# partendo dalla chiave privata. Essendo la chiave privata criptata,
# la funzione necessita anche del sale e della password per decriptarla.
def generate_RSA_public_key(password, private_key, salt):
    # Carica la chiave privata serializzata
    decrypted_private_key_bytes = _decrypt_private_key(private_key, password, salt)

    # Serializza la chiave pubblica
    public_key = decrypted_private_key_bytes.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return public_key


# La funzione encrypt_message serve a criptare il messaggio specificato 
# utilizzando la chiave pubblica specificata.
def encrypt_message_RSA(message, public_key):
    # Carica la chiave pubblica serializzata
    loaded_public_key = serialization.load_pem_public_key(
        public_key,
        backend=default_backend()
    )

    # Cifra il messaggio utilizzando la chiave pubblica
    encrypted_message = loaded_public_key.encrypt(
        message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return encrypted_message

# La funzione decript_message serve a decriptare i messaggi e necessita,
# oltre alla chiave privata necessaria per decriptare i messaggi, della password
# e del sale per decriptare la chiave privata.
def decript_message_RSA(encrypted_message, password, encrypted_private_key, salt):
    # Decifra la chiave privata usando password e sale
    decripted_private_key = _decrypt_private_key(encrypted_private_key, password, salt)

    # Decifra il messaggio utilizzando la chiave privata
    decripted_message = decripted_private_key.decrypt(
        encrypted_message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return decripted_message
