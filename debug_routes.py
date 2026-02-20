import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.getcwd())

from app.main import app

print("Registered Routes:")
for route in app.routes:
    print(f"{route.path} {route.methods}")
