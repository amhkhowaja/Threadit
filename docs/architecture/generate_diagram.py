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

W, H = 1500, 800
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
        f'<text x="48" y="46" font-size="23" font-weight="800" fill="{INK}">'
        "Threadit &#8212; implemented architecture</text>",
        f'<text x="48" y="70" font-size="12.5" fill="{MUTED}">'
        "Reads are public (in-process + DAX cached); writes require Cognito auth and share "
        "a Redis rate-limit window. Edges show the real /v1 endpoints.</text>",
    ]

    # Columns:  client 40 | edge 300 | vpc 600 | cache 970 | data 1210
    # Cognito on the top row so nothing routes through it.
    s.append(node(600, 92, 300, 68, "Amazon Cognito", "hosted UI, JWT (OIDC/PKCE)", "Cognito"))

    # Client
    s.append(client(40, 250, 210, 72))

    # Edge group
    s.append(group(300, 196, 262, 250, "Edge / entry", EDGE_FILL, AWS_ORANGE))
    s.append(
        node(314, 228, 234, 74, "CloudFront", "CDN edge cache", "CloudFront", EDGE_FILL, badge="not verified")
    )
    s.append(node(314, 336, 234, 74, "Load Balancer", "method-routed", "ELB", EDGE_FILL))

    # VPC group with read/write services (read box carries the in-process cache chip)
    s.append(group(600, 196, 330, 430, "VPC &#183; public + private subnets (2 AZs)", VPC_FILL, VPC_STROKE))
    s.append(node(618, 236, 294, 86, "ECS Fargate &#8212; read", "post_read :8080", "ECS", VPC_FILL))
    # in-process SingleFlight cache chip inside the read box
    s.append(
        f'<rect x="820" y="246" width="86" height="20" rx="10" fill="#e8f3ec" stroke="#2e8b57"/>'
        f'<text x="863" y="260" font-size="9.5" fill="#2e8b57" text-anchor="middle" '
        f'font-weight="700">SingleFlight</text>'
    )
    s.append(node(618, 360, 294, 86, "ECS Fargate &#8212; write", "post_write :8081", "Fargate", VPC_FILL))
    s.append(node(618, 520, 294, 72, "Amazon ECR", "service image registry", "ECR", VPC_FILL))

    # Cache tier (newly-wired): DAX for read cache, ElastiCache for shared rate-limit state.
    s.append(group(970, 196, 190, 300, "Cache tier", "#eaf4ef", "#2e8b57"))
    s.append(node(982, 234, 166, 76, "DAX", "DynamoDB read cache", "DAX", "#eaf4ef", "#2e8b57"))
    s.append(node(982, 330, 166, 76, "ElastiCache", "Redis: rate-limit state", "ElastiCache", "#eaf4ef", "#2e8b57"))
    s.append(
        f'<text x="982" y="470" font-size="10.5" fill="#2e8b57">in-process SingleFlight</text>'
        f'<text x="982" y="486" font-size="10.5" fill="#2e8b57">cache lives in the read svc</text>'
    )

    # Data group (right), tall column.
    s.append(group(1210, 92, 220, 668, "Data &#38; search", DATA_FILL, DATA_STROKE))
    s.append(node(1222, 132, 196, 76, "DynamoDB", "single table + GSIs", "DynamoDB", DATA_FILL))
    s.append(node(1222, 240, 196, 72, "S3", "post images", "S3", DATA_FILL))
    s.append(node(1222, 352, 196, 72, "OpenSearch", "search index", "OpenSearch", DATA_FILL))
    s.append(node(1222, 470, 196, 72, "Lambda indexer", "Streams consumer", "Lambda", DATA_FILL))
    s.append(node(1222, 590, 196, 68, "SQS DLQ", "failed events", "SQS", DATA_FILL))

    # ---- connectors with real endpoints ----
    # Routing channel into the data column lives at x=1185 (between cache grp right
    # x=1160 and data grp left x=1210). The read svc right edge is x=912; the data
    # boxes' left edge is x=1222.

    # client -> cloudfront
    s.append(ortho([(250, 286), (314, 286)], "HTTPS"))
    # client -> cognito (up the left margin, across the top)
    s.append(ortho([(145, 250), (145, 126), (600, 126)], "OIDC sign-in / token", dash=True, tx=360, ty=118))
    # cloudfront -> alb (inside edge group)
    s.append(ortho([(431, 302), (431, 336)]))
    # alb -> read (GET), alb -> write (POST)
    s.append(ortho([(548, 360), (583, 360), (583, 279), (618, 279)], "GET /v1/posts, /{id}", tx=600, ty=250))
    s.append(ortho([(548, 386), (570, 386), (570, 403), (618, 403)], "POST /v1/posts (+comments)", tx=612, ty=478))

    # READ service -> DAX (cached read) -> DynamoDB
    s.append(ortho([(912, 258), (982, 258)], "cached read"))
    s.append(ortho([(1148, 272), (1185, 272), (1185, 170), (1222, 170)], "GetItem/Query", tx=1150, ty=150))
    # READ service -> OpenSearch (search) : own lane at x=950 up/over into the channel
    s.append(ortho([(912, 300), (950, 300), (950, 540), (1185, 540), (1185, 388), (1222, 388)],
                    "GET /v1/posts?search_keyword", tx=1030, ty=556))

    # WRITE service -> ElastiCache (rate-limit state)
    s.append(ortho([(912, 392), (982, 392)], "rate-limit (Redis)"))
    # WRITE service -> DynamoDB (Put/Update) : lane at x=962 into the channel, up to DynamoDB
    s.append(ortho([(912, 410), (962, 410), (962, 560), (1200, 560), (1200, 190), (1222, 190)],
                    "PutItem/UpdateItem", tx=1035, ty=576))
    # WRITE service -> S3 (presigned PUT) and READ service -> S3 (presigned GET)
    s.append(ortho([(912, 428), (974, 428), (974, 580), (1205, 580), (1205, 262), (1222, 262)],
                    "S3 presigned PUT/GET", tx=1060, ty=596))

    # Async pipeline in the data group's right gutter (x=1452), clear of boxes.
    s.append(ortho([(1418, 170), (1452, 170), (1452, 508), (1418, 508)], "Streams", tx=1462, ty=340))
    s.append(ortho([(1320, 470), (1320, 424)], "index", dash=True, tx=1344, ty=452))
    s.append(ortho([(1320, 542), (1320, 590)], "on failure", tx=1350, ty=570))

    # CloudFront -> S3 images (prod), dashed: down from edge, under everything, into S3.
    s.append(
        ortho(
            [(431, 410), (431, 740), (1210, 740), (1210, 300), (1222, 300)],
            "images via CDN (prod)",
            dash=True,
            tx=820,
            ty=734,
        )
    )

    s.append(
        f'<text x="48" y="{H - 20}" font-size="11" fill="{MUTED}">'
        "Dashed = not exercised end-to-end yet (CloudFront needs AWS account verification). "
        "Cache tier (DAX + ElastiCache + in-process SingleFlight) and the rate limiter are wired. "
        "AWS icons: awslabs/aws-icons-for-plantuml (Apache-2.0).</text>"
    )
    s.append("</svg>")
    OUT.write_text("\n".join(s))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
