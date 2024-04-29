import secrets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


# Creato da Nunzio D'Amore
#
# Questo file contiene il necessario per la generazione di chiavi simmetriche AES
# in modo sicuro, e i metodi di criptaggio e decriptaggio dei messaggi tramite AES.

# La funzione generate_aes_key genera una chiave a 256 bit 
# casuale, in modo sicuro
def generate_aes_key():
    # Genera sale di 32 bit
    salt = secrets.token_bytes(32)
    # Genera chiave casuale di 32 bit
    start_key = secrets.token_bytes(32)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    # Genera chiave AES da 256 bit
    key = kdf.derive(start_key)
    return key


# encrypt_message cripta i messaggi usando la chiave specificata
def encrypt_message(message, key):
    iv = secrets.token_bytes(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(message) + encryptor.finalize()
    return iv + ciphertext

# decrypt_message decripta il messaggio usando la chiave specificata
def decrypt_message(encrypted_message, key):
    iv = encrypted_message[:16]
    ciphertext = encrypted_message[16:]
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_message = decryptor.update(ciphertext) + decryptor.finalize()
    return decrypted_message