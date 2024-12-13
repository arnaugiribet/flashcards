import socket

try:
    ip = socket.gethostbyname('flashcards-db.ct8kc6o4us1y.us-east-1.rds.amazonaws.com')
    print(f"Resolved IP: {ip}")
except socket.gaierror as e:
    print(f"DNS resolution error: {e}")