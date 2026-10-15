import io, json
OUT = r"C:\Users\dth15\Desktop\ANSYS\automation\logs\open_tmp.json"

def s(x):
    try:
        return str(x)
    except Exception:
        return "?"

out = {}
try:
    ExtAPI.DataModel.Project.Open(r"__PATH__")
    out["open"] = "OK"
except Exception as e:
    out["open"] = repr(e)
with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False))
print("OPEN DONE")
