"""Run this once:  python check_setup.py   -> tells you if your API key works."""
from llm import get_client, ask, MODEL
print("Model in use:", MODEL)
print("Models available to your key (flash family):")
try:
    for m in get_client().models.list():
        if "flash" in m.name:
            print("  ", m.name)
except Exception as e:
    print("Could not list models:", e)
print("\nTest call ...")
print(ask("Reply with exactly: SETUP OK"))