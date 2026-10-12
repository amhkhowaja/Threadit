#!/usr/bin/env python3
"""Generate docs/architecture/threadit-architecture.svg.

Self-contained block diagram of Threadit's IMPLEMENTED architecture using the
official AWS service icons (awslabs/aws-icons-for-plantuml, Apache-2.0) under
docs/architecture/icons/. Icons are base64-embedded so the SVG renders anywhere
(including GitHub) with no external requests.

Layout rules kept deliberately simple so arrows never cross a service box:
every column has a clear gutter, and connectors route through those gutters.
"""

from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT / "docs" / "architecture" / "icons"
OUT = ROOT / "docs" / "architecture" / "threadit-architecture.svg"

W, H = 1440, 860
AWS_ORANGE = "#ec7211"
INK = "#152a3a"
MUTED = "#5a6b7b"
LINE = "#7d93a8"
PANEL = "#ffffff"
VPC_FILL = "#eef5fb"
VPC_STROKE = "#2f6f9f"
EDGE_FILL = "#fff4ea"
DATA_FILL = "#f3f0fa"
DATA_STROKE = "#6b46c1"


def icon_b64(name: str) -> str:
    return base64.b64encode((ICONS / f"{name}.png").read_bytes()).decode()


def img(name: str, x: float, y: float, size: int = 46) -> str:
    return (
        f'<image x="{x:.0f}" y="{y:.0f}" width="{size}" height="{size}" '
        f'href="data:image/png;base64,{icon_b64(name)}" />'
    )


def node(x, y, w, h, title, sub, icon, fill=PANEL, stroke="#d4dde6", badge=None):
    ix = x + 14
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"/>',
        img(icon, ix, y + (h - 46) / 2),
        f'<text x="{ix + 58}" y="{y + h / 2 - 3}" font-size="14.5" font-weight="700" '
        f'fill="{INK}">{title}</text>',
        f'<text x="{ix + 58}" y="{y + h / 2 + 15}" font-size="11" fill="{MUTED}">{sub}</text>',
    ]
    if badge:
        bw = 8 * len(badge) + 16
        parts.append(
            f'<rect x="{x + w - bw - 10}" y="{y + 8}" width="{bw}" height="18" rx="9" '
            f'fill="#fde8e8" stroke="#d64545" stroke-width="1"/>'
            f'<text x="{x + w - bw / 2 - 10}" y="{y + 21}" font-size="10" font-weight="700" '
            f'fill="#b22" text-anchor="middle">{badge}</text>'
        )
    return "\n".join(parts)


def client(x, y, w, h):
    cx = x + 38
    cy = y + h / 2
    glyph = (
        f'<rect x="{cx - 22}" y="{cy - 18}" width="44" height="34" rx="4" fill="#eef2f6" '
        f'stroke="{INK}" stroke-width="1.6"/>'
        f'<line x1="{cx - 22}" y1="{cy - 8}" x2="{cx + 22}" y2="{cy - 8}" stroke="{INK}" stroke-width="1.6"/>'
        f'<circle cx="{cx - 15}" cy="{cy - 13}" r="2" fill="{AWS_ORANGE}"/>'
        f'<circle cx="{cx - 8}" cy="{cy - 13}" r="2" fill="{AWS_ORANGE}"/>'
    )
    return "\n".join(
        [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{PANEL}" '
            f'stroke="#d4dde6" stroke-width="1.5"/>',
            glyph,
            f'<text x="{x + 72}" y="{y + h / 2 - 3}" font-size="14.5" font-weight="700" fill="{INK}">'
            "Browser (SPA)</text>",
            f'<text x="{x + 72}" y="{y + h / 2 + 15}" font-size="11" fill="{MUTED}">React + TS + Vite</text>',
        ]
    )


def group(x, y, w, h, text, fill, stroke):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="2"/>'
        f'<text x="{x + 16}" y="{y + 24}" font-size="12.5" font-weight="700" fill="{stroke}">{text}</text>'
    )


def ortho(points, text="", dash=False, tx=None, ty=None):
    d = ' stroke-dasharray="5 4"' if dash else ""
    path = "M " + " L ".join(f"{px},{py}" for px, py in points)
    t = ""
    if text:
        if tx is None:
            tx = (points[0][0] + points[-1][0]) / 2
        if ty is None:
            ty = points[0][1] - 7
        t = f'<text x="{tx}" y="{ty}" font-size="10.5" fill="{MUTED}" text-anchor="middle">{text}</text>'
    return (
        f'<path d="{path}" fill="none" stroke="{LINE}" stroke-width="2"{d} '
        f'marker-end="url(#arrow)"/>{t}'
    )


def main() -> None:
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/>'
        "</marker></defs>",
        f'<rect width="{W}" height="{H}" fill="#fbfcfd"/>',
        f'<text x="48" y="48" font-size="23" font-weight="800" fill="{INK}">'
        "Threadit &#8212; implemented architecture</text>",
        f'<text x="48" y="72" font-size="12.5" fill="{MUTED}">'
        "Reads are public (edge-cached); writes require Cognito auth. One container image "
        "serves split read/write services behind an ALB.</text>",
    ]

    # Column x-origins with generous gutters:
    #   client 48 | edge 330 | vpc 650 | data 1180
    # Gutters: 290-330, 620-650, 1000-1180 (wide routing channel to data).

    # Cognito (auth) sits on its own top row so nothing routes through it.
    s.append(node(650, 110, 300, 72, "Amazon Cognito", "hosted UI, JWT (OIDC/PKCE)", "Cognito"))

    # Client
    s.append(client(48, 250, 220, 72))

    # Edge group
    s.append(group(330, 210, 270, 250, "Edge / entry", EDGE_FILL, AWS_ORANGE))
    s.append(
        node(346, 244, 238, 76, "CloudFront", "CDN edge cache", "CloudFront", EDGE_FILL, badge="not verified")
    )
    s.append(node(346, 352, 238, 76, "Load Balancer", "POST&#8594;write, else read", "ELB", EDGE_FILL))

    # VPC group
    s.append(group(650, 240, 330, 420, "VPC &#183; public + private subnets (2 AZs)", VPC_FILL, VPC_STROKE))
    s.append(node(670, 280, 294, 80, "ECS Fargate &#8212; read", "post_read :8080 (GET)", "ECS", VPC_FILL))
    s.append(node(670, 400, 294, 80, "ECS Fargate &#8212; write", "post_write :8081 (POST)", "Fargate", VPC_FILL))
    s.append(node(670, 540, 294, 76, "Amazon ECR", "service image registry", "ECR", VPC_FILL))

    # Data group (right), tall column. Boxes inset to leave a RIGHT gutter (x=1372..1392)
    # for the async Streams pipeline so it never crosses a box.
    s.append(group(1180, 110, 250, 650, "Data &#38; search", DATA_FILL, DATA_STROKE))
    s.append(node(1192, 150, 170, 80, "DynamoDB", "single table + GSIs", "DynamoDB", DATA_FILL))
    s.append(node(1192, 260, 170, 76, "S3", "post images", "S3", DATA_FILL))
    s.append(node(1192, 372, 170, 76, "OpenSearch", "search index", "OpenSearch", DATA_FILL))
    s.append(node(1192, 490, 170, 76, "Lambda indexer", "Streams consumer", "Lambda", DATA_FILL))
    s.append(node(1192, 608, 170, 72, "SQS DLQ", "failed events", "SQS", DATA_FILL))

    # ---- connectors (all routed through gutters) ----
    # client -> cloudfront
    s.append(ortho([(268, 286), (346, 286)], "HTTPS"))
    # client -> cognito (up the left, across the top, into Cognito)
    s.append(ortho([(158, 250), (158, 150), (650, 150)], "sign-in / token", dash=True, tx=400, ty=142))
    # cloudfront -> alb (down inside edge group gutter)
    s.append(ortho([(465, 320), (465, 352)]))
    # alb -> read service, alb -> write service
    s.append(ortho([(584, 384), (620, 384), (620, 320), (670, 320)], "GET"))
    s.append(ortho([(584, 400), (604, 400), (604, 440), (670, 440)], "POST (JWT)"))

    # Sync reads/writes enter the data boxes from the LEFT, routed in the channel x=1000..1180.
    # read service -> dynamo / s3 / opensearch (lanes x=1030/1050/1070)
    s.append(ortho([(964, 300), (1030, 300), (1030, 190), (1192, 190)], "Query/Get", tx=1030, ty=175))
    s.append(ortho([(964, 320), (1050, 320), (1050, 298), (1192, 298)], "GET"))
    s.append(ortho([(964, 340), (1070, 340), (1070, 410), (1192, 410)], "search", tx=1086, ty=395))
    # write service -> dynamo / s3 (lanes x=1110/1130)
    s.append(ortho([(964, 420), (1110, 420), (1110, 212), (1192, 212)], "Put/Update", tx=1110, ty=478))
    s.append(ortho([(964, 440), (1130, 440), (1130, 320), (1192, 320)], "PUT"))

    # Async pipeline in the RIGHT gutter (x=1382), clear of all boxes:
    # DynamoDB Streams down to Lambda, Lambda up into OpenSearch (index), Lambda down to DLQ.
    s.append(ortho([(1362, 190), (1388, 190), (1388, 528), (1362, 528)], "Streams", tx=1404, ty=360))
    s.append(ortho([(1277, 490), (1277, 448)], "index", dash=True, tx=1300, ty=472))
    s.append(ortho([(1277, 566), (1277, 608)], "on failure", tx=1304, ty=590))

    # CloudFront -> S3 (images in prod): leave edge bottom, run under everything, up into S3.
    s.append(
        ortho(
            [(465, 428), (465, 710), (1150, 710), (1150, 290), (1192, 290)],
            "images (prod)",
            dash=True,
            tx=800,
            ty=704,
        )
    )

    s.append(
        f'<text x="48" y="{H - 22}" font-size="11" fill="{MUTED}">'
        "Dashed = not exercised end-to-end yet: CloudFront needs AWS account verification, so the "
        "CDN edge-cache path is unverified. Dev uses the same Terraform on the Floci emulator. "
        "AWS icons: awslabs/aws-icons-for-plantuml (Apache-2.0).</text>"
    )
    s.append("</svg>")
    OUT.write_text("\n".join(s))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
