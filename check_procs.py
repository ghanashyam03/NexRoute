import subprocess

res = subprocess.run(["tasklist"], capture_output=True, text=True)
lines = res.stdout.splitlines()

sumo_lines = [l for l in lines if "sumo" in l.lower()]
python_lines = [l for l in lines if "python" in l.lower()]

print(f"Active SUMO processes count: {len(sumo_lines)}")
for l in sumo_lines:
    print("  ", l)

print(f"Active Python processes count: {len(python_lines)}")
for l in python_lines[:10]:
    print("  ", l)
