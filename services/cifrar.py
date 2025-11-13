import bcrypt
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from dotenv import load_dotenv

load_dotenv()
CYPHER_SECURE_KEY = os.environ.get("CYPHER_SECURE_KEY", None)

# ==========================
# 🔐 Funciones para contraseñas con bcrypt
# ==========================
def hash_password(password: str) -> str:
    """Genera un hash seguro de la contraseña usando bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña ingresada coincide con el hash almacenado."""
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

# ==========================
# 🔒 Funciones para cifrado de datos sensibles con AES (Opcional)
# ==========================
def derive_key(secret: str, salt: bytes) -> bytes:
    """Genera una clave derivada usando PBKDF2 con SHA-256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # AES-256 usa claves de 32 bytes
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(secret.encode())

def encrypt_method_AES(message: str) -> str:
    """Cifra un mensaje con AES-GCM y devuelve una cadena base64 con salt, nonce y texto cifrado."""
    salt = os.urandom(16)  # Generar un salt aleatorio
    key = derive_key(CYPHER_SECURE_KEY, salt)
    
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # Generar un nonce aleatorio
    
    encrypted_message = aesgcm.encrypt(nonce, message.encode(), None)
    
    # Concatenar salt, nonce y mensaje cifrado
    encrypted_data = base64.b64encode(salt + nonce + encrypted_message).decode()
    return encrypted_data 

def decrypt_method_AES(encrypted_data: str) -> str:
    """Descifra un mensaje cifrado con AES-GCM en base64."""
    data = base64.b64decode(encrypted_data)
    
    salt = data[:16]  # Extraer el salt
    nonce = data[16:28]  # Extraer el nonce
    ciphertext = data[28:]  # Extraer el texto cifrado
    
    key = derive_key(CYPHER_SECURE_KEY, salt)
    aesgcm = AESGCM(key)
    
    decrypted_message = aesgcm.decrypt(nonce, ciphertext, None)
    return decrypted_message.decode()
