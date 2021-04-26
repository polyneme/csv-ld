import os
from typing import Optional, Union
from pathlib import Path

from fastapi import FastAPI, Response, Header
from fastapi.responses import HTMLResponse
import rdflib

app = FastAPI()

TEST_BASE = "https://ns.csv-ld.org/2021/04/csv-ld/core#"


def load_ttl(filename: Union[Path, str]) -> rdflib.Graph:
    g = rdflib.Graph()
    g.parse(str(filename), format="turtle")
    return g


TERMS = load_ttl(
    os.path.join(os.path.dirname(__file__), "..", "examples", "csvld-core.ttl")
)


def render_html(g: rdflib.Graph) -> str:
    header = """<html>
  <style type="text/css">
    dt { font-weight: bold; text-decoration: underline dotted; }
  </style>
  <body>
    <dl>
"""
    footer = """
    </dl>
  </body>
</html>"""

    dl = ""
    _parsed_subjects = set()
    for subject in g.subjects():
        if subject in _parsed_subjects:
            continue
        _parsed_subjects.add(subject)
        term = subject.split(TEST_BASE)[-1]
        label = g.label(subject)
        comment = g.comment(subject)

        dt = f"""      <dt id="#{term}">{label}</dt>
      <dd>{comment}</dd>"""
        dl += dt

    return header + dl + footer


def sorted_media_types(accept: str) -> bool:
    # e.g. "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    alternatives = [a.split(";") for a in accept.split(",")]
    for a in alternatives:
        # provide default relative quality factor
        # https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html
        if len(a) == 1:
            a.append("q=1")
        # ignore accept-params other than the relative quality factor
        for i, element in enumerate(a):
            if "=" in element and not element.startswith("q"):
                a.pop(i)
    alternatives = sorted(
        [(type_, float(qexpr[2:])) for type_, qexpr in alternatives],
        key=lambda a: a[1],
        reverse=True,
    )
    return [a[0] for a in alternatives]


@app.get("/2021/04/csv-ld/core")
async def root(accept: Optional[str] = Header(None)):
    types_ = sorted_media_types(accept)
    for media_type in types_:
        if media_type == "text/html":
            return HTMLResponse(content=render_html(TERMS), status_code=200)
        elif media_type == "application/ld+json":
            TERMS.namespace_manager.bind("base", TEST_BASE)
            try:
                return Response(
                    content=TERMS.serialize(
                        encoding="utf-8",
                        format=media_type,
                        auto_compact=True,
                    ).decode("utf-8"),
                    media_type=media_type,
                )
            except rdflib.plugin.PluginException:
                continue
        else:
            try:
                return Response(
                    content=TERMS.serialize(
                        base=TEST_BASE, encoding="utf-8", format=media_type
                    ).decode("utf-8"),
                    media_type=media_type,
                )
            except rdflib.plugin.PluginException:
                continue
    else:
        return HTMLResponse(content=render_html(TERMS), status_code=200)
