from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import bcrypt
from cryptography.fernet import Fernet
import base64


#serialization — משמש להמרה של אובייקט מפתח לייצוג שניתן לשמור/לשלוח (PEM) ולהיפך.
#padding ו־hashes — רכיבים של הצפנת RSA; כאן משתמשים ב-OAEP עם SHA-256 (בטוח יותר מ-PKCS#1 v1.5).
#Fernet — ספריית "פרוטוקול" שמייצרת ומנהלת מפתחות סימטריים, מבצעת הצפנה + אימות (Authenticated Encryption).
#Fernet מחזיר ומקבל טוקנים (bytes).

#PEM — מחרוזת בבייטים

def server_asymmetric_encryption(public_key):
    # שמירה ללקוח. זה לא המפתח כאובייקט לשימוש ישיר, זה ייצוג שניתן לשליחה/שמירה.
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    # שולחים את pem_public ללקוח
    #pem_public הוא המפתח הציבורי של השרת, אבל בפורמט שניתן לשמור או לשלוח.
    #זה לא האובייקט של public_key עצמו, אלא הייצוג שלו בבייטים (bytes), בדרך כלל בצורת PEM (Base64 עם כותרות).
    return pem_public


def encryption_data_server_and_client(message, server_public_key):
    # הצפנה אסימטרית של המידע המועבר מהלקוח לשרת
    encrypted_data = server_public_key.encrypt(
            message.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
    )
    return encrypted_data


def decryption_data_in_server(server_private_key, data):
    #data כבר מסוג בייטס
    decrypted_bytes = server_private_key.decrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
    )
    return decrypted_bytes


def decryption_data_in_client(server_public_key, data):
    decrypted_bytes = server_public_key.decrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted_bytes


def encryption_password(password):
    password_bytes = password.encode('utf-8')  # str → bytes
    hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    hashed_b64 = base64.b64encode(hashed_bytes).decode('ascii')
    return hashed_b64


def generate_symmetric_key():
    # יוצר מפתח Fernet (AES)
    key = Fernet.generate_key()
    fernet = Fernet(key)
    return key, fernet


def encryption_agent_key(server_public_key):

    fernet_key, fernet = generate_symmetric_key()

    # הצפנת המפתח הסימטרי עם RSA
    encrypted_fernet_key = server_public_key.encrypt(
        fernet_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return encrypted_fernet_key, fernet


def decryption_agent_key(server_private_key, encrypted_agent_key):
    # מפענחים עם המפתח הפרטי של השרת
    fernet_key = server_private_key.decrypt(
        encrypted_agent_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    # יוצרים אובייקט Fernet עם המפתח שכבר מפוענח
    fernet = Fernet(fernet_key)
    return fernet


def symmetric_encrypt_for_agent_server_message(fernet, message: str) -> bytes:
    return fernet.encrypt(message.encode())


def symmetric_decrypt_for_agent_server_message(fernet, data: bytes) -> str:
    return fernet.decrypt(data).decode()
