import io, json

OUT = r"__OUT__"

def s(x):
    try:
        return str(x)
    except:
        try:
            return repr(x)
        except:
            return "?"

rows = []
for rp in Model.RemotePoints.Children:
    r = {}
    try:
        r["h"] = rp.Name.encode("utf-8").encode("hex")
    except:
        r["h"] = "?"
    try:
        r["st"] = s(rp.ObjectState)
    except:
        pass
    try:
        r["loc"] = [int(i) for i in rp.Location.Ids]
    except:
        pass
    rows.append(r)

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps({"n": len(rows), "rows": rows}, ensure_ascii=False, indent=1))
print("RP LIST DONE")
