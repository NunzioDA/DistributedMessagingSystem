import hashlib
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

## Effettua l'hash di una stringa in un range prestabilito con SHA256
## se range_2 non viene assegnato range_1 sarà il limite massimo
## e il minimo 0.
## Altrimenti range_2 sarà il massimo e range_1 il minimo
##
## Il range massimo non è compreso
def hash_to_range(input_string, range_1, range_2 = None):

    if(range_2 is None):
        range_max = range_1
        range_min = 0
    else:
        range_min =range_1
        range_max =range_2

    hashed = hashlib.sha256(input_string.encode()).hexdigest()
    hashed = hashlib.sha256(hashed.encode()).hexdigest()
    
    hashed_int = int(hashed, 16)

    hash_range = range_max - range_min
    mapped_value = (hashed_int % hash_range) + range_min
    
    return mapped_value

## Genera la chiave pubblica con cui verificare le firme dei messaggi
## criptati con la chiave privata indicata in private_key tramite 
## l'algoritmo ECDSA.
def generate_signature_public_key(private_key):
    private_key_bytes = private_key.encode()
    private_key = hashlib.sha256(private_key_bytes).hexdigest()

    private_key = ec.derive_private_key(
        int.from_bytes(private_key_bytes, byteorder='big'),
        ec.SECP256R1()
    )

    public_key = private_key.public_key()

    serialized_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    signature_base64 = base64.b64encode(serialized_public_key)
    return signature_base64.decode()

## Questa funzione usa ECDSA per firmare il messaggio specificato
## con message usando la chiave privata in private_key

# Funzione per firmare un messaggio
def sign_message(private_key, message):
    private_key_bytes = private_key.encode()
    private_key = hashlib.sha256(private_key_bytes).hexdigest()

    derived_private_key = ec.derive_private_key(
        int.from_bytes(private_key_bytes, byteorder='big'),
        ec.SECP256R1()
    )

    
    # Codifica il messaggio in una sequenza di byte utilizzando UTF-8
    message_bytes = message.encode('utf-8')
    
    # Firma il messaggio utilizzando la chiave privata
    signature_bytes = derived_private_key.sign(
        message_bytes,
        ec.ECDSA(hashes.SHA256())
    )
    
    # Converte la firma da byte a una stringa esadecimale
    signature_hex = signature_bytes.hex()
    
    return signature_hex

## Questa funzione usa ECDSA per verificare la firma contenuta in
## signature relativo al messaggio contenuto in message
## usando la chiave pubblica in public_key

def verify_signature(public_key_str, signature_str, message):
    decoded_public_key = base64.b64decode(public_key_str.encode())

    public_key = serialization.load_pem_public_key(
        decoded_public_key,
        backend=default_backend()
    )
    
    # Codifica il messaggio in una sequenza di byte utilizzando UTF-8
    message_bytes = message.encode('utf-8')
    
    # Converte la firma da stringa esadecimale a byte
    signature_bytes = bytes.fromhex(signature_str)
    
    try:
        # Verifica la firma utilizzando la chiave pubblica
        public_key.verify(
            signature_bytes,
            message_bytes,
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except InvalidSignature:
        return False
