"""Собирает cad/dom-central-ave.dxf из данных плана (src/data.js → JSON).

Запуск из корня репозитория:
  node -e '...'  (см. README, раздел «DXF»)  → /tmp/plan.json
  python3 cad/make_dxf.py /tmp/plan.json
Единицы — мм. Три этажа в пространстве модели рядом: 1 этаж, 2 этаж, чердак (сдвиг 24 м по X).
Ось Y чертежа направлена вверх (в данных плана — вниз), поэтому Y берётся со знаком минус.
"""
import json, math, sys, pathlib
import ezdxf
from ezdxf.enums import TextEntityAlignment

D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/plan.json", encoding="utf-8"))
OUT = pathlib.Path(__file__).with_name("dom-central-ave.dxf")
DX = 24000  # сдвиг этажей по X

doc = ezdxf.new("R2018", setup=True)
doc.units = ezdxf.units.MM
doc.header["$INSUNITS"] = 4
doc.header["$MEASUREMENT"] = 1
doc.styles.add("RU", font="arial.ttf")

LAYERS = {
    "А-ОСИ": (8, "DASHDOT"), "А-СТЕНЫ-НАР": (7, None), "А-СТЕНЫ": (7, None), "А-ОКНА": (5, None), "А-ДВЕРИ": (30, None),
    "А-ЛЕСТНИЦА": (8, None), "А-ПОМЕЩЕНИЯ": (9, None), "А-ПОМЕЩЕНИЯ-ТЕКСТ": (7, None), "А-КРОВЛЯ": (8, "DASHED"), "А-ЗАГОЛОВКИ": (7, None),
    "ОТД-ПОЛЫ": (42, None), "ОВ-КОНДИЦИОНЕРЫ": (4, None), "ОВ-ФРЕОН-ТРАССЫ": (4, "DASHED"), "ОВ-ОТОПЛЕНИЕ": (1, None),
    "ОВ-ТЕПЛЫЙ-ПОЛ": (30, None), "ЭО-ОСВЕЩЕНИЕ": (2, None), "ЭО-ЛЕНТА": (2, "DASHED"), "ЭМ-РОЗЕТКИ": (6, None),
    "ВК-ПРИБОРЫ": (34, None), "ВК-КАНАЛИЗАЦИЯ": (34, "DASHED"), "ВЕНТ": (3, None), "ВЕНТ-ВОЗДУХОВОДЫ": (3, "DASHED"),
}
for n, (c, lt) in LAYERS.items():
    l = doc.layers.add(n, color=c)
    if lt: l.dxf.linetype = lt
doc.header["$LTSCALE"] = 50

msp = doc.modelspace()
FLOORTYPE_ACI = {"Ф1": 254, "Ф2": 41, "Ф3": 151, "Ф4": 52}

def P(f, x, y):
    return ((f - 1) * DX + x, -y)

def rect(f, x0, y0, x1, y1, layer, fill=None, color=None):
    pts = [P(f, x0, y0), P(f, x1, y0), P(f, x1, y1), P(f, x0, y1)]
    attrs = {"layer": layer}
    if color is not None: attrs["color"] = color
    msp.add_lwpolyline(pts, close=True, dxfattribs=attrs)
    if fill is not None:
        h = msp.add_hatch(color=fill, dxfattribs={"layer": layer}); h.paths.add_polyline_path(pts, is_closed=True)

def poly(f, pts, layer, close=False, color=None, width=0):
    attrs = {"layer": layer}
    if color is not None: attrs["color"] = color
    e = msp.add_lwpolyline([P(f, *p) for p in pts], close=close, dxfattribs=attrs)
    if width: e.dxf.const_width = width
    return e

def text(f, x, y, s, h=180, layer="А-ПОМЕЩЕНИЯ-ТЕКСТ", align=TextEntityAlignment.MIDDLE_CENTER, color=None):
    attrs = {"layer": layer, "height": h, "style": "RU"}
    if color is not None: attrs["color"] = color
    msp.add_text(s, dxfattribs=attrs).set_placement(P(f, x, y), align=align)

def mtext(f, x, y, s, h=200, layer="А-ПОМЕЩЕНИЯ-ТЕКСТ"):
    m = msp.add_mtext(s, dxfattribs={"layer": layer, "char_height": h, "style": "RU"})
    m.set_location(P(f, x, y), attachment_point=ezdxf.enums.MTextEntityAlignment.MIDDLE_CENTER)

def circle(f, x, y, r, layer, color=None):
    attrs = {"layer": layer}
    if color is not None: attrs["color"] = color
    msp.add_circle(P(f, x, y), r, dxfattribs=attrs)

for fl in D["FLOORS"]:
    f = fl["id"]
    # заголовок
    text(f, 6950, -3600, f'{fl["name"]}  (отм. {fl["mark"]})', h=500, layer="А-ЗАГОЛОВКИ")
    text(f, 6950, -2900, fl["total"], h=220, layer="А-ЗАГОЛОВКИ")
    # оси
    for x, n in D["AXES"]["x"]:
        msp.add_line(P(f, x, -1800), P(f, x, 17400), dxfattribs={"layer": "А-ОСИ"})
        circle(f, x, -2300, 300, "А-ОСИ"); text(f, x, -2300, n, h=300, layer="А-ОСИ")
    for y, n in D["AXES"]["y"]:
        msp.add_line(P(f, -2300, y), P(f, 15800, y), dxfattribs={"layer": "А-ОСИ"})
        circle(f, -2800, y, 300, "А-ОСИ"); text(f, -2800, y, n, h=300, layer="А-ОСИ")
    if f == 3:
        poly(f, D["ROOF_EAVE"], "А-КРОВЛЯ", close=True)
        poly(f, D["ATTIC_OUTLINE"], "А-СТЕНЫ-НАР", close=True)
    # полы (отделка)
    for r in D["ROOMS"]:
        if r["f"] != f: continue
        t = r.get("fl")
        if t and t != "Ф0":
            h = msp.add_hatch(color=FLOORTYPE_ACI[t], dxfattribs={"layer": "ОТД-ПОЛЫ"})
            h.paths.add_polyline_path([P(f, *p) for p in r["poly"]], is_closed=True)
    # помещения
    for r in D["ROOMS"]:
        if r["f"] != f: continue
        poly(f, r["poly"], "А-ПОМЕЩЕНИЯ", close=True)
        x, y = r["lab"]
        lines = [((r["n"] + ". ") if r.get("n") else "") + r["name"]]
        if r.get("area"): lines.append(f'{r["area"]:.2f}'.replace(".", ",") + " м²")
        if r.get("fl") and r["fl"] != "Ф0": lines.append("пол " + r["fl"])
        mtext(f, x, y, "\\P".join(lines), h=170 if (r.get("area") or 99) < 8.5 else 230)
    # стены
    W = D["WALLS"][str(f)]
    for x0, y0, x1, y1 in W["ext"]: rect(f, x0, y0, x1, y1, "А-СТЕНЫ-НАР", fill=8)
    for x0, y0, x1, y1 in W["int"]: rect(f, x0, y0, x1, y1, "А-СТЕНЫ", fill=9)
    if W.get("stair"):
        st = W["stair"]; (ax, ay), _, (cx, cy), _ = st
        poly(f, st, "А-ЛЕСТНИЦА", close=True)
        for i in range(10):
            xx = ax + (cx - ax) * i / 9
            msp.add_line(P(f, xx, ay), P(f, xx, cy), dxfattribs={"layer": "А-ЛЕСТНИЦА"})
    # окна
    for x, y, l, o, lab in D["WINDOWS"][str(f)]:
        if f == 3:
            rect(f, x - 300, y - l / 2, x + 300, y + l / 2, "А-ОКНА")
        elif o == "h":
            for dy in (-120, 0, 120): msp.add_line(P(f, x - l / 2, y + dy), P(f, x + l / 2, y + dy), dxfattribs={"layer": "А-ОКНА"})
        else:
            for dx in (-120, 0, 120): msp.add_line(P(f, x + dx, y - l / 2), P(f, x + dx, y + l / 2), dxfattribs={"layer": "А-ОКНА"})
    # двери: проём + полотно + дуга открывания
    for d in D["DOORS"][str(f)]:
        x, y, w, o = d[:4]; mk = d[4] if len(d) > 4 else ""
        if o == "h":
            rect(f, x - w / 2, y - 220, x + w / 2, y + 220, "А-ДВЕРИ")
            hx, hy = x - w / 2, y + 220
            msp.add_line(P(f, hx, hy), P(f, hx, hy + w), dxfattribs={"layer": "А-ДВЕРИ"})
            msp.add_arc(P(f, hx, hy), w, 270, 360, dxfattribs={"layer": "А-ДВЕРИ"})
        else:
            rect(f, x - 220, y - w / 2, x + 220, y + w / 2, "А-ДВЕРИ")
            hx, hy = x + 220, y - w / 2
            msp.add_line(P(f, hx, hy), P(f, hx + w, hy), dxfattribs={"layer": "А-ДВЕРИ"})
            msp.add_arc(P(f, hx, hy), w, 270, 360, dxfattribs={"layer": "А-ДВЕРИ"})
        if mk: text(f, x + (0 if o == "h" else 500), y - (450 if o == "h" else 0), mk, h=180, layer="А-ДВЕРИ")

    # ===== инженерия =====
    for dv in D["DEV"]:
        if dv["f"] != f: continue
        s = dv["sys"]; t = dv.get("t")
        if s == "ac":
            if dv.get("route"): poly(f, [[dv["x"], dv["y"]]] + dv["route"], "ОВ-ФРЕОН-ТРАССЫ")
            if t == "indoor":
                L, T = 900, 260
                if dv.get("o") == "h": rect(f, dv["x"] - L / 2, dv["y"] - T / 2, dv["x"] + L / 2, dv["y"] + T / 2, "ОВ-КОНДИЦИОНЕРЫ")
                else: rect(f, dv["x"] - T / 2, dv["y"] - L / 2, dv["x"] + T / 2, dv["y"] + L / 2, "ОВ-КОНДИЦИОНЕРЫ")
                text(f, dv["x"] + 350, dv["y"] + 350, dv["lab"] + f' (сист. {dv.get("sysNo", "")})', h=170, layer="ОВ-КОНДИЦИОНЕРЫ", align=TextEntityAlignment.LEFT)
            elif t == "outdoor":
                rect(f, dv["x"] - 500, dv["y"] - 320, dv["x"] + 500, dv["y"] + 320, "ОВ-КОНДИЦИОНЕРЫ"); circle(f, dv["x"] - 150, dv["y"], 220, "ОВ-КОНДИЦИОНЕРЫ")
                text(f, dv["x"], dv["y"] + 600, dv["lab"] + " " + dv["model"].split(" ")[1], h=170, layer="ОВ-КОНДИЦИОНЕРЫ")
            elif t == "todo":
                circle(f, dv["x"], dv["y"], 230, "ОВ-КОНДИЦИОНЕРЫ"); text(f, dv["x"], dv["y"], "?", h=250, layer="ОВ-КОНДИЦИОНЕРЫ")
        elif s == "rad":
            if t == "radiator":
                L, T = dv["len"], 150
                if dv["o"] == "h": rect(f, dv["x"] - L / 2, dv["y"] - T / 2, dv["x"] + L / 2, dv["y"] + T / 2, "ОВ-ОТОПЛЕНИЕ", fill=1)
                else: rect(f, dv["x"] - T / 2, dv["y"] - L / 2, dv["x"] + T / 2, dv["y"] + L / 2, "ОВ-ОТОПЛЕНИЕ", fill=1)
                text(f, dv["x"] + (0 if dv["o"] == "h" else (-300 if dv["x"] > 7000 else 300)), dv["y"] + (300 if dv["o"] == "h" and dv["y"] < 5000 else (-300 if dv["o"] == "h" else 0)), dv["lab"], h=150, layer="ОВ-ОТОПЛЕНИЕ")
            else:
                rect(f, dv["x"] - 330, dv["y"] - 330, dv["x"] + 330, dv["y"] + 330, "ОВ-ОТОПЛЕНИЕ"); text(f, dv["x"], dv["y"] + 550, "Котёл", h=180, layer="ОВ-ОТОПЛЕНИЕ")
        elif s == "tp":
            rect(f, dv["x"] - 170, dv["y"] - 170, dv["x"] + 170, dv["y"] + 170, "ОВ-ТЕПЛЫЙ-ПОЛ"); text(f, dv["x"], dv["y"], "Т", h=200, layer="ОВ-ТЕПЛЫЙ-ПОЛ")
    for z in D["TP"]:
        if z["f"] != f: continue
        poly(f, z["poly"], "ОВ-ТЕПЛЫЙ-ПОЛ", close=True)
        h = msp.add_hatch(color=30, dxfattribs={"layer": "ОВ-ТЕПЛЫЙ-ПОЛ"}); h.set_pattern_fill("ANSI31", scale=20)
        h.paths.add_polyline_path([P(f, *p) for p in z["poly"]], is_closed=True)
        cx = sum(p[0] for p in z["poly"]) / 4; cy = sum(p[1] for p in z["poly"]) / 4
        text(f, cx, cy, z["id"], h=200, layer="ОВ-ТЕПЛЫЙ-ПОЛ")
    for l in D["LIGHTS"]:
        if l["f"] != f: continue
        k = l["k"]
        if k in ("track", "led"):
            poly(f, l["pts"], "ЭО-ЛЕНТА" if k == "led" else "ЭО-ОСВЕЩЕНИЕ", width=60 if k == "track" else 0)
        else:
            for x, y in l["pts"]:
                r = {"spot": 110, "pend": 180, "chand": 300, "wall": 140, "floor": 160}[k]
                circle(f, x, y, r, "ЭО-ОСВЕЩЕНИЕ")
                if k in ("pend", "chand"):
                    msp.add_line(P(f, x - r * .7, y - r * .7), P(f, x + r * .7, y + r * .7), dxfattribs={"layer": "ЭО-ОСВЕЩЕНИЕ"})
                    msp.add_line(P(f, x - r * .7, y + r * .7), P(f, x + r * .7, y - r * .7), dxfattribs={"layer": "ЭО-ОСВЕЩЕНИЕ"})
        if l.get("line"):
            x, y = l["pts"][0]; text(f, x + 170, y - 220, l["line"].replace("Линия ", "Л"), h=140, layer="ЭО-ОСВЕЩЕНИЕ", align=TextEntityAlignment.LEFT)
    for r in D["ROOMS"]:
        if r["f"] != f or not r.get("sock"): continue
        num = lambda s: int(s.split("—")[-1].strip().split()[0]) if "—" in s and s.split("—")[-1].strip().split()[0].isdigit() else 0
        n_s = sum(num(s) for s in r["sock"] if s.startswith("Розетка")); n_w = sum(num(s) for s in r["sock"] if s.startswith("Выключатель"))
        x, y = r["lab"]; text(f, x, y + 820, f"Розеток {n_s} / выкл. {n_w}", h=150, layer="ЭМ-РОЗЕТКИ")
    S = D["SEWER"]
    for p in S["pipes"]:
        if p["f"] == f: poly(f, p["pts"], "ВК-КАНАЛИЗАЦИЯ", width=60 if p["d"] >= 110 else 30)
    if S["outlet"]["f"] == f:
        poly(f, S["outlet"]["pts"], "ВК-КАНАЛИЗАЦИЯ", width=80); e = S["outlet"]["pts"][-1]
        text(f, e[0] + 150, e[1], S["outlet"]["lab"], h=150, layer="ВК-КАНАЛИЗАЦИЯ", align=TextEntityAlignment.LEFT)
    for x in S["fix"]:
        if x["f"] == f:
            circle(f, x["x"], x["y"], 110, "ВК-ПРИБОРЫ")
            text(f, x["x"] + 160, x["y"] + 160, f'{x["lab"]} Ø{x["d"]}', h=110, layer="ВК-ПРИБОРЫ", align=TextEntityAlignment.LEFT)
    for s in S["stacks"]:
        if f in s["floors"]:
            circle(f, s["x"], s["y"], 190, "ВК-КАНАЛИЗАЦИЯ"); text(f, s["x"] + 280, s["y"] - 330, s["id"] + " Ø110", h=160, layer="ВК-КАНАЛИЗАЦИЯ", align=TextEntityAlignment.LEFT)
    V = D["VENT"]
    for b in V["blocks"]:
        if f in b["floors"]:
            rect(f, b["x0"], b["y0"], b["x1"], b["y1"], "ВЕНТ")
            n = len(b["ch"]); w = (b["x1"] - b["x0"]) / n
            for i in range(1, n): msp.add_line(P(f, b["x0"] + w * i, b["y0"]), P(f, b["x0"] + w * i, b["y1"]), dxfattribs={"layer": "ВЕНТ"})
            text(f, b["x0"] - 150, b["y0"] - 250, b["id"], h=170, layer="ВЕНТ", align=TextEntityAlignment.RIGHT)
    for g in V["grills"]:
        if g["f"] == f: rect(f, g["x"] - 120, g["y"] - 70, g["x"] + 120, g["y"] + 70, "ВЕНТ")
    for d in V["ducts"]:
        if d["f"] == f: poly(f, d["pts"], "ВЕНТ-ВОЗДУХОВОДЫ")

# легенда полов
lx, ly = 0, 19500
text(1, lx, ly, "Типы полов:", h=250, layer="ОТД-ПОЛЫ", align=TextEntityAlignment.LEFT)
for i, (k, v) in enumerate([kv for kv in D["FLOORTYPES"].items() if kv[0] != "Ф0"]):
    yy = ly + 500 + i * 450
    rect(1, lx, yy - 150, lx + 500, yy + 150, "ОТД-ПОЛЫ", fill=FLOORTYPE_ACI[k])
    text(1, lx + 700, yy, f'{k} — {v["name"]}', h=180, layer="ОТД-ПОЛЫ", align=TextEntityAlignment.LEFT)
text(1, lx, ly + 2600, "Источники: дизайн-проекты RUDA studio (05-23, 07-23), проект дома 88-96. Точность привязки ±150 мм. Данные: src/data.js", h=160, layer="А-ЗАГОЛОВКИ", align=TextEntityAlignment.LEFT)

doc.set_modelspace_vport(height=26000, center=(DX * 1 + 7000, -8000))
doc.saveas(OUT)
print("saved", OUT)
