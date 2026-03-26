import bcrypt

# Plain password
password = b"booknandu@123"

# Generate salt
salt = bcrypt.gensalt()

# Hash the password
hashed = bcrypt.hashpw(password, salt)

print(hashed.decode())  # This prints the bcrypt hash string
