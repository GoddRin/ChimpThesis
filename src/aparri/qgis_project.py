"""Phase 10D: a ready-to-open QGIS project (``outputs/layers/Aparri_v2.qgz``).

The project loads the rebuilt layers from ``Aparri_Erosion_Risk_v2.gpkg`` (same folder, relative paths), styled
like the thesis maps (green / orange / red).  It was generated from a template of the QGIS 3.x project format and
validated as XML; **it has not been opened in QGIS by the analyst (QGIS is not installed in the analysis
environment)**.  If QGIS complains, open the GeoPackage layers directly and load ``Aparri_Erosion_Risk_v2.qml``
with Layer Properties -> Style -> Load Style; README_QGIS.md explains this.
"""
from __future__ import annotations

import re
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .io import REPO_ROOT, ensure_dir, load_config
from .risk import QML, SYMBOL, write_qml

GPKG = "Aparri_Erosion_Risk_v2.gpkg"
EXTENT = (347000.0, 2025500.0, 369500.0, 2035500.0)     # xmin ymin xmax ymax, EPSG:32651


def srs(epsg: int = 32651) -> str:
    return (f'<spatialrefsys nativeFormat="Wkt"><wkt></wkt><proj4>+proj=utm +zone=51 +datum=WGS84 +units=m +no_defs</proj4><srsid>{3000+epsg%1000}</srsid>'
            f'<srid>{epsg}</srid><authid>EPSG:{epsg}</authid><description>WGS 84 / UTM zone 51N</description><projectionacronym>utm</projectionacronym>'
            f'<ellipsoidacronym>EPSG:7030</ellipsoidacronym><geographicflag>false</geographicflag></spatialrefsys>')


def line_symbol(rgb: str, width: str, dash: str | None = None) -> str:
    style = "dash" if dash else "solid"
    return (f'<symbol type="line" name="0" alpha="1" force_rhr="0" clip_to_extent="1"><layer class="SimpleLine" enabled="1" pass="0" locked="0">'
            f'<Option type="Map"><Option value="round" name="capstyle" type="QString"/><Option value="{rgb},255" name="line_color" type="QString"/>'
            f'<Option value="{style}" name="line_style" type="QString"/><Option value="{width}" name="line_width" type="QString"/>'
            f'<Option value="MM" name="line_width_unit" type="QString"/><Option value="round" name="joinstyle" type="QString"/></Option></layer></symbol>')


def fill_symbol(fill: str, outline: str, width: str, alpha: str = "1") -> str:
    return (f'<symbol type="fill" name="0" alpha="{alpha}" force_rhr="0" clip_to_extent="1"><layer class="SimpleFill" enabled="1" pass="0" locked="0">'
            f'<Option type="Map"><Option value="{fill}" name="color" type="QString"/><Option value="{outline}" name="outline_color" type="QString"/>'
            f'<Option value="solid" name="style" type="QString"/><Option value="{width}" name="outline_width" type="QString"/>'
            f'<Option value="MM" name="outline_width_unit" type="QString"/></Option></layer></symbol>')


def single(symbol: str) -> str:
    return f'<renderer-v2 type="singleSymbol" symbollevels="0" forceraster="0" enableorderby="0" referencescale="-1"><symbols>{symbol}</symbols><rotation/><sizescale/></renderer-v2>'


def risk_renderer() -> str:
    from .risk import write_qml
    tmp = REPO_ROOT / "outputs" / "layers" / "Aparri_Erosion_Risk_v2.qml"
    write_qml(tmp)
    x = tmp.read_text(encoding="utf-8")
    m = re.search(r"<renderer-v2.*?</renderer-v2>", x, re.S)
    return m.group(0)


LAYERS = [
    # (id, name, gpkg layer, geometry, renderer builder, visible)
    ("risk_segments", "Erosion risk classes 2025 (rebuilt)", "risk_segments", "Line", risk_renderer, True),
    ("sh2025", "Shoreline 2025", "shoreline_2025", "Line", lambda: single(line_symbol("0,0,0", "0.5")), True),
    ("sh2020", "Shoreline 2020", "shoreline_2020", "Line", lambda: single(line_symbol("99,99,99", "0.4")), False),
    ("sh2010", "Shoreline 2010", "shoreline_2010", "Line", lambda: single(line_symbol("0,134,139", "0.4")), False),
    ("sh2000", "Shoreline 2000", "shoreline_2000", "Line", lambda: single(line_symbol("33,113,181", "0.4")), False),
    ("sh1990", "Shoreline 1990 (reference)", "shoreline_1990", "Line", lambda: single(line_symbol("106,61,154", "0.5")), True),
    ("transects", "Transects (50 m)", "transects", "Line", lambda: single(line_symbol("120,120,120", "0.15")), False),
    ("study", "Study barangays", "study_barangays", "Polygon", lambda: single(fill_symbol("217,217,217,120", "85,85,85,255", "0.4", "0.6")), True),
]


def maplayer(lid: str, name: str, layer: str, geom: str, renderer: str) -> str:
    return (f'<maplayer type="vector" geometry="{geom}" autoRefreshEnabled="0" hasScaleBasedVisibilityFlag="0" minScale="100000000" maxScale="0" refreshOnNotifyEnabled="0" readOnly="0">'
            f'<id>{lid}</id><datasource>./{GPKG}|layername={layer}</datasource><layername>{name}</layername><srs>{srs()}</srs>'
            f'<provider encoding="UTF-8">ogr</provider>{renderer}<blendMode>0</blendMode><featureBlendMode>0</featureBlendMode><layerOpacity>1</layerOpacity></maplayer>')


def build_qgs() -> str:
    tree = "".join(f'<layer-tree-layer id="{lid}" name="{name}" source="./{GPKG}|layername={layer}" providerKey="ogr" checked="{"Qt::Checked" if vis else "Qt::Unchecked"}" expanded="1"/>'
                   for lid, name, layer, geom, rb, vis in LAYERS)
    order = "".join(f'<layer id="{lid}"/>' for lid, *_ in LAYERS)
    layers = "".join(maplayer(lid, name, layer, geom, rb()) for lid, name, layer, geom, rb, vis in LAYERS)
    x0, y0, x1, y1 = EXTENT
    return (f'<!DOCTYPE qgis PUBLIC \'http://mrcc.com/qgis.dtd\' \'SYSTEM\'><qgis projectname="Aparri erosion v2" version="3.34.0">'
            f'<title>Aparri coastal erosion, 1990-2025 (rebuilt)</title><projectCrs>{srs()}</projectCrs>'
            f'<layer-tree-group name="" checked="Qt::Checked" expanded="1">{tree}</layer-tree-group>'
            f'<mapcanvas name="theMapCanvas" annotationsVisible="1"><units>meters</units><extent><xmin>{x0}</xmin><ymin>{y0}</ymin><xmax>{x1}</xmax><ymax>{y1}</ymax></extent>'
            f'<rotation>0</rotation><destinationsrs>{srs()}</destinationsrs></mapcanvas>'
            f'<projectlayers>{layers}</projectlayers><layerorder>{order}</layerorder>'
            f'<properties><Paths><Absolute type="bool">false</Absolute></Paths></properties></qgis>')


README = """# Opening the QGIS project

1. Keep `Aparri_v2.qgz` and `Aparri_Erosion_Risk_v2.gpkg` in the same folder (the project uses relative paths).
2. Double-click `Aparri_v2.qgz` (QGIS 3.x). The project CRS is EPSG:32651 (UTM 51N, metres) - **measure in this CRS, not in Web Mercator**.
3. Layers: *Erosion risk classes 2025* (green Low / orange Medium / red High; grey = not classified), shorelines 1990-2025, transects, study barangays. Click a segment with the Identify tool for EPR, LRR, confidence, flags.
4. The project file was generated by script and **has not been opened in QGIS by the analyst**. If QGIS reports a problem: *Layer -> Add Layer -> Add Vector Layer* -> choose `Aparri_Erosion_Risk_v2.gpkg`, tick the layers you want, then for the risk layer *Properties -> Symbology -> Style -> Load Style* -> `Aparri_Erosion_Risk_v2.qml`.
5. A print layout in the thesis style: *Project -> New Print Layout*; add the map, legend, scale bar (2.5 km), north arrow; export at 300 dpi.
"""


def run() -> None:  # pragma: no cover
    out = ensure_dir("outputs/layers")
    qgs = build_qgs()
    ET.fromstring(qgs.split("?>", 1)[-1].replace("<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>", ""))      # must be well-formed XML
    with zipfile.ZipFile(out / "Aparri_v2.qgz", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Aparri_v2.qgs", qgs)
    (out / "README_QGIS.md").write_text(README, encoding="utf-8")
    print("wrote", out / "Aparri_v2.qgz")


if __name__ == "__main__":  # pragma: no cover
    run()
