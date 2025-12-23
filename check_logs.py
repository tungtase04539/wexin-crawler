
with open('logs/app.log', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('filtered_logs.txt', 'w', encoding='utf-8') as out:
    out.write("Recent Errors/Warnings:\n")
    for line in lines[-500:]:
        if "failed" in line.lower() or "exception" in line.lower() or "error" in line.lower() or "traceback" in line.lower():
            out.write(line.strip() + "\n")
