import io, json

OUT = r"__OUT__"
PLAN = __PLAN__

def s(x):
    try:
        return str(x)
    except:
        try:
            return repr(x)
        except:
            return "?"

out = {}

spring = None
for g in Model.Connections.Children:
    try:
        if "Spring" in s(g.GetType()):
            spring = g
            break
    except:
        pass

out["found"] = spring is not None

if spring is not None:
    def make_sel(ids):
        sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
        sel.Ids = list(ids)
        return sel

    try:
        spring.MobileScopeLocation = make_sel([PLAN["mobile_face"]])
        out["mob_set"] = "OK"
    except Exception as e:
        out["mob_set"] = "ERR:%r" % e
    try:
        spring.ReferenceScopeLocation = make_sel([PLAN["ref_face"]])
        out["ref_set"] = "OK"
    except Exception as e:
        out["ref_set"] = "ERR:%r" % e

    for attr in ["MobileScopeLocation", "ReferenceScopeLocation"]:
        try:
            v = getattr(spring, attr)
            out[attr + "_back"] = [int(i) for i in v.Ids]
        except Exception as e:
            out[attr + "_back"] = "ERR:%r" % e

    try:
        out["state"] = s(spring.ObjectState)
    except:
        pass
    try:
        out["ref_body"] = s(spring.ReferenceBody)
        out["mob_body"] = s(spring.MobileBody)
    except:
        pass
    for attr in ["SpringLength", "LongitudinalStiffness", "Load", "ReferenceXCoordinate", "ReferenceYCoordinate", "ReferenceZCoordinate", "MobileXCoordinate", "MobileYCoordinate", "MobileZCoordinate"]:
        try:
            out["v_" + attr] = s(getattr(spring, attr))
        except:
            pass

    if s(spring.ObjectState) == "FullyDefined":
        try:
            out["conn_state"] = s(Model.Connections.ObjectState)
        except:
            pass
        try:
            ExtAPI.DataModel.Project.Save()
            out["save"] = "OK"
        except Exception as e:
            out["save"] = "ERR:%r" % e

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=1))
print("SPRING FACE FIX DONE")
