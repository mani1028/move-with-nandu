import hashlib, os, base64

password = b"booknandu@123"
salt = os.urandom(16)
iterations = 29000

dk = hashlib.pbkdf2_hmac("sha256", password, salt, iterations)

salt_b64 = base64.b64encode(salt).decode("utf-8")
dk_b64 = base64.b64encode(dk).decode("utf-8")

hash_string = f"$pbkdf2-sha256${iterations}${salt_b64}${dk_b64}"
print(hash_string)
