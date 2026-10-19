#!/usr/bin/env python3
"""Génère docs/architecture.gif (animation du flux CI/CD GitOps) et docs/architecture.png.

Usage :  python3 scripts/make_architecture_gif.py        (nécessite Pillow : pip install pillow)
Le dessin est fait à l'échelle x2 puis réduit pour obtenir des bords lissés.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
S = 2  # facteur de sur-échantillonnage
OUT = Path(__file__).resolve().parent.parent / "docs"

# --------------------------------------------------------------------------- polices
FONT_DIRS = [
    "/usr/share/fonts/opentype/inter",
    "/usr/share/fonts/truetype/inter",
    "/usr/share/fonts/truetype/dejavu",
    "/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "C:/Windows/Fonts",
]
CANDIDATES = {
    "regular": ["Inter-Regular.otf", "DejaVuSans.ttf", "Arial.ttf", "arial.ttf"],
    "medium": ["Inter-Medium.otf", "DejaVuSans.ttf", "Arial.ttf", "arial.ttf"],
    "semibold": ["Inter-SemiBold.otf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"],
    "bold": ["Inter-Bold.otf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"],
    "mono": ["DejaVuSansMono.ttf", "Menlo.ttc", "Courier New.ttf", "cour.ttf"],
}
_cache: dict = {}


def font(kind: str, size: float) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key in _cache:
        return _cache[key]
    for d in FONT_DIRS:
        for name in CANDIDATES[kind]:
            p = os.path.join(d, name)
            if os.path.exists(p):
                _cache[key] = ImageFont.truetype(p, int(round(size * S)))
                return _cache[key]
    _cache[key] = ImageFont.load_default()
    return _cache[key]


# --------------------------------------------------------------------------- palette
def hexrgb(h: str, a: int = 255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


BG = "#0a0f1c"
BG2 = "#0e1627"
PANEL = "#121c31"
PANEL_HI = "#18253f"
BORDER = "#26344f"
TEXT = "#e8eefc"
MUTED = "#8fa0c0"
DIM = "#4a5a7a"
GREEN = "#34d399"
RED = "#f87171"
AWS = "#ff9900"

C = {
    "dev": "#94a3b8", "github": "#e6edf3", "dockerhub": "#2496ed", "terraform": "#8b5cf6",
    "ansible": "#f43f5e", "jenkins": "#f97316", "trivy": "#14b8a6", "k8s": "#3b82f6",
    "argocd": "#fb923c", "cw": "#ec4899", "user": "#a3e635", "pods": "#34d399",
}


# --------------------------------------------------------------------------- géométrie
def sc(v):
    return v * S


def rr(d, box, r, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = box
    d.rounded_rectangle((sc(x0), sc(y0), sc(x1), sc(y1)), radius=sc(r), fill=fill, outline=outline, width=int(width * S))


def text(d, xy, s, kind="regular", size=13, fill=TEXT, anchor="lm"):
    d.text((sc(xy[0]), sc(xy[1])), s, font=font(kind, size), fill=fill if isinstance(fill, tuple) else hexrgb(fill), anchor=anchor)


def seg_lengths(pts):
    return [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]


def point_at(pts, t):
    ls = seg_lengths(pts)
    total = sum(ls)
    target = max(0.0, min(1.0, t)) * total
    acc = 0.0
    for i, l in enumerate(ls):
        if acc + l >= target or i == len(ls) - 1:
            u = 0 if l == 0 else (target - acc) / l
            x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u
            y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u
            return (x, y)
        acc += l
    return pts[-1]


def partial(pts, t):
    ls = seg_lengths(pts)
    total = sum(ls)
    target = t * total
    out = [pts[0]]
    acc = 0.0
    for i, l in enumerate(ls):
        if acc + l <= target:
            out.append(pts[i + 1])
            acc += l
        else:
            u = (target - acc) / l if l else 0
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u))
            break
    return out


def dashed(d, pts, color, width, dash=6, gap=5):
    """Ligne pointillée le long d'une polyligne."""
    ls = seg_lengths(pts)
    for i, l in enumerate(ls):
        if l == 0:
            continue
        ux, uy = (pts[i + 1][0] - pts[i][0]) / l, (pts[i + 1][1] - pts[i][1]) / l
        pos = 0.0
        while pos < l:
            e = min(pos + dash, l)
            d.line((sc(pts[i][0] + ux * pos), sc(pts[i][1] + uy * pos), sc(pts[i][0] + ux * e), sc(pts[i][1] + uy * e)),
                   fill=color, width=int(width * S))
            pos += dash + gap


def arrow_head(d, pts, color, size=8):
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    a = math.atan2(y1 - y0, x1 - x0)
    p1 = (x1, y1)
    p2 = (x1 - size * math.cos(a - 0.45), y1 - size * math.sin(a - 0.45))
    p3 = (x1 - size * math.cos(a + 0.45), y1 - size * math.sin(a + 0.45))
    d.polygon([(sc(p[0]), sc(p[1])) for p in (p1, p2, p3)], fill=color)


# --------------------------------------------------------------------------- scène
NODES = {
    # nom: (x0, y0, x1, y1, titre, sous-titre, monogramme, couleur)
    "dev": (30, 60, 220, 140, "Développeur", "git push sur main", "</>", C["dev"]),
    "github": (520, 60, 800, 140, "GitHub", "app/ · Jenkins/ · k8s-manifests/", "GH", C["github"]),
    "dockerhub": (1030, 60, 1230, 140, "DockerHub", "registre d'images", "DH", C["dockerhub"]),
    "terraform": (30, 235, 220, 305, "Terraform", "VPC · 4 EC2 · SG · IAM", "TF", C["terraform"]),
    "ansible": (30, 350, 220, 420, "Ansible", "Jenkins · K8s · Argo", "AN", C["ansible"]),
    "jmaster": (324, 252, 458, 342, "Master", "JCasC · UI :8080", "J", C["jenkins"]),
    "jagent": (490, 252, 664, 342, "Agent (slave)", "Docker · Trivy · pytest", "J", C["jenkins"]),
    "cw": (324, 548, 664, 608, "CloudWatch + SNS", "CPU · mémoire · status → alerte e-mail", "CW", C["cw"]),
    "kmaster": (716, 250, 916, 392, "kubemaster", "control-plane · Flannel", "K8", C["k8s"]),
    "kworker": (1000, 250, 1226, 392, "kubenode1", "worker · containerd", "K8", C["k8s"]),
    "svc": (1000, 440, 1226, 492, "Service NodePort", ":30080 → pods :5000", "SV", C["k8s"]),
    "user": (1000, 548, 1226, 612, "Utilisateur", "navigateur web", "U", C["user"]),
}

CHIPS = [("Tests", C["jenkins"]), ("Build", C["jenkins"]), ("Scan", C["trivy"]), ("Push", C["dockerhub"]), ("GitOps", C["github"])]
CHIP_X0, CHIP_Y0, CHIP_W, CHIP_H, CHIP_GAP = 324, 396, 62, 30, 6

FLOWS = {
    "push": dict(pts=[(220, 100), (520, 100)], color=C["github"], label=("git push", (370, 90))),
    "poll": dict(pts=[(391, 252), (391, 160), (560, 160), (560, 140)], color="#38bdf8", label=("polling SCM", (475, 150))),
    "ssh": dict(pts=[(458, 297), (490, 297)], color="#a78bfa", label=None),
    "image": dict(pts=[(640, 252), (640, 155), (1130, 155), (1130, 140)], color=C["dockerhub"], label=("docker push  <build>-<sha>", (885, 146))),
    "commit": dict(pts=[(610, 252), (610, 140)], color="#facc15", label=("commit newTag", (655, 205))),
    "argopoll": dict(pts=[(780, 250), (780, 140)], color=C["argocd"], label=None),
    "sync": dict(pts=[(916, 321), (1000, 321)], color=C["argocd"], label=("sync", (958, 308))),
    "pull": dict(pts=[(1180, 140), (1180, 250)], color=C["dockerhub"], label=("pull image", (1204, 196))),
    "traffic": dict(pts=[(1113, 548), (1113, 392)], color=C["user"], label=("HTTP", (1141, 520))),
    "tf": dict(pts=[(220, 270), (314, 270)], color=C["terraform"], label=("provisionne", (267, 258))),
    "an": dict(pts=[(220, 385), (314, 385)], color=C["ansible"], label=("configure", (267, 373))),
}

STEPS = [
    ("Le développeur pousse son code sur GitHub", [("push", 0.0, 1.0)]),
    ("Jenkins détecte le commit et délègue le job à l'agent", [("poll", 0.0, 0.62), ("ssh", 0.62, 1.0)]),
    ("Tests unitaires pytest, puis build de l'image (non-root, gunicorn)", []),
    ("Scan Trivy bloquant : aucune image HIGH/CRITICAL n'est publiée", []),
    ("Push de l'image taguée <build>-<sha> sur DockerHub", [("image", 0.0, 1.0)]),
    ("Commit automatique du nouveau tag dans k8s-manifests/ (GitOps)", [("commit", 0.0, 1.0)]),
    ("ArgoCD voit le changement dans Git et synchronise le cluster", [("argopoll", 0.0, 0.5), ("sync", 0.5, 1.0)]),
    ("Le nœud tire l'image, 2 pods démarrent, l'application répond", [("pull", 0.0, 0.5), ("traffic", 0.5, 1.0)]),
]
# chips allumés à la fin de chaque étape (index d'étape -> nb de chips)
CHIPS_AFTER = {2: 2, 3: 3, 4: 4, 5: 5}


def chip_box(i):
    x0 = CHIP_X0 + i * (CHIP_W + CHIP_GAP)
    return (x0, CHIP_Y0, x0 + CHIP_W, CHIP_Y0 + CHIP_H)


def chips_lit(step, p):
    """Nombre de chips allumés pour l'étape `step` à l'avancement p (0..1)."""
    if step < 2:
        return 0
    base = {2: 0, 3: 2, 4: 3, 5: 4}.get(step, 5)
    if step == 2:
        return 1 if p >= 0.34 and p < 0.75 else (2 if p >= 0.75 else 0)
    if step in (3, 4, 5):
        return base + (1 if p >= 0.5 else 0)
    return 5


# --------------------------------------------------------------------------- éléments statiques
def draw_static() -> Image.Image:
    img = Image.new("RGB", (W * S, H * S), hexrgb(BG)[:3])  # RGB + Draw(..., "RGBA") => fondus translucides corrects
    d = ImageDraw.Draw(img, "RGBA")
    # fond : points discrets
    for x in range(20, W, 28):
        for y in range(20, H, 28):
            d.ellipse((sc(x) - 1, sc(y) - 1, sc(x) + 1, sc(y) + 1), fill=hexrgb("#18233a"))
    # bandeau titre
    text(d, (30, 28), "iVolve  ·  CI/CD GitOps sur AWS", "bold", 22, TEXT)
    text(d, (1250, 28), "Terraform · Ansible · Jenkins · Trivy · ArgoCD · Kubernetes", "regular", 12.5, MUTED, "rm")
    # conteneur AWS
    rr(d, (300, 172, 1255, 656), 18, fill=hexrgb(BG2), outline=None)
    dashed_box(d, (300, 172, 1255, 656), hexrgb(AWS, 190))
    rr(d, (318, 163, 540, 187), 12, fill=hexrgb(BG), outline=hexrgb(AWS, 200), width=1)
    text(d, (329, 175), "AWS · us-east-1 · VPC 10.0.0.0/16", "semibold", 11.5, AWS)
    # zones
    rr(d, (314, 200, 676, 640), 14, fill=hexrgb(PANEL, 140), outline=hexrgb(BORDER))
    rr(d, (696, 200, 1241, 640), 14, fill=hexrgb(PANEL, 140), outline=hexrgb(BORDER))
    text(d, (330, 217), "CI  ·  Jenkins (EC2 t3.medium)", "semibold", 12.5, C["jenkins"])
    text(d, (712, 217), "CD  ·  Kubernetes 1.36 (kubeadm) + ArgoCD", "semibold", 12.5, C["k8s"])
    text(d, (324, 378), "PIPELINE  ·  Jenkinsfile", "semibold", 10, MUTED)
    # panneau sécurité
    rr(d, (30, 455, 220, 640), 14, fill=hexrgb(PANEL, 160), outline=hexrgb(BORDER))
    text(d, (46, 475), "SÉCURITÉ INTÉGRÉE", "semibold", 10.5, GREEN)
    for i, line in enumerate(["IMDSv2 + EBS chiffrés", "SG par rôle, SSH restreint", "Secrets : Ansible Vault", "Trivy bloquant avant push", "Pods non-root, rootfs RO", "Pod Security « restricted »"]):
        d.ellipse((sc(47), sc(500 + i * 22) - 3, sc(47) + 6, sc(500 + i * 22) + 3), fill=hexrgb(GREEN, 200))
        text(d, (60, 500 + i * 22), line, "regular", 11.5, "#c4d0ea")
    return img


def dashed_box(d, box, color, dash=9, gap=6, width=1.4):
    x0, y0, x1, y1 = box
    r = 18
    pts = [(x0 + r, y0), (x1 - r, y0)], [(x1, y0 + r), (x1, y1 - r)], [(x1 - r, y1), (x0 + r, y1)], [(x0, y1 - r), (x0, y0 + r)]
    for seg in pts:
        dashed(d, seg, color, width, dash, gap)
    for (cx, cy, a0) in ((x1 - r, y0 + r, 270), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        d.arc((sc(cx - r), sc(cy - r), sc(cx + r), sc(cy + r)), a0, a0 + 90, fill=color, width=int(width * S))


# --------------------------------------------------------------------------- éléments dynamiques
def draw_node(d, name, state="idle", pulse=0.0):
    x0, y0, x1, y1, title, sub, mono, col = NODES[name]
    accent = hexrgb(col)
    if state == "active":
        # halo progressif : 9 couches très translucides, de plus en plus larges
        for k in range(9, 0, -1):
            rr(d, (x0 - k * 1.5, y0 - k * 1.5, x1 + k * 1.5, y1 + k * 1.5), 12 + k * 1.3, fill=hexrgb(col, int(6 + 4 * pulse)))
    fill = PANEL_HI if state != "idle" else PANEL
    outline = accent if state == "active" else (hexrgb(col, 150) if state == "done" else hexrgb(BORDER))
    rr(d, (x0, y0, x1, y1), 12, fill=hexrgb(fill), outline=outline, width=2 if state == "active" else 1.2)
    # badge
    big = (y1 - y0) >= 100
    bw = 34
    bx, by = x0 + 12, (y0 + 12 if big else (y0 + y1) / 2 - bw / 2)
    rr(d, (bx, by, bx + bw, by + bw), 9, fill=hexrgb(col, 255 if state != "idle" else 150))
    dark = name in ("github", "dockerhub") or col in (C["user"], C["pods"])
    text(d, (bx + bw / 2, by + bw / 2 + 0.5), mono, "bold", 12 if len(mono) < 3 else 11, "#0a0f1c" if dark or name in ("github",) else "#ffffff", "mm")
    tx = x0 + 12 + bw + 10
    ty = by + bw / 2
    text(d, (tx, ty - 8), title, "semibold", 13.5, TEXT)
    text(d, (tx, ty + 9), sub, "regular", 10.5, MUTED)


def draw_flow_static(d, key, state):
    """state: 'idle' (pointillé discret) | 'done' (plein, teinté)"""
    f = FLOWS[key]
    col = f["color"]
    if state == "idle":
        dashed(d, f["pts"], hexrgb(DIM, 150), 1.4, 4, 5)
    else:
        d.line([(sc(x), sc(y)) for x, y in f["pts"]], fill=hexrgb(col, 130), width=int(1.8 * S), joint="curve")
        arrow_head(d, f["pts"], hexrgb(col, 170), 7)
    if f["label"]:
        s, pos = f["label"]
        text(d, pos, s, "medium", 10.5, hexrgb(col, 230) if state == "done" else hexrgb(MUTED, 220), "mm")


def draw_flow_active(d, key, t):
    f = FLOWS[key]
    col = f["color"]
    seg = partial(f["pts"], max(t, 0.001))
    d.line([(sc(x), sc(y)) for x, y in seg], fill=hexrgb(col, 255), width=int(2.6 * S), joint="curve")
    if t >= 0.999:
        arrow_head(d, f["pts"], hexrgb(col), 9)
    # traîne + paquet lumineux
    for k in range(6, 0, -1):
        tt = max(0.0, t - k * 0.035)
        px, py = point_at(f["pts"], tt)
        r = 3.2 - k * 0.3
        d.ellipse((sc(px - r), sc(py - r), sc(px + r), sc(py + r)), fill=hexrgb(col, 90))
    px, py = point_at(f["pts"], t)
    for r, a in ((11, 40), (8, 90), (5.2, 255)):
        d.ellipse((sc(px - r), sc(py - r), sc(px + r), sc(py + r)), fill=hexrgb("#ffffff" if r == 5.2 else col, a))
    if f["label"]:
        s, pos = f["label"]
        text(d, pos, s, "semibold", 10.5, col, "mm")


def draw_chips(d, lit, active_idx=None, pulse=0.0):
    for i, (name, col) in enumerate(CHIPS):
        x0, y0, x1, y1 = chip_box(i)
        on = i < lit
        cur = active_idx == i
        if cur:
            for k in range(6, 0, -1):
                rr(d, (x0 - k, y0 - k, x1 + k, y1 + k), 8 + k, fill=hexrgb(col, int(7 + 4 * pulse)))
        rr(d, (x0, y0, x1, y1), 8, fill=hexrgb(col, 235) if on else hexrgb(PANEL), outline=hexrgb(col, 200) if (on or cur) else hexrgb(BORDER), width=1.2)
        fg = "#0a0f1c" if (on and col in (C["github"], C["trivy"], C["dockerhub"])) else ("#ffffff" if on else MUTED)
        text(d, ((x0 + x1) / 2, (y0 + y1) / 2 + 0.5), ("✓ " if on and False else "") + name, "semibold", 11.5, fg, "mm")
        if i < len(CHIPS) - 1:
            ax = x1 + CHIP_GAP / 2
            d.polygon([(sc(ax - 2), sc(y0 + CHIP_H / 2 - 3)), (sc(ax - 2), sc(y0 + CHIP_H / 2 + 3)), (sc(ax + 2.2), sc(y0 + CHIP_H / 2))], fill=hexrgb(DIM))


def draw_argocd_chip(d, state, pulse=0.0):
    box = (730, 332, 902, 376)
    col = C["argocd"]
    if state == "active":
        for k in range(7, 0, -1):
            rr(d, (box[0] - k, box[1] - k, box[2] + k, box[3] + k), 9 + k, fill=hexrgb(col, int(8 + 4 * pulse)))
    rr(d, box, 9, fill=hexrgb(col, 240) if state != "idle" else hexrgb(PANEL), outline=hexrgb(col, 220) if state != "idle" else hexrgb(BORDER), width=1.2)
    fg = "#0a0f1c" if state != "idle" else MUTED
    text(d, (box[0] + 14, (box[1] + box[3]) / 2 - 7), "ArgoCD", "bold", 13, fg)
    text(d, (box[0] + 14, (box[1] + box[3]) / 2 + 9), "auto-sync · self-heal · prune", "regular", 9.5, "#3b2410" if state != "idle" else DIM)


def draw_pods(d, state, flip=0.0):
    """Deux pods dans kubenode1 ; `flip` (0..1) : rolling update (ancien -> nouveau)."""
    for i in range(2):
        x0 = 1014 + i * 100
        box = (x0, 332, x0 + 88, 376)
        if state == "idle":
            fill, ol, label = hexrgb(PANEL), hexrgb(BORDER), "pod"
        else:
            new = flip > (0.35 + 0.35 * i)
            fill = hexrgb(C["pods"], 235) if new else hexrgb("#27365a")
            ol = hexrgb(C["pods"], 230)
            label = "pod ✓" if new else "pod"
        rr(d, box, 9, fill=fill, outline=ol, width=1.2)
        text(d, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 - 6), label, "bold", 12, "#06281d" if (state != "idle" and flip > (0.35 + 0.35 * i)) else MUTED, "mm")
        text(d, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 9), ":5000", "mono", 9, "#0b3b2b" if (state != "idle" and flip > (0.35 + 0.35 * i)) else DIM, "mm")


def draw_cw(d, phase):
    x0, y0 = 590, 562
    for i in range(9):
        h = 6 + 10 * (0.5 + 0.5 * math.sin(phase * 2 * math.pi + i * 0.9))
        rr(d, (x0 + i * 7, y0 + 30 - h, x0 + i * 7 + 4, y0 + 30), 1.5, fill=hexrgb(C["cw"], 190))


def draw_github_tag(d, tag):
    text(d, (666, 124), f"newTag: \"{tag}\"", "mono", 10, hexrgb("#fbbf24"), "mm")


def draw_trivy_badge(d, p):
    if p <= 0:
        return
    rr(d, (400, 436, 582, 460), 12, fill=hexrgb("#0b2e2a", 240), outline=hexrgb(C["trivy"], 220), width=1.2)
    text(d, (491, 448), "0 vulnérabilité HIGH/CRITICAL ✓" if p >= 0.5 else "analyse de l'image…", "semibold", 10.5, "#5eead4", "mm")


def draw_footer(d, step, n_steps, caption, t=0.0):
    rr(d, (30, 668, 1250, 710), 12, fill=hexrgb(PANEL), outline=hexrgb(BORDER))
    if step is None:
        text(d, (60, 689), "Vue d'ensemble de l'architecture", "semibold", 15, TEXT)
        return
    col = "#38bdf8"
    d.ellipse((sc(46), sc(678), sc(46 + 22), sc(678 + 22)), fill=hexrgb(col))
    text(d, (57, 689.5), str(step + 1), "bold", 12.5, "#06222f", "mm")
    text(d, (84, 689), caption, "semibold", 15, TEXT)
    # points de progression
    for i in range(n_steps):
        x = 1250 - 22 - (n_steps - 1 - i) * 18
        on = i <= step
        d.ellipse((sc(x - 5), sc(689 - 5), sc(x + 5), sc(689 + 5)), fill=hexrgb(col) if on else hexrgb(BORDER))


# --------------------------------------------------------------------------- assemblage
def render(step, p, static_img, pulse, loop_hold=False):
    """step : index 0..7 (None = intro) ; p : avancement 0..1 dans l'étape."""
    img = static_img.copy()
    d = ImageDraw.Draw(img, "RGBA")

    done_steps = set(range(step)) if step is not None else set()
    if loop_hold:
        done_steps = set(range(len(STEPS)))
    active_flows = {}
    if step is not None and not loop_hold:
        for key, a, b in STEPS[step][1]:
            if p >= a:
                active_flows[key] = min(1.0, (p - a) / (b - a))
    done_flows = set()
    for s in done_steps:
        for key, _, _ in STEPS[s][1]:
            done_flows.add(key)
    for key, t in list(active_flows.items()):
        if t >= 1.0:
            done_flows.add(key)

    # provisionnement (toujours visible, discret)
    for key in ("tf", "an"):
        draw_flow_static(d, key, "done")

    # flux
    for key in FLOWS:
        if key in ("tf", "an"):
            continue
        if key in active_flows and active_flows[key] < 1.0:
            continue
        draw_flow_static(d, key, "done" if key in done_flows else "idle")
    # petit "pont" là où argopoll croise image
    for key, t in active_flows.items():
        if t < 1.0:
            draw_flow_static(d, key, "idle")
    for key, t in active_flows.items():
        if t < 1.0 or key in ("push",):
            draw_flow_active(d, key, t)

    # états des nœuds
    act = set()
    if step is not None and not loop_hold:
        flows_now = [k for k, t in active_flows.items() if t < 1.0] or [k for k in active_flows]
        mapping = {
            "push": ("dev", "github"), "poll": ("github", "jmaster"), "ssh": ("jmaster", "jagent"),
            "image": ("jagent", "dockerhub"), "commit": ("jagent", "github"), "argopoll": ("github",),
            "sync": ("kmaster", "kworker"), "pull": ("dockerhub", "kworker"), "traffic": ("user", "svc", "kworker"),
        }
        for k in flows_now:
            act.update(mapping.get(k, ()))
        if step in (2, 3):
            act.add("jagent")
        if step == 1 and p >= 0.62:
            act.add("jagent")
    done_nodes = {"terraform", "ansible", "cw"}
    if step is not None:
        for s in done_steps:
            for k, _, _ in STEPS[s][1]:
                done_nodes.update({
                    "push": ("dev", "github"), "poll": ("github", "jmaster"), "ssh": ("jmaster", "jagent"),
                    "image": ("dockerhub",), "commit": ("github",), "argopoll": (), "sync": ("kmaster", "kworker"),
                    "pull": ("dockerhub", "kworker"), "traffic": ("user", "svc"),
                }.get(k, ()))
        if step >= 2:
            done_nodes.update({"jagent", "jmaster", "github", "dev"})
    if loop_hold:
        done_nodes.update(NODES.keys())

    for name in NODES:
        st = "active" if name in act else ("done" if name in done_nodes else "idle")
        draw_node(d, name, st, pulse)

    # CloudWatch (barres animées)
    draw_cw(d, pulse)

    # chips du pipeline
    lit = 5 if loop_hold else (chips_lit(step, p) if step is not None else 0)
    if step is not None and step >= 6:
        lit = 5
    active_chip = None
    if step in (2, 3, 4, 5) and not loop_hold and lit < 5:
        active_chip = lit
    if step in (2, 3, 4, 5) and not loop_hold:
        active_chip = min(lit, 4) if lit < 5 else 4
    draw_chips(d, lit, active_chip, pulse)

    # ArgoCD & pods
    argo_state = "idle"
    if step is not None and (step >= 6 or loop_hold):
        argo_state = "active" if (step == 6 and not loop_hold) else "done"
    draw_argocd_chip(d, argo_state, pulse)
    pods_state = "idle"
    flip = 0.0
    if loop_hold or (step is not None and step >= 8):
        pods_state, flip = "done", 1.0
    elif step == 7:
        pods_state = "done"
        flip = min(1.0, max(0.0, (p - 0.2) / 0.5))
    draw_pods(d, pods_state, flip)

    # badges contextuels
    if step == 3 and not loop_hold:
        draw_trivy_badge(d, p if p > 0 else 0.01)
    elif step is not None and step > 3 or loop_hold:
        draw_trivy_badge(d, 1.0)
    if (step is not None and step >= 5) or loop_hold:
        draw_github_tag(d, "128-a1b2c3d4")

    # pied de page
    if loop_hold:
        rr(d, (30, 668, 1250, 710), 12, fill=hexrgb(PANEL), outline=hexrgb(BORDER))
        d.ellipse((sc(46), sc(678), sc(46 + 22), sc(678 + 22)), fill=hexrgb(GREEN))
        text(d, (57, 689.5), "✓", "bold", 13, "#052e1d", "mm")
        text(d, (84, 689), "Chaque commit déclenche le cycle complet — zéro intervention manuelle, tout est tracé dans Git", "semibold", 15, TEXT)
    elif step is None:
        draw_footer(d, None, len(STEPS), "")
    else:
        draw_footer(d, step, len(STEPS), STEPS[step][0])

    return img.resize((W, H), Image.LANCZOS).convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    static_img = draw_static()
    frames, durations = [], []

    def add(img, ms):
        frames.append(img)
        durations.append(ms)

    n = 0
    # intro
    add(render(None, 0, static_img, 0.0), 1400)
    for si in range(len(STEPS)):
        n_frames = 9 if len(STEPS[si][1]) > 1 or si in (2, 3, 5) else 7
        for k in range(n_frames):
            p = (k + 1) / n_frames
            pulse = 0.5 + 0.5 * math.sin((len(frames)) * 0.9)
            add(render(si, p, static_img, pulse), 520 if k == n_frames - 1 else 110)
    # fin : tout est vert
    for k in range(6):
        add(render(7, 1.0, static_img, 0.5 + 0.5 * math.sin(k * 1.1), loop_hold=True), 2200 if k == 5 else 260)

    # export PNG de la dernière vue (aperçu statique)
    frames[-1].save(OUT / "architecture.png", optimize=True)

    # palette commune (256 couleurs) calculée sur un échantillon d'images -> pas de scintillement
    sample = frames[:: max(1, len(frames) // 10)] + [frames[-1]]
    sheet = Image.new("RGB", (W, H * len(sample)))
    for i, f in enumerate(sample):
        sheet.paste(f, (0, i * H))
    pal_src = sheet.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal_src, dither=Image.Dither.NONE) for f in frames]
    q[0].save(OUT / "architecture.gif", save_all=True, append_images=q[1:], duration=durations, loop=0, optimize=True, disposal=1)
    size = (OUT / "architecture.gif").stat().st_size / 1024
    print(f"{len(frames)} images · architecture.gif = {size:.0f} Ko · architecture.png écrit dans {OUT}")


if __name__ == "__main__":
    main()
