"""Build the complete thesis manuscript (DOCX) from the department-format original + the rebuilt GIS results.

    python -m aparri.manuscript          ->  outputs/manuscript/Thesis_Manuscript_FINAL_DRAFT.docx

* The original docx is only READ (its Chapter I-II text, references, questionnaire and work schedule are carried over).
* Chapter III-V are written from the pipeline results. Yellow [bracketed] text = a fact only the students can supply.
* No number is invented: every figure comes from outputs/tables/*.csv or from the original manuscript.
"""
from __future__ import annotations

import re
from pathlib import Path

import docx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from .docx_kit import Manuscript
from .io import ensure_dir
from .orig_text import ORIG, blocks

OUT = Path("outputs/manuscript")
MAPS = Path("outputs/maps")
TAB = Path("outputs/tables")
TITLE = ("DEVELOPMENT OF CONSTRUCTION MANAGEMENT FRAMEWORK FOR SHORELINE PROTECTION STRUCTURES "
         "BASED ON COASTAL EROSION RISK LEVELS IN APARRI, CAGAYAN")
AUTHORS = ["RIZABELL F. BRUNO", "SANDARA MARIE M. CABAUATAN", "ROSS ANN D. MORA", "PHOEBE KATE S. UBANDO"]


# --------------------------------------------------------------------------------------------- figures drawn here
def _box(ax, xy, w, h, text, fc="#e8f0fa", ec="#1f3a68", fs=9):
    ax.add_patch(FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02,rounding_size=0.03", fc=fc, ec=ec, lw=1.4))
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=fs, wrap=True)


def _arrow(ax, a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=14, lw=1.4, color="#1f3a68"))


def fig_concept(path: Path):
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.set_xlim(0, 9); ax.set_ylim(0, 4.8); ax.axis("off")
    for t, x in (("INPUT", 1.5), ("PROCESS", 4.5), ("OUTPUT", 7.5)):
        ax.text(x, 4.55, t, ha="center", fontsize=12, weight="bold")
    W, H = 2.6, 0.85
    _box(ax, (0.2, 3.0), W, H, "Shoreline positions\n1990, 2000, 2010, 2020, 2025", fs=10)
    _box(ax, (0.2, 0.8), W, H, "Expert opinions\n(54 respondents, Likert scale)", fs=10)
    _box(ax, (3.2, 3.0), W, H, "GIS analysis: transects and\nshoreline change rate", fs=10)
    _box(ax, (3.2, 1.9), W, H, "Classification:\nLow / Medium / High", fs=10)
    _box(ax, (3.2, 0.8), W, H, "Weighted mean and\ndecision matrix", fs=10)
    _box(ax, (6.2, 3.0), W, H, "Erosion risk map and\nbarangay table", fs=10)
    _box(ax, (6.2, 1.9), W, H, "Construction management\nframework", fc="#fdf1d6", ec="#9a6a00", fs=10)
    _box(ax, (6.2, 0.8), W, H, "Ranking of the structures", fs=10)
    _arrow(ax, (2.8, 3.42), (3.2, 3.42)); _arrow(ax, (4.5, 3.0), (4.5, 2.75))
    _arrow(ax, (5.8, 3.42), (6.2, 3.42)); _arrow(ax, (5.8, 2.32), (6.2, 2.32))
    _arrow(ax, (2.8, 1.22), (3.2, 1.22)); _arrow(ax, (5.8, 1.22), (6.2, 1.22)); _arrow(ax, (7.5, 1.65), (7.5, 1.9))
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig)


def fig_framework(path: Path):
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.set_xlim(0, 9); ax.set_ylim(0, 5.2); ax.axis("off")
    steps = ["1. Measure the\nshoreline change\n(1990–2025)", "2. Classify the coast:\nLow (<2), Medium (2–5),\nHigh (>5 m/year)",
             "3. Choose structure\noptions for the class\n(Table 4.8)", "4. Apply the four\nmanagement phases"]
    for i, t in enumerate(steps):
        _box(ax, (0.2 + i * 2.2, 3.9), 2.0, 1.0, t, fs=9.5)
        if i:
            _arrow(ax, (0.2 + i * 2.2 - 0.2, 4.4), (0.2 + i * 2.2, 4.4))
    ax.text(4.5, 3.45, "Management phases (requirements are stricter for higher classes)", ha="center", fontsize=10,
            style="italic")
    phases = ["PLANNING", "DESIGN", "CONSTRUCTION", "MONITORING AND\nMAINTENANCE"]
    for i, t in enumerate(phases):
        _box(ax, (0.2 + i * 2.2, 2.2), 2.0, 0.9, t, fc="#fdf1d6", ec="#9a6a00", fs=10)
        if i:
            _arrow(ax, (0.2 + i * 2.2 - 0.2, 2.65), (0.2 + i * 2.2, 2.65))
    _arrow(ax, (7.8, 3.9), (7.8, 3.6))
    _box(ax, (0.2, 0.4), 8.0, 0.8, "Re-measure the shoreline regularly and update the classes", fc="#e3f2e6",
         ec="#2e7d4f", fs=10)
    _arrow(ax, (7.8, 2.2), (7.8, 1.2))
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig)


def extract_study_area_map(path: Path):
    d = docx.Document(str(ORIG))
    for rel in d.part.rels.values():
        if rel.reltype.endswith("/image") and rel.target_part.partname.endswith("image4.jpeg"):
            path.write_bytes(rel.target_part.blob)
            return True
    return False


# --------------------------------------------------------------------------------------------- content helpers
def f2(x, d=2):
    return f"{x:+.{d}f}".replace("-", "−") if isinstance(x, (int, float)) else str(x)


def load_tables():
    t41 = pd.read_csv(TAB / "Table_4_2_barangay_results.csv")
    ext = pd.read_csv(TAB / "Table_4_2_extended.csv")
    pri = pd.read_csv(TAB / "priority_ranking_field_inspection.csv")
    return t41, ext, pri


def carry(m: Manuscript, lo, hi, skip_first_heading=False, drop_head=None, verify=()):
    """Copy original paragraphs (cleaned). verify = keywords; paragraphs containing one get a [VERIFY CITATION] tag."""
    first = True
    for k, t in blocks(lo, hi):
        if first and skip_first_heading and k.startswith("h"):
            first = False
            continue
        first = False
        if drop_head and k.startswith("h") and t in drop_head:
            continue
        if re.fullmatch(r"\(.{1,6}\)", t):
            continue                                   # stray formula fragment
        mm = re.match(r"Erosion Rate = 2 1 (Where.*)", t)
        if mm:
            m.eq("EPR = (S₂ − S₁) / T")
            t = mm.group(1)
        if k == "h3":
            m.h(t, 2)
        elif k in ("h1", "h2"):
            m.h(t, 2)
        elif k == "list":
            m.lst([t])
        else:
            if not t.endswith(tuple('.?!:;)”"]')):
                t += "."
            if any(v in t for v in verify):
                t += " [[VERIFY CITATION]]"
            m.p(t)


# --------------------------------------------------------------------------------------------- the document
def build():
    ensure_dir(OUT)
    t41, ext, pri = load_tables()
    fig_concept(OUT / "fig_concept.png")
    fig_framework(OUT / "fig_framework.png")
    have_map = extract_study_area_map(OUT / "fig_study_area_orig.jpeg")
    src = docx.Document(str(ORIG))

    m = Manuscript()
    m.first_section(header=False)

    # ---------------------------------------------------------------- cover
    for _ in range(2):
        m.p("", indent=False)
    m.p("**" + TITLE + "**", indent=False, align="c", spacing=1.3, after=30, size=14)
    m.p("Presented to the Faculty of the College of Engineering and Architecture", indent=False, align="c")
    m.p("**CAGAYAN STATE UNIVERSITY**", indent=False, align="c")
    m.p("Carig Campus, Tuguegarao City, Cagayan", indent=False, align="c", after=30)
    m.p("In Partial Fulfillment of the Requirements for the Degree", indent=False, align="c")
    m.p("**BACHELOR OF SCIENCE IN CIVIL ENGINEERING**", indent=False, align="c", after=36)
    for a in AUTHORS:
        m.p(a, indent=False, align="c", spacing=1.2, after=2)
    m.p("", indent=False)
    m.p("[[Month Year of final defense]]", indent=False, align="c")

    # ---------------------------------------------------------------- approval sheet
    m.h("APPROVAL SHEET", 1, page_break=True, toc=False)
    m.p("This thesis titled “" + TITLE + "”, prepared and submitted by " + ", ".join(AUTHORS[:3]) + ", and "
        + AUTHORS[3] + " in partial fulfillment of the requirements for the degree, Bachelor of Science in Civil "
        "Engineering major in Construction Engineering Management, is hereby recommended for final oral examination.",
        spacing=1.3)
    m.p("", indent=False)
    m.p("**ENGR. MARK LESTER CAGURANGAN**\nAdviser", indent=False, align="c", spacing=1.1)
    m.p("Approved by the Tribunal on Oral Examination with a grade of ________.", indent=False, after=14)
    m.p("**ENGR. JOWELL JOHN B. TALOSIG**\nChairman", indent=False, align="c", spacing=1.1, after=10)
    m.p("**ENGR. ARISTOTLE JAMES M. AGANON**\t\t**ENGR. FELIPE NEIL C. PINTUCAN**\nMember\t\t\t\t\t\tMember",
        indent=False, align="c", spacing=1.1, after=10, size=11)
    m.p("**ENGR. JOSEPH R. CABALBAG, ME**\nDepartment Chair", indent=False, align="c", spacing=1.1, after=14)
    m.p("Accepted and approved in partial fulfillment of the requirements for the degree, Bachelor of Science in "
        "Civil Engineering major in Construction Engineering Management.", spacing=1.2)
    m.p("Date: ____________________\t\t**ENGR. JOHN MICHAEL B. CASIBANG, MSc**\n\t\t\t\t\t\tDean, College of Engineering and Architecture",
        indent=False, spacing=1.2, size=11)

    # ---------------------------------------------------------------- front matter (roman numerals)
    m.new_section(numfmt="lowerRoman", restart=True, header=True)
    m.h("ACKNOWLEDGMENT", 1)
    m.p("[[STUDENTS: write the acknowledgment — thank the adviser, panel, the Aparri LGU/MDRRMO/DPWH offices, the 54 "
        "respondents, family. The project files contain no acknowledgment text, so none was invented.]]")
    m.h("ABSTRACT", 1, page_break=True)
    m.p("**Title:** " + TITLE, indent=False, spacing=1.15)
    m.p("**Researchers:** " + "; ".join(AUTHORS) + "      **Adviser:** Engr. Mark Lester Cagurangan      "
        "**Institution:** Cagayan State University – Carig Campus      **Degree:** BS Civil Engineering", indent=False,
        spacing=1.15)
    m.p("Coastal erosion threatens the barangays along the Aparri, Cagayan shoreline, yet shoreline protection "
        "structures are often chosen after damage has occurred and without a measured basis. This study classified "
        "the erosion of the open coast of eight barangays (Dodan, Maura, Bulala Norte, Bulala Sur, San Antonio, "
        "Linao, Paddaya and Punta), compared five shoreline protection structures through expert judgment, and "
        "proposed a construction management framework that links the two.")
    m.p("Shoreline positions for 1990, 2000, 2010, 2020 and 2025 were processed in a Geographic Information System "
        "(GIS). Along 415 lines drawn every 50 m across the coast (373 usable), the End Point Rate, the distance the "
        "shoreline moved between 1990 and 2025 divided by 35 years, was computed and classed as Low (below 2 m/year), "
        "Medium (2–5 m/year) or High (above 5 m/year) erosion. Fifty-four experts rated seawalls, revetments, riprap, "
        "breakwaters and mangrove rehabilitation on six criteria using a five-point scale, and the ratings were "
        "analyzed by weighted mean.")
    m.p("The median shoreline change was −1.46 m/year, and 94 % of the usable transects moved landward. Of the 18.8 km "
        "of classified open coast, 13.8 km (73 %) were Low and 5.0 km (27 %) were Medium; no stretch reached the High "
        "class. The highest mean erosion rates were in Bulala Norte (−3.35 m/year) and Bulala Sur (−2.74 m/year); "
        "both are entirely Medium. Because the class limits lie close to the typical rates, the Low/Medium boundary is "
        "uncertain for Dodan and Linao. The experts ranked the seawall first (overall mean 4.35, Very High), followed by "
        "mangrove rehabilitation (4.14), revetment (3.99), breakwater (3.71) and riprap (3.63). The proposed framework "
        "applies four management phases — planning, design, construction, and monitoring and maintenance — with "
        "stronger requirements for Medium than for Low stretches.")
    m.p("The results describe erosion rate only; exposure of buildings and people, field verification, and measured "
        "positional errors of the shorelines were not part of this study.")
    m.p("**Keywords:** coastal erosion; shoreline protection structures; shoreline change rate; risk classification; "
        "GIS; weighted mean; construction management framework", indent=False)

    # TOC / lists are filled at the end (need heading list)
    toc_marker = len(m.doc.paragraphs)
    m.h("TABLE OF CONTENTS", 1, page_break=True, toc=False)
    toc_placeholder_idx = len(m.doc.element.body) - 1

    # ---------------------------------------------------------------- body (arabic)
    m.new_section(numfmt="decimal", restart=True, header=True)

    # =============================== CHAPTER I
    m.h("CHAPTER I\nTHE PROBLEM AND ITS BACKGROUND", 1)
    m.h("Introduction", 2)
    carry(m, 191, 211, verify=())
    m.h("Statement of the Problem", 2)
    carry(m, 213, 218)
    m.h("Objectives of the Study", 2)
    m.h("General Objective", 3)
    m.p("To develop a construction management framework for shoreline protection structures in Aparri, Cagayan based "
        "on coastal erosion risk levels.")
    m.h("Specific Objectives", 3)
    m.lst(["To classify the coast of the study area into low, medium, and high levels of coastal erosion risk;",
           "To determine the most suitable shoreline protection structures in terms of their perceived efficiency and "
           "feasibility;",
           "To rank the shoreline protection structures for the study area as a whole and to relate the ranking to the "
           "erosion risk levels found along the coast; and",
           "To develop a construction management framework for shoreline protection structures according to the "
           "coastal erosion risk levels in Aparri, Cagayan."], numbered=True)
    m.h("Conceptual Framework of the Study", 2)
    m.p("Figure 1.1 shows the framework of the study. The inputs are the shoreline positions of five years and the "
        "opinions of expert respondents. In the process, the shoreline positions are analyzed in a Geographic "
        "Information System to obtain the shoreline change rate of each stretch of coast, and each stretch is "
        "classified as Low, Medium or High erosion. The expert ratings are summarized with the weighted mean and "
        "entered in a decision matrix. The outputs are the erosion risk map, the ranking of the structures and the "
        "construction management framework. Coastal erosion factors such as waves, sediment supply and coastal "
        "development are discussed from the literature (Chapter II) to help explain shoreline behavior; they were not "
        "measured in this study.")
    m.figure(OUT / "fig_concept.png", "Figure 1.1. Conceptual framework of the study", width=5.6)
    m.h("Hypothesis of the Study", 2)
    m.p("The following hypothesis was tested at the 0.05 level of significance:")
    m.lst(["**Ho1:** There is no significant difference in the perceived suitability (efficiency and feasibility) "
           "among the shoreline protection structures evaluated by the expert respondents.",
           "**Ha1:** There is a significant difference in the perceived suitability (efficiency and feasibility) among "
           "the shoreline protection structures evaluated by the expert respondents."])
    m.p("The questionnaire asked each expert to rate every structure once for the study area as a whole. It did not ask "
        "for separate ratings at Low, Medium and High erosion; therefore the hypothesis compares the structures with "
        "one another, and the matching of structures to risk levels in the framework is presented as the researchers’ "
        "proposal based on the ratings and the literature (Chapter IV).")
    carry(m, 255, 270)
    m.h("Scope and Delimitation", 2)
    m.p("This research deals with a construction management framework for shoreline protection structures along the "
        "open, sea-facing coast of the coastal barangays of Aparri, Cagayan, namely Linao, Maura, Punta, San Antonio, "
        "Bulala Sur, Bulala Norte, Dodan and Paddaya, which together form a continuous shoreline experiencing "
        "coastal erosion.")
    m.p("The erosion risk level was determined from the shoreline change rate between 1990 and 2025 using shoreline "
        "positions of 1990, 2000, 2010, 2020 and 2025. The classes therefore describe the speed of shoreline movement "
        "only; they do not measure the exposure of buildings, roads or people, or the physical condition of existing "
        "structures. The banks of the Cagayan River mouth, where the shoreline is also shaped by river discharge, were "
        "separated from the open coast and were not classified.")
    m.p("The efficiency and feasibility of shoreline protection structures were evaluated, compared and ranked "
        "through the weighted mean of expert judgment. The study did not design or build any structure, did not "
        "perform physical or numerical modeling of waves and sediments, and did not include field measurements of "
        "coastal erosion factors.")
    m.h("Definition of Terms", 2)
    defs = [
        ("Accretion", "Seaward movement of the shoreline; the beach grows. In this study it has a positive rate."),
        ("Anthropogenic", "Caused by human activities, for example coastal development or sand extraction."),
        ("Baseline", "A reference line drawn on land, behind all shorelines, from which distances to each shoreline "
                     "are measured."),
        ("Coastal Erosion", "The wearing away of the coast so that the shoreline moves toward the land."),
        ("Coastal Erosion Factors", "Natural and human influences that affect shoreline behavior, such as waves, tides, "
                                    "sediment supply, sea-level rise, storms and coastal development."),
        ("Construction Management Framework (CMF)", "An organized set of steps and requirements that guides the "
                                                    "planning, design, construction and monitoring of shoreline "
                                                    "protection structures."),
        ("Cronbach’s Alpha", "A number from 0 to 1 that shows whether the items of a questionnaire give consistent "
                              "results. A value of 0.70 or more is considered acceptable."),
        ("End Point Rate (EPR)", "The distance the shoreline moved between the first and the last year, divided by the "
                                 "number of years. A negative EPR means erosion (landward movement); a positive EPR "
                                 "means accretion."),
        ("Erosion Risk Map", "A map that colors each stretch of shoreline as Low, Medium or High according to its "
                             "erosion rate, to show where attention is needed first."),
        ("Geographic Information System (GIS)", "Computer software for storing, measuring and mapping data that have "
                                                "a location, such as shorelines."),
        ("Google Earth Engine", "A free online service of Google for processing satellite images."),
        ("Hybrid Engineering", "Combining hard structures (for example a seawall) with soft, natural measures "
                               "(for example mangroves)."),
        ("Landsat", "A series of Earth-observation satellites whose images have a pixel size of 30 m."),
        ("Likert Scale", "A rating scale; here 1 (Not Appropriate) to 5 (Highly Appropriate)."),
        ("Linear Regression Rate (LRR)", "The shoreline change rate obtained by fitting a straight line through the "
                                         "shoreline positions of all years."),
        ("Net Shoreline Movement (NSM)", "The total distance, in meters, between the earliest and the latest "
                                         "shoreline along a transect."),
        ("Normalized Difference Water Index (NDWI)", "A value computed from satellite image bands that separates "
                                                     "water from land."),
        ("Open Coast", "The sea-facing shoreline, as distinguished from the banks of a river mouth."),
        ("Pixel", "One square cell of a satellite image; for Landsat it measures 30 m by 30 m."),
        ("Scouring", "The removal of sand or soil at the base of a structure by waves or currents, which can "
                     "undermine the structure."),
        ("Shoreline", "The line where land meets the sea, used as a reference to track changes along the coast."),
        ("Shoreline Protection Structures", "Man-made or nature-based works that reduce shoreline erosion: seawalls, "
                                            "revetments, riprap, breakwaters and mangrove rehabilitation."),
        ("Transect", "A straight line drawn across the coast at right angles to the baseline, along which the "
                     "position of each year’s shoreline is measured."),
        ("Weighted Mean", "The average of ratings in which each rating is multiplied by how many respondents gave it."),
    ]
    for term, d_ in defs:
        m.p(f"**{term}.** {d_}", indent=False, spacing=1.15, after=4)

    # =============================== CHAPTER II
    m.h("CHAPTER II\nREVIEW OF RELATED LITERATURE", 1, page_break=True)
    carry(m, 319, 657, verify=("Nerves", "Calapini, W. D. et al. (2025)", "Nieuwenhout", "Luijendijk et al. (2018)"))

    # =============================== CHAPTER III
    m.h("CHAPTER III\nMETHODOLOGY", 1, page_break=True)
    m.p("This chapter explains how the study was carried out: the study area, the research design, the way the "
        "shoreline change was measured and classified, the survey of experts, and the statistical tools used.")
    m.h("3.1 General Overview", 2)
    m.p("The study used a mixed-method design. The quantitative part measured the movement of the shoreline in a "
        "Geographic Information System and classified the erosion risk; the second part gathered the judgment of "
        "experts on five shoreline protection structures and analyzed it with the weighted mean. Both results were "
        "then combined into a construction management framework.")
    m.h("3.2 Study Area", 2)
    m.p("The study was conducted in eight barangays of Aparri, Cagayan, namely Linao, Maura, Punta, San Antonio, "
        "Bulala Sur, Bulala Norte, Dodan and Paddaya. These barangays share one continuous shoreline and are influenced by the same coastal processes, including wave action, storm surges and "
        "monsoon winds. The open coast covered by the analysis measured about 20 km (Figure 3.1).")
    if have_map:
        m.figure(OUT / "fig_study_area_orig.jpeg", "Figure 3.1. Map of Aparri, Cagayan", width=5.0)
    m.h("3.3 Research Design", 2)
    m.p("The design combined quantitative GIS analysis and an expert survey. First, the shoreline change rate was "
        "computed and used to classify erosion risk as low, medium or high. Second, five shoreline protection "
        "structures were evaluated by experts and ranked using weighted means. Third, the two results were combined into "
        "a construction management framework suited to the local conditions of the selected parts of Aparri.")
    m.h("3.4 Shoreline Change and Risk Assessment Method", 2)
    m.h("3.4.1 Shoreline data", 3)
    m.p("Shoreline positions for 1990, 2000, 2010, 2020 and 2025 were represented as lines in a Geographic "
        "Information System. Two sets of shorelines were available. The main set consisted of shoreline lines "
        "supplied in the project files; the second set was traced from Landsat water-index images (Normalized "
        "Difference Water Index, McFeeters, 1996 [[VERIFY CITATION]]) prepared in Google Earth Engine (Gorelick et "
        "al., 2017 [[VERIFY CITATION]]) at 30 m resolution, and was used as an independent check. "
        "[[STUDENTS: state who prepared the main shoreline lines, from which imagery (sensor and acquisition date of "
        "each year) and which shoreline indicator (for example the water line) was used; the project files do not "
        "record this.]]")
    m.h("3.4.2 Preparation of the shoreline lines", 3)
    m.p("All data were converted to the WGS 84 / UTM zone 51N coordinate system (EPSG:32651) so that distances and "
        "areas are in meters. The shoreline lines arrived as 19 loose pieces for the five years. A scripted and logged "
        "procedure removed stretches digitized twice within a year (18.3 km in 2010), joined ends closer than 5 m, "
        "removed small self-crossing loops (shorter than 50 m), and set aside one feature whose year could not be "
        "read, which was not analyzed. The cleaned lines were then divided into the open sea-facing coast and the "
        "banks of the Cagayan River mouth by a fixed geometric rule (distance of 350 m from the outer outline of all "
        "shorelines). Only the open coast, about 20 km per year, was classified, because river banks respond to river "
        "flow and sandbar movement and not to waves alone.")
    m.h("3.4.3 Baseline and transects", 3)
    m.p("A baseline was drawn on the land side of all shorelines. It was made by smoothing the 1990 shoreline over "
        "200 m and shifting it landward by the largest landward position of any year plus 150 m. The land side was "
        "decided by testing which side contained the barangay areas. Transects, straight lines at right angles to the "
        "baseline, were generated every 50 m (Figure 3.2). This produced 415 transects, of which 373 were valid, "
        "meaning that they crossed both the 1990 and the 2025 shoreline and did not cross a neighboring transect. "
        "This approach follows the Digital Shoreline Analysis System of the U.S. Geological Survey (Thieler et al., "
        "2009).")
    m.figure(MAPS / "method_transect_diagram.png", "Figure 3.2. Baseline, transects and shoreline positions used to "
             "measure change", width=5.3)
    m.h("3.4.4 Shoreline change rates", 3)
    m.p("On every transect the distance from the baseline to each year’s shoreline was measured. Three quantities were "
        "computed:")
    m.lst(["**Net Shoreline Movement (NSM)** = distance in 2025 − distance in 1990, in meters;",
           "**End Point Rate (EPR)** = NSM ÷ T, where T = 35 years (2025 − 1990);",
           "**Linear Regression Rate (LRR)**, the slope of the straight line fitted through the shoreline positions of "
           "all five years, reported beside the EPR."])
    m.eq("EPR = (S₂ − S₁) / T")
    m.p("where S₂ is the shoreline position in the later year (2025), S₁ the position in the earlier year (1990) and T "
        "the time between them in years. A negative value means the shoreline moved landward (erosion); a positive "
        "value means it moved seaward (accretion). The exact acquisition dates of the images were not available; the "
        "difference of the years was used for T.", indent=False)
    m.h("3.4.5 Classification and summary by barangay", 3)
    m.p("Each transect was assigned an erosion risk class from the size of its landward rate (Table 3.1). Transects "
        "with positive EPR (accretion) were counted as Low and marked as accreting. Transects that crossed their "
        "neighbors, found near the river mouth, were left unclassified. The 2025 shoreline was cut into segments at "
        "the mid-points between transects, and each segment took the class of its transect. Segments were assigned to "
        "the nearest study barangay within 500 m. For each barangay the mean, minimum and maximum EPR and the length "
        "of shoreline in each class were computed. Areas in hectares were obtained as length multiplied by a 100 m "
        "coastal strip, so that kilometers remain the primary measure.")
    m.table("Table 3.1. Classification of coastal erosion risk level", ["Risk level", "Erosion rate (m/year)"],
            [["Low", "less than 2"], ["Medium", "2 to 5 (limits included)"], ["High", "more than 5"]],
            widths=[2.0, 2.6], note="Note: Erosion rate is the size of a negative EPR. The limits follow the classes "
            "used in the literature reviewed in Chapter II (see Luijendijk et al., 2018 [[VERIFY CITATION]]).")
    m.h("3.4.6 Uncertainty and quality checks", 3)
    m.p("The images have a pixel of 30 m. If each shoreline is uncertain by one pixel, a 35-year end-point rate is "
        "uncertain by √2 × 30 ÷ 35 = 1.21 m/year. Because no measured positional error was available, this value was "
        "used only as a what-if band to label the confidence of the classes; the classification was not adjusted by "
        "it. The computer procedure was tested with artificial shorelines of known movement (a straight coast "
        "retreating exactly 2.000 m/year or advancing 1.500 m/year, circular arcs, missing years, loops and "
        "reversed land/sea sides). It was also compared with the second shoreline set (Landsat-traced), and its "
        "sensitivity to the technical choices (transect spacing, smoothing, baseline distance, which crossing to keep) "
        "and to the class limits was tested.")
    m.h("3.5 Population and Sample", 2)
    m.p("The respondents were people with knowledge and experience in coastal engineering, construction management and "
        "shoreline protection: licensed civil engineers, engineers of the Department of Public Works and Highways "
        "(DPWH), coastal or environmental engineers, contractors, and technical personnel of local government units "
        "(LGUs). Purposive sampling was used, so that only those qualified and knowledgeable about shoreline erosion "
        "and protection were selected. A total of 54 experts responded. [[STUDENTS: state how many were invited, the "
        "response rate and the period of data gathering.]]")
    m.h("3.6 Research Instrument", 2)
    m.p("Three instruments were used. First, GIS software processed the spatial data and computed the shoreline change "
        "rates (QGIS and Python, with the settings listed in Appendix C). Second, an Expert Evaluation Questionnaire "
        "(Appendix B) collected the ratings of professionals on the efficiency and feasibility of the structures using "
        "a five-point Likert scale. Third, secondary data such as maps, reports and literature supported the "
        "interpretation of the results.")
    m.h("3.7 Data Gathering Procedure", 2)
    m.p("The research adviser and the Dean of the College of Engineering and Architecture endorsed the study, and "
        "permission was sought from the offices concerned for the secondary data. The secondary "
        "data consisted of shoreline lines, satellite images and government records on the shorelines of Aparri for the "
        "years 1990, 2000, 2010, 2020 and 2025. The questionnaire was given to the chosen "
        "respondents after the purpose of the study had been explained, their participation was voluntary and their "
        "answers were assured to be confidential. The retrieved questionnaires were compiled and analyzed together with "
        "the shoreline results. Field observation of the shoreline was not part of the analysis reported here; it is "
        "listed as a limitation and a recommendation in Chapter V, and a field verification form is provided in "
        "Appendix E. [[STUDENTS: confirm that the endorsement and permission letters were obtained as planned, and whether site visits were made; if yes, add the dates, barangays and findings here.]]")
    m.h("3.8 Evaluation and Ranking of Shoreline Protection Structures", 2)
    m.p("The respondents rated five structures (seawall, revetment, riprap, breakwater and mangrove rehabilitation) on "
        "six criteria: stability, effectiveness, cost of construction, durability, maintenance requirements and "
        "environmental impact. The weighted mean of each criterion was computed, and the six criterion means were "
        "averaged with equal weights into an overall mean that was entered in a decision matrix. The structure with the "
        "highest overall mean was ranked first. The overall means were interpreted with the scale in Table 3.2.")
    m.table("Table 3.2. Interpretation of the weighted mean",
            ["Scale", "Description", "Range", "Interpretation"],
            [["5", "Highly Appropriate", "4.21–5.00", "Very High"], ["4", "Appropriate", "3.41–4.20", "High"],
             ["3", "Moderately Appropriate", "2.61–3.40", "Moderate"], ["2", "Slightly Appropriate", "1.81–2.60", "Low"],
             ["1", "Not Appropriate", "1.00–1.80", "Very Low"]], widths=[0.8, 2.2, 1.3, 1.4])
    m.h("3.9 Framework Development Process", 2)
    m.p("The construction management framework was built by organizing the project phases of planning, design, "
        "construction, and monitoring and maintenance, and by specifying, for each erosion risk class, the "
        "structure options and the requirements of each phase. The structure options follow the expert ranking "
        "(Table 4.6) and the hard, soft and hybrid approaches reviewed in Chapter II. The framework is intended as a "
        "decision-making guide and not as a final engineering design.")
    m.h("3.10 Reliability of the Instruments", 2)
    m.p("The reliability of the questionnaire was checked with Cronbach’s Alpha, the standard being 0.70 or higher "
        "(Taber, 2018). The coefficient is computed as")
    m.eq("α = [k / (k − 1)] × [1 − (Σσᵢ² / σₜ²)]")
    m.p("where k is the number of items, σᵢ² the variance of each item and σₜ² the variance of the total score. "
        "[[STUDENTS: report the Cronbach’s alpha of the pilot test and of the final data (the program in this project "
        "computes it as soon as the respondents’ answers are entered), or state that no pilot test was done.]] For the "
        "GIS work, reliability was supported by repeating the processing on a second shoreline set, by tests with "
        "artificial shorelines of known change, and by sensitivity runs (Section 3.4.6).", indent=False)
    m.h("3.11 Statistical Tools and Treatment", 2)
    m.p("**Descriptive statistics.** Shoreline change rates were summarized by mean, minimum, maximum and median, and "
        "shown in tables, maps and graphs.")
    m.p("**Frequency and percentage distribution.** The respondents were described by profession, years of experience "
        "and familiarity with shoreline protection structures. Frequency is the number of respondents in a category; "
        "percentage is that number divided by the total of 54, multiplied by 100.")
    m.p("**Weighted mean.** The ratings were averaged with")
    m.eq("x̄ = Σ(f · x) / N")
    m.p("where x̄ is the weighted mean, f the number of respondents giving a rating, x the rating (1 to 5) and N the "
        "total number of responses.", indent=False)
    m.p("**Test of the hypothesis.** To test whether the structures differ in perceived suitability, the Friedman test "
        "is used because the same respondents rated all structures; pairs of structures are compared afterward with "
        "the Wilcoxon signed-rank test with Holm’s correction, at α = 0.05.")
    m.h("3.12 Ethical Consideration", 2)
    carry(m, 986, 988)

    # =============================== CHAPTER IV
    m.h("CHAPTER IV\nRESULTS AND DISCUSSION", 1, page_break=True)
    m.h("4.1 Introduction", 2)
    m.p("This chapter presents the results in the order of the objectives: the shoreline change and erosion risk "
        "classification (Objective 1), the profile of the respondents and the evaluation of the structures "
        "(Objectives 2 and 3), and the proposed construction management framework (Objective 4). In the tables, a "
        "negative rate means erosion and a positive rate means accretion.")
    m.h("4.2 Multi-Temporal Shoreline Change", 2)
    m.p("Figure 4.1 shows the open-coast shorelines of 1990, 2000, 2010, 2020 and 2025. Along the straight coast from "
        "Bulala Sur to Bulala Norte the 1990 shoreline lies seaward of the later shorelines; the mean net movement from "
        "1990 to 2025 was −96 m at Bulala Sur and −117 m at Bulala Norte, compared with −49 m at Maura, −68 m at Dodan "
        "and −49 m at Paddaya. At the Linao spit and the river mouth the lines diverge and cross each other; transects "
        "there are not comparable and were left unclassified. River banks are drawn dashed and were not analyzed.")
    m.figure(MAPS / "Fig_4_1_v2_multitemporal_shorelines.png", "Figure 4.1. Multi-temporal shoreline change map of the "
             "selected coastal barangays in Aparri, Cagayan, 1990–2025", width=6.0)
    m.h("4.3 Computation of the Shoreline Change Rate", 2)
    m.p("A total of 415 transects spaced 50 m apart were generated and 373 were valid. The End Point Rate from 1990 to "
        "2025 of the valid transects ranged from −3.49 to +5.30 m/year (mean −1.57; median −1.46 m/year), and 94 % of "
        "the valid transects had a negative EPR, meaning landward movement. The largest erosion rate was 3.49 m/year; "
        "no valid transect reached the 5 m/year limit of the High class. Figure 4.3 shows the rate along the coast from "
        "the northwest end to Paddaya; the positive peak at Linao is the growing sand spit.")
    m.figure(MAPS / "Fig_4_3_epr_profile_along_coast.png", "Figure 4.3. Shoreline change rate along the open coast of the "
             "eight study barangays, 1990–2025", width=6.0)
    m.h("4.4 Barangay-Level EPR and Coastal Erosion Risk Results", 2)
    m.p("Table 4.1 gives the EPR and the risk-class areas of each barangay; Table 4.2 gives the same results in "
        "kilometers of shoreline, which is the primary measure, with the number of valid transects.")
    rows = [[r["Barangay"], f2(r["Mean EPR (m/year)"]), f2(r["Minimum EPR (m/year)"]), f2(r["Maximum EPR (m/year)"]),
             f"{r['Low Risk (ha)']:.2f}", f"{r['Medium Risk (ha)']:.2f}", f"{r['High Risk (ha)']:.2f}"]
            for _, r in t41.iterrows()]
    m.table("Table 4.1. Barangay-level EPR and coastal erosion risk results, 1990–2025",
            ["Barangay", "Mean EPR (m/yr)", "Min. EPR (m/yr)", "Max. EPR (m/yr)", "Low (ha)", "Medium (ha)", "High (ha)"],
            rows, widths=[1.2, 0.85, 0.85, 0.85, 0.7, 0.8, 0.7], size=9,
            note="Hectares = kilometers of classified shoreline × a 100 m coastal strip.")
    rows = [[r["Barangay"], f"{r['Low risk (km)']:.2f}", f"{r['Medium risk (km)']:.2f}", f"{r['High risk (km)']:.2f}",
             f"{r['Unclassified (km)']:.2f}", int(r["n valid"]), int(r["n flagged"])] for _, r in ext.iterrows()]
    m.table("Table 4.2. Kilometers of shoreline per risk class and number of transects",
            ["Barangay", "Low (km)", "Medium (km)", "High (km)", "Not classified (km)", "Valid transects",
             "Flagged transects"], rows, widths=[1.2, 0.7, 0.8, 0.7, 0.9, 0.8, 0.8], size=9,
            note="Flagged transects crossed a neighbor (river mouth and spit) and were not classified.")
    m.p("In order of mean EPR, the largest landward movement was recorded at Bulala Norte (−3.35 m/year), followed by "
        "Bulala Sur (−2.74) and Dodan (−1.93). Of the 18.8 km of classified shoreline, 13.8 km (73 %) fell in the Low "
        "class, 5.0 km (27 %) in the Medium class and none in the High class; 1.4 km near the river mouth could not be "
        "classified. Bulala Norte and Bulala Sur are entirely Medium; Linao is mixed (1.28 km Low, 1.31 km Medium); "
        "Dodan has 0.75 km and Maura 0.15 km of Medium shoreline; Paddaya, San Antonio and Punta are Low. Punta’s mean "
        "rate is positive (+0.19 m/year) but only 6 of its 19 transects were valid.")
    m.h("4.5 Coastal Erosion Risk Map", 2)
    m.p("Figure 4.2 shows the classified shoreline. Medium stretches lie along Bulala Sur and Bulala Norte, in parts "
        "of Linao, and in short stretches of Dodan and Maura; Low stretches occur elsewhere. Accreting segments (blue "
        "triangles) total 1.97 km, at Linao (1.26 km) and Punta (0.70 km). The High class does not occur on the open "
        "coast. Dotted segments have low confidence.")
    m.figure(MAPS / "Fig_4_2_v2_erosion_risk_map.png", "Figure 4.2. Coastal erosion risk map of the selected coastal "
             "barangays in Aparri, Cagayan", width=6.0)
    m.h("4.6 Discussion of the Coastal Erosion Risk Map", 2)
    m.p("The Medium class along Bulala Sur and Bulala Norte shows where the shoreline retreated fastest during the "
        "35 years. Since the movement is a long-term average, it does not show whether the retreat happened gradually "
        "or in a few storms. Linao’s result is mixed because the spit near the river mouth moves seaward while its "
        "neighboring stretch retreats.")
    m.p("**How reliable is the classification?** The class limits (2 and 5 m/year) lie close to the typical rates, so "
        "the map is more sensitive to the limits than to any technical choice. Changing the transect spacing, the "
        "smoothing, the baseline distance or the crossing rule changed the share of any class by at most 0.5 "
        "percentage points. Moving both class limits by ±0.5 m/year, however, changed the Medium share of the coast "
        "from 27 % to between 19 % and 48 % (Figure 4.4). With the one-pixel what-if band of ±1.21 m/year, the class of "
        "Maura, Bulala Norte, San Antonio, Paddaya, Punta and Bulala Sur did not change across the tests, while Dodan and "
        "Linao were not stable. A second, independent shoreline set gave the same class for 92 % of 253 transects "
        "(correlation of the rates r = 0.89; Figure 4.5).")
    m.figure(MAPS / "Fig_6_sensitivity_class_shares.png", "Figure 4.4. Share of the coast in each class under "
             "different technical choices and class limits", width=5.6)
    m.figure(MAPS / "Fig_6_source_agreement.png", "Figure 4.5. Agreement between the two independent shoreline sets",
             width=5.6)
    m.p("**Difference from the proposal-stage map.** The map shown at the proposal stage placed High risk along Bulala "
        "Sur and Bulala Norte. That map could not be reproduced from its source layers, and the rebuilt analysis gives "
        "Medium there (−2.74 and −3.35 m/year). The rebuilt result is the one reported in this thesis (Appendix D).")
    m.h("4.7 Barangays for First Field Inspection", 2)
    m.p("To help the local government decide where to look first, the barangays were ordered by two things only: how "
        "fast the shoreline retreated (mean erosion rate) and how long the Medium or High stretch is. Each was scaled "
        "from 0 to 1 and the two were averaged with equal weights (Table 4.3). This order is not a risk index, since "
        "buildings, roads and people were not included.")
    rows = [[int(r["rank"]), r["Barangay"], f"{r['mean_erosion_rate_m_yr']:.2f}", f"{r['km_medium_or_high']:.2f}",
             f"{r['priority_score']:.2f}"] for _, r in pri.iterrows()]
    m.table("Table 4.3. Order of barangays for first field inspection",
            ["Rank", "Barangay", "Mean erosion rate (m/yr)", "Medium or High shoreline (km)", "Score (0–1)"], rows,
            widths=[0.6, 1.4, 1.4, 1.6, 1.0], size=9.5)
    m.h("4.8 Profile of the Expert Respondents", 2)
    m.p("The respondents are described by profession and experience. Of the 54 experts, 21 (38.9 %) were civil "
        "engineers, 18 (33.3 %) DPWH engineers, 12 (22.2 %) coastal or environmental engineers, 2 (3.7 %) LGU technical "
        "personnel and 1 (1.9 %) a contractor (Table 4.4). The respondents therefore cover different fields relevant to "
        "shoreline protection and construction management.")
    m.table("Table 4.4. Professional background of the expert respondents", ["Professional background", "Frequency",
            "Percentage"], [["Civil Engineer", 21, "38.9%"], ["DPWH Engineer", 18, "33.3%"],
                            ["Coastal/Environmental Engineer", 12, "22.2%"], ["LGU Technical Personnel", 2, "3.7%"],
                            ["Contractor", 1, "1.9%"], ["Total", 54, "100%"]], widths=[3.0, 1.2, 1.2], bold_last=True)
    m.p("Regarding experience (Table 4.5), 29 respondents (53.7 %) had less than 5 years, 16 (29.6 %) had 5–10 years, "
        "6 (11.1 %) had 11–20 years and 3 (5.6 %) had more than 20 years. More than half of the respondents are "
        "therefore early-career professionals, which should be kept in mind when interpreting the ratings.")
    m.table("Table 4.5. Years of professional experience of the expert respondents", ["Years of experience", "Frequency",
            "Percentage"], [["Less than 5 years", 29, "53.7%"], ["5–10 years", 16, "29.6%"], ["11–20 years", 6, "11.1%"],
                            ["More than 20 years", 3, "5.6%"], ["Total", 54, "100%"]], widths=[3.0, 1.2, 1.2],
            bold_last=True)
    m.p("Table 4.6 shows experience and familiarity with shoreline protection structures. Forty-nine respondents (90.7 %) "
        "were familiar with the structures, 21 (38.9 %) had education or training in coastal engineering, and 15 "
        "(27.8 %) had worked on or supervised such a structure. Although direct work experience and formal training "
        "were limited, most respondents were familiar with the structures they rated.")
    m.table("Table 4.6. Experience, familiarity and training related to shoreline protection structures",
            ["Question", "Yes (n)", "Yes (%)", "No (n)", "No (%)"],
            [["Worked on or supervised a shoreline protection structure", 15, "27.8%", 39, "72.2%"],
             ["Familiar with the types of shoreline protection structures", 49, "90.7%", 5, "9.3%"],
             ["Received education or training in coastal engineering or shoreline protection", 21, "38.9%", 33,
              "61.1%"]], widths=[3.0, 0.7, 0.7, 0.7, 0.7], size=9.5)
    m.h("4.9 Evaluation of Shoreline Protection Structures", 2)
    m.p("The experts rated seawalls, revetments, riprap, breakwaters and mangrove rehabilitation on stability, "
        "effectiveness, cost, durability, maintenance and environmental impact. The weighted means are in the decision "
        "matrix of Table 4.7.")
    mat = [["Seawall", 4.5370, 4.5741, 4.2778, 4.2037, 4.2963, 4.2037, 4.3488, "Very High", 1],
           ["Revetment", 4.2593, 4.1296, 3.9074, 3.7593, 4.0000, 3.8704, 3.9877, "High", 3],
           ["Riprap", 3.8148, 3.5741, 3.5741, 3.3704, 3.8148, 3.6111, 3.6265, "High", 5],
           ["Breakwater", 3.8519, 3.8148, 3.6667, 3.4630, 3.7963, 3.6481, 3.7068, "High", 4],
           ["Mangrove Rehabilitation", 4.0185, 4.1667, 4.3519, 3.8889, 3.9074, 4.4815, 4.1358, "High", 2]]
    rows = [[r[0]] + [f"{v:.4f}" for v in r[1:8]] + [r[8], r[9]] for r in mat]
    m.table("Table 4.7. Decision matrix: weighted mean evaluation of shoreline protection structures",
            ["Structure", "Stab.", "Effect.", "Cost", "Dura.", "Maint.", "Env.", "Overall", "Interpretation", "Rank"],
            rows, widths=[1.2, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.55, 0.7, 0.4], size=8.5,
            note="Stab. = stability; Effect. = effectiveness; Dura. = durability; Maint. = maintenance requirements; "
                 "Env. = environmental impact. The overall mean is the average of the six criteria with equal weights. "
                 "(Breakwater × effectiveness is 206 ÷ 54 = 3.8148 and was printed as 3.8149 at the proposal stage.)")
    m.p("The seawall was the highest-rated structure (overall mean 4.3488, Very High), followed by mangrove "
        "rehabilitation (4.1358), revetment (3.9877), breakwater (3.7068) and riprap (3.6265), all High. The seawall "
        "received the highest ratings for stability (4.5370), effectiveness (4.5741), durability (4.2037) and "
        "maintenance (4.2963), while mangrove rehabilitation received the highest ratings for environmental impact "
        "(4.4815) and cost (4.3519). Each structure therefore has different perceived strengths.")
    m.p("**Does the order depend on the weights?** The overall mean gives the six criteria equal weight. Re-ranking "
        "with double weight on cost, on environmental impact, or on stability and durability left the order unchanged "
        "(seawall, mangrove rehabilitation, revetment, breakwater, riprap). Looking only at engineering criteria, the "
        "revetment moved ahead of mangrove rehabilitation, and with cost and environment only, mangrove rehabilitation "
        "ranked first. Over 20,000 random weightings the seawall ranked first in about 96 % of cases. The statement "
        "“seawall first, riprap last” is therefore firm, while the order of mangrove rehabilitation and revetment "
        "depends on how much weight engineering performance receives. All averages lie between 3.37 and 4.57, so the "
        "respondents rated every structure fairly high.")
    m.h("4.10 Test of the Hypothesis", 2)
    m.p("The weighted means differ, from 4.35 for the seawall to 3.63 for riprap. Whether the difference is "
        "statistically significant is decided by the Friedman test on the individual answers. "
        "[[STUDENTS: enter the respondents’ answers in the survey file and run the program; then write χ², df, p-value "
        "and the decision at α = 0.05 here. The answers of the 54 respondents were not in the project files, so this test "
        "could not be computed.]]")
    m.h("4.11 Proposed Construction Management Framework", 2)
    m.p("The framework turns the results into steps (Figure 4.6). It first uses the erosion risk class of a shoreline "
        "stretch (Objective 1), then chooses structure options from the expert ranking and the approaches reviewed in "
        "Chapter II (Objectives 2 and 3), and finally sets requirements for the four management phases (Objective 4). "
        "Because the respondents rated each structure once for the whole area, the matching of structures to a risk "
        "class in Table 4.8 is the researchers’ proposal, based on the ratings and the literature. "
        "[[ADVISER REVIEW: confirm the contents of Table 4.8.]]")
    m.figure(OUT / "fig_framework.png", "Figure 4.6. Proposed construction management framework", width=5.8)
    fr = [
        ["Low\n(< 2 m/yr)\n13.8 km: Maura, Paddaya, San Antonio, Punta; parts of Dodan and Linao",
         "Mangrove rehabilitation and other soft measures (rank 2; best environmental and cost ratings); maintain "
         "existing structures. No new hard structure unless a site-specific hazard is found.",
         "Include the stretch in the coastal inventory; confirm the class with a field visit.",
         "Light, low-cost nature-based design; check that planted areas can survive local waves.",
         "Community-based planting and protection of existing mangroves; supervised by LGU/engineer.",
         "Re-measure the shoreline with the same method; inspect after typhoons."],
        ["Medium\n(2–5 m/yr)\n5.0 km: Bulala Sur and Norte; parts of Linao, Dodan, Maura",
         "Seawall or revetment (ranks 1 and 3; highest stability and effectiveness), combined with mangrove or "
         "other soft measures where site conditions allow (hybrid approach).",
         "First priority for field inspection (Table 4.3); gather topography, soil, wave and cost information before "
         "choosing a structure.",
         "Site-specific design by a licensed engineer; include protection against scouring at the toe; check the "
         "environmental effect.",
         "Staged construction with quality control and supervision; schedule work outside the typhoon season.",
         "Inspect the structure after each major storm; repeat the shoreline survey regularly and keep maintenance "
         "records."],
        ["High\n(> 5 m/yr)\nnot found on the open coast, 1990–2025",
         "Contingency only: seawall or revetment, possibly with a breakwater, supported by a detailed coastal study.",
         "Immediate hazard assessment of people and property at risk.",
         "Detailed engineering study (waves, currents, sediments) before any design.",
         "Emergency or phased works with strict supervision.",
         "Frequent monitoring until the shoreline stabilizes."],
    ]
    m.table("Table 4.8. Proposed construction management framework by erosion risk class",
            ["Risk class", "Structure options", "Planning", "Design", "Construction", "Monitoring and maintenance"],
            fr, widths=[1.05, 1.25, 0.95, 0.95, 0.95, 0.95], size=8, align_num=False,
            note="Proposal of the researchers, derived from Table 4.7 and Chapter II. It is a decision guide and does "
                 "not replace a site-specific engineering design.")
    b = ext[ext.Barangay == "Bulala Norte"].iloc[0]
    m.p("**Worked example.** Bulala Norte has a mean EPR of −3.35 m/year and 1.35 km of Medium shoreline, with the "
        "highest field-inspection priority (Table 4.3). Under the framework, the planning phase starts with a field "
        "inspection and the collection of topographic, soil and wave data; the design phase considers a seawall or "
        "revetment (the highest-rated structures) combined with soft measures, with toe protection against scouring; "
        "construction is staged and supervised outside the typhoon season; and monitoring repeats the shoreline survey "
        "and inspects the structure after each major storm.")
    m.h("4.12 Limits of the Results", 2)
    m.p("The results should be read with these limits: (1) the classes are based on the erosion rate only; exposure "
        "and vulnerability were not assessed; (2) the 30 m image pixel is coarse compared with the 2 m/year class limit, "
        "and positional errors, image dates and tide levels were not available; (3) the shorelines at the river mouth "
        "were not classified; (4) the survey did not ask for ratings by risk level, and more than half of the "
        "respondents had under five years of experience; and (5) the results were not verified in the field.")

    # =============================== CHAPTER V
    m.h("CHAPTER V\nSUMMARY, CONCLUSION AND RECOMMENDATIONS", 1, page_break=True)
    m.h("5.1 Summary", 2)
    m.p("The study aimed to develop a construction management framework for shoreline protection structures in Aparri, "
        "Cagayan, based on coastal erosion risk levels. Shoreline positions of 1990, 2000, 2010, 2020 and 2025 for the "
        "open coast of eight barangays were analyzed with 415 transects spaced 50 m apart (373 valid) using the End "
        "Point Rate, and the coast was classified as Low (below 2 m/year), Medium (2–5 m/year) or High (above 5 "
        "m/year). Fifty-four experts rated five shoreline protection structures on six criteria with a five-point "
        "scale, and the ratings were analyzed by weighted mean. The framework was assembled from the classification, the "
        "ranking and the literature.")
    m.h("5.2 Conclusion", 2)
    m.p("**Objective 1.** Of the 18.8 km of classified open coast, 13.8 km (73 %) were Low, 5.0 km (27 %) Medium and "
        "none High. The highest mean erosion rates were in Bulala Norte (−3.35 m/year) and Bulala Sur (−2.74 m/year), "
        "both entirely Medium, while Maura, Paddaya, San Antonio and Punta were mainly Low. Dodan and Linao lie near the "
        "Low–Medium boundary and their class is less certain. These classes describe the erosion rate only.")
    m.p("**Objective 2.** The experts considered the seawall the most suitable structure (overall mean 4.35, Very "
        "High), followed by mangrove rehabilitation (4.14), revetment (3.99), breakwater (3.71) and riprap (3.63). The "
        "first and last places held under all tested weightings, while the order of mangrove rehabilitation and "
        "revetment depended on the weight given to engineering criteria.")
    m.p("**Objective 3.** The ranking is for the study area as a whole. The matching of structures to risk levels — "
        "hybrid or hard structures for Medium stretches and soft, nature-based measures for Low stretches — rests on the "
        "ratings and on the literature, and was not rated by the respondents for each risk level.")
    m.p("**Objective 4.** The proposed framework links the erosion risk class to structure options and to the "
        "requirements of the planning, design, construction, and monitoring and maintenance phases, with stronger "
        "requirements for Medium than for Low stretches (Table 4.8). Hypothesis: "
        "[[STUDENTS: state the result of the Friedman test after it is computed — see Section 4.10.]]")
    m.h("5.3 Recommendations", 2)
    m.p("**To the Local Government Unit and MDRRMO:** give first priority to field inspection of the Medium stretches, "
        "beginning with Bulala Norte and Bulala Sur, and start a regular shoreline monitoring program (for example "
        "repeated GPS surveys of the shoreline at the same tide and season).", indent=False)
    m.p("**To DPWH and practicing engineers:** use the framework as a guide together with a site-specific coastal "
        "engineering design, keeping in mind that the classes describe the erosion rate only.", indent=False)
    m.p("**To future researchers:** (a) record the date and tide of each image and use seasonal composites; (b) measure "
        "the positional error of the shorelines; (c) add exposure of buildings and roads and the vulnerability of the "
        "population; (d) ask the experts to rate the structures separately for Low, Medium and High erosion; (e) verify "
        "the results in the field (form in Appendix E); and (f) study the Cagayan River mouth with a method suited to "
        "river mouths.", indent=False)
    m.p("**To the department:** keep the computer files, settings and logs of the GIS analysis with the thesis so that "
        "the results can be reproduced.", indent=False)
    m.h("5.4 Limitations", 2)
    m.p("The study is limited to the erosion rate; to 30 m imagery without measured error, dates or tide; to the open "
        "coast outside the river mouth; to a survey not stratified by risk level and with mostly early-career "
        "respondents; and to results not yet verified in the field.")

    # =============================== REFERENCES
    m.h("REFERENCES", 1, page_break=True)
    m.p("[[STUDENTS: the following in-text citations in Chapters I–II have no matching entry in this list. Add the "
        "entry or remove the citation: Dong et al. (2024); Rocha et al. (2023); Rivera & Dela Vega (2025); Taslin et "
        "al. (2024); Nguyen et al. (2025); Ballad et al. (2021); DPWH (2021); Angnuureng (2025); Toledo et al. (2025); "
        "Zhou et al. (2023); Thirumurthy et al. (2022); OECD (2026); Nature Communications (2022); Elsevier’s "
        "Anthropocene (2023); Ouyang & Wang (2024).]]", indent=False, spacing=1.1, size=10)
    refs = REFERENCES
    for r in sorted(refs, key=lambda s: s.lower()):
        par = m.p(r, indent=False, spacing=1.0, after=8, align="l")
        par.paragraph_format.left_indent = docx_inch(0.5)
        par.paragraph_format.first_line_indent = docx_inch(-0.5)

    # =============================== APPENDICES
    m.h("APPENDICES", 1, page_break=True)
    m.h("Appendix A. Work Breakdown Schedule", 2)
    m.copy_table(src.tables[12])
    m.p("")
    m.h("Appendix B. Research Questionnaire", 2, page_break=True)
    from docx.oxml.ns import qn as _qn
    from docx.table import Table as _T
    from docx.text.paragraph import Paragraph as _P
    start = src.paragraphs[1574]._p
    on = False
    for el in src.element.body:
        if el is start:
            on = True
            continue
        if not on:
            continue
        if el.tag == _qn("w:p"):
            t = re.sub(r"\s+", " ", _P(el, src).text).strip()
            if not t or t.startswith(("CAGAYAN STATE UNIVERSITY CARIG", "COLLEGE OF ENGINEERING", "AND ARCHITECTURE")):
                continue
            if t.isupper() or t in ("Seawalls", "Revetments", "Riprap", "Breakwater", "Mangrove Rehabilitation"):
                m.p("**" + t + "**", indent=False, align="c", spacing=1.15, after=4, keep_next=True)
            else:
                m.p(t, indent=False, spacing=1.15, after=4)
        elif el.tag == _qn("w:tbl"):
            tb = _T(el, src)
            if len(tb.rows) < 2:
                continue
            header = [c.text.strip().replace("\n", " ") for c in tb.rows[0].cells]
            rows_ = []
            for r in tb.rows[1:]:
                seen, vals = None, []
                for c in r.cells:
                    if c._tc is not seen:
                        vals.append(c.text.strip().replace("\n", " "))
                    seen = c._tc
                rows_.append(vals + [""] * (len(header) - len(vals)))
            m.table(None, header, rows_, size=9, align_num=False)
    m.h("Appendix C. GIS Settings Used", 2, page_break=True)
    m.table(None, ["Item", "Value"], [
        ["Coordinate system for measuring", "WGS 84 / UTM zone 51N (EPSG:32651); source data in EPSG:4326"],
        ["Years analyzed", "1990, 2000, 2010, 2020, 2025; EPR end points 1990 and 2025 (T = 35 years)"],
        ["Baseline", "1990 open-coast shoreline smoothed over 200 m, shifted landward 150 m beyond the farthest landward year"],
        ["Transects", "Every 50 m, 600 m seaward and 600 m landward; nearest crossing kept"],
        ["Cleaning of the lines", "Join ends < 5 m; remove loops < 50 m; remove stretches digitized twice in one year"],
        ["Open coast / river banks", "350 m from the outer outline of all shorelines"],
        ["Risk classes", "Low < 2; Medium 2–5 (limits included); High > 5 m/year"],
        ["Barangay assignment", "Nearest barangay within 500 m; areas = kilometers × 100 m strip"],
        ["Positional uncertainty", "Not measured; one-pixel what-if of 30 m per date (±1.21 m/year)"],
        ["Software", "QGIS, Python (GeoPandas, Shapely); all steps scripted with a log"],
    ], widths=[1.9, 4.0], size=9.5, align_num=False)
    m.h("Appendix D. Data Audit Summary", 2)
    m.p("Before the analysis, the supplied files were audited. The shoreline lines were found as 19 loose pieces; one "
        "feature had an unreadable year and was not used; 18.3 km of the 2010 shoreline had been digitized twice. The "
        "risk map of the proposal stage consisted of 117 cells on the 30 m pixel grid and 7 hand-drawn polygons, and "
        "it could not be reproduced from the shoreline lines with the rate limits of Table 3.1; the Medium and High "
        "labels of that map were carried by the seven hand-drawn polygons. For this reason the risk map was rebuilt "
        "from the shoreline lines, and the rebuilt version is the one reported in Chapter IV. The full audit is "
        "kept in the project files (Technical Annex).", indent=False)
    m.h("Appendix E. Field Verification", 2)
    m.p("A field verification form and a list of suggested check points (the Medium stretches first) are provided "
        "with the project files. [[STUDENTS: attach the completed forms if the field verification was done.]]",
        indent=False)
    m.h("Appendix F. Respondents’ Data", 2)
    m.p("[[STUDENTS: attach the anonymized answers of the 54 respondents and the Cronbach’s alpha computation.]]",
        indent=False)
    m.h("Appendix G. Permission Letters and Consent", 2)
    m.p("[[STUDENTS: attach the endorsement and permission letters and the informed-consent form.]]", indent=False)

    # ---------------------------------------------------------------- tables of contents (inserted after the heading)
    heads = [(l, t) for l, t in m.headings if l <= 2]
    tocs = [(1 if l == 1 else 2, t) for l, t in heads]
    cap_t = [(1, t) for k, t in m.captions if k == "Table"]
    cap_f = [(1, t) for k, t in m.captions if k == "Figure"]
    body = m.doc.element.body
    anchor = body[toc_placeholder_idx]          # the "TABLE OF CONTENTS" heading
    from docx.text.paragraph import Paragraph
    tail = []

    def emit(title, instr, entries):
        h = m.doc.add_heading(level=1)
        h.add_run(title)
        h.paragraph_format.page_break_before = True
        m.toc(instr, entries)
        tail.extend([h._p] + [p._p for p in m.doc.paragraphs[-len(entries):]])

    n0 = len(body)
    emit_start = len(body)
    # build the three lists at the end of the body, then move them behind the anchor
    m.toc('TOC \\o "1-2" \\h \\z \\u', tocs)
    toc_els = list(body)[emit_start:-1]
    emit("LIST OF TABLES", 'TOC \\h \\z \\t "TableCaption,1"', cap_t)
    emit("LIST OF FIGURES", 'TOC \\h \\z \\t "FigureCaption,1"', cap_f)
    all_new = list(body)[emit_start:-1]
    ref = anchor
    for el in all_new:
        ref.addnext(el)
        ref = el
    m.update_fields_on_open()
    path = OUT / "Thesis_Manuscript_FINAL_DRAFT.docx"
    m.doc.core_properties.title = TITLE
    m.doc.core_properties.author = "Bruno, Cabauatan, Mora, Ubando"
    m.doc.save(path)
    return path


def docx_inch(x):
    from docx.shared import Inches
    return Inches(x)


REFERENCES = [
    "Amos, D., & Akib, S. (2023). A review of coastal protection using artificial and natural countermeasures—Mangrove vegetation and polymers. Eng, 4(1), 941–953.",
    "Bartolome, I. S., & Griño Jr, A. (2026). Reliability analysis of Dampalit Mega Dike using Monte Carlo simulation against sliding failure. GEOMATE Journal, 30(137), 43–51.",
    "Calapini, W. D., Tan, F. J., Monjardin, C. E. F., & Gacu, J. G. (2025). Geospatial analysis of flood hazard using GIS-based hydrologic–hydraulic modeling: A case of the Cagayan River Basin, Philippines. Geomatics, 5(4), 64. https://doi.org/10.3390/geomatics5040064",
    "Cao, C., Zhu, K., Cai, F., Qi, H., Liu, J., Lei, G., ... & Su, Y. (2022). Vulnerability evolution of coastal erosion in the Pearl River Estuary Great Bay Area due to the influence of human activities in the past forty years. Frontiers in Marine Science, 9, 847655.",
    "Cavalli, R. M. (2024). Remote data for mapping and monitoring coastal phenomena and parameters: A systematic review. Remote Sensing, 16(3), 446.",
    "Dodgson, J. S., Spackman, M., Pearman, A., & Phillips, L. D. (2009). Multi-criteria analysis: A manual. Department for Communities and Local Government, UK.",
    "Elemin, S. A., Fekhaoui, M., Cheikh, M. A. S., Pizzigalli, C., Sidoumou, Z., & Avoulwatt, M. (2026). Port-induced shoreline change and ecological implications in an arid coastal system: Evidence from N’Diago Port, Mauritania. Ecological Engineering & Environmental Technology, 27(5), 359–375.",
    "Felipe, A. J. B., Alejo, L. A., Padre, R. J., & Bareng, J. L. R. (2026). Past and future river bank trend assessment of lower Cagayan River, Philippines. Environment, Development and Sustainability, 28(2), 3363–3398. https://link.springer.com/article/10.1007/s10668-024-05113-3",
    "Gao, W., Du, J., Gao, S., Xu, Y., Li, B., Wei, X., ... & Li, P. (2023). Shoreline change due to global climate change and human activity at the Shandong Peninsula from 2007 to 2020. Frontiers in Marine Science, 9, 1123067. https://doi.org/10.3389/fmars.2022.1123067",
    "Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., Thau, D., & Moore, R. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote Sensing of Environment, 202, 18–27. [[VERIFY CITATION]]",
    "Gu, J., Wei, X., Han, Y., Zeng, J., Hu, M., & Gong, Z. (2025). A conflict-coordination framework for constructing living shorelines: A case study of ecological seawalls. Sustainability, 17(22), 10050. https://www.mdpi.com/2071-1050/17/22/10050",
    "Igbokwe, J. I., Obasohan, J. N., & Igbokwe, E. C. (2024). GIS-based analytical hierarchy process modelling and mapping of erosion vulnerability in the coastal areas of Rivers State, Nigeria. Asian Journal of Geographical Research, 7(2), 11–25.",
    "Jordan, P., & Fröhle, P. (2022). Bridging the gap between coastal engineering and nature conservation? A review of coastal ecosystems as nature-based solutions for coastal protection. Journal of Coastal Conservation, 26(2), 4. https://link.springer.com/article/10.1007/s11852-021-00848-x",
    "Li, C., & Fang, S. (2026). Coastal land use transitions and their cascading impacts on ecosystem resilience: A global bibliometric review. Regional Ecology and Management, 1(1), 7.",
    "Luijendijk, A., Hagenaars, G., Ranasinghe, R., Baart, F., Donchyts, G., & Aarninkhof, S. (2018). The state of the world’s beaches. Scientific Reports, 8(1), 6641.",
    "McFeeters, S. K. (1996). The use of the Normalized Difference Water Index (NDWI) in the delineation of open water features. International Journal of Remote Sensing, 17(7), 1425–1432. [[VERIFY CITATION]]",
    "Narafu, T., Shimizu, T., Sanada, Y., Tamura, Y., Mita, N., Takahashi, S., ... & Itsuki, A. (2015). Lessons learnt from damage to buildings by Bohol earthquake and typhoon Yolanda 2013 in the Philippines. Bulletin of International Institute of Seismology and Earthquake Engineering, 49, 39–61.",
    "Nerves, A., Rivera, F. D., Blanco, A., Tirol, Y., & Nadaoka, K. (2024). Shoreline change analysis in New Washington, Aklan using Digital Shoreline Analysis System (DSAS). ISPRS Annals of the Photogrammetry, Remote Sensing and Spatial Information Sciences, X-5-2024, 111–117. https://doi.org/10.5194/isprs-annals-X-5-2024-111-2024",
    "Nieuwenhout, C., & Andreasson, L. M. (2023). The legal framework for artificial energy islands in the northern seas. The International Journal of Marine and Coastal Law, 39(1), 39–72. https://doi.org/10.1163/15718085-bja10151",
    "Osondu, I., Imoni, O., Chukwuemeka, P., Amos, M. D., Ajibade, D. I., Mene-Ejegi, O. O., ... & Akajiaku, C. U. (2025). Machine learning-based shoreline change prediction and erosion analysis: A case study of Ogu/Bolo, Nigeria. Discover Civil Engineering, 2(1), 230.",
    "Perricone, V., Mutalipassi, M., Mele, A., Buono, M., Vicinanza, D., & Contestabile, P. (2023). Nature-based and bioinspired solutions for coastal protection: An overview among key ecosystems and a promising pathway for new functional and sustainable designs. ICES Journal of Marine Science, 80(5), 1218–1239.",
    "Sauvé, P., Bernatchez, P., & Glaus, M. (2022). Multicriteria decision analysis to assist in the selection of coastal defence measures: Involving coastal managers and professionals in the identification and weighting of criteria. Frontiers in Marine Science, 9, 845348.",
    "Senatilleke, U., Herath, R., Fonseka, P. U., Kantamaneni, K., & Rathnayake, U. (2026). Assessment of shoreline change in Southeast Ireland using geospatial techniques. Sustainability, 18(7), 3280. https://www.mdpi.com/2071-1050/18/7/3280",
    "Singhvi, A., Luijendijk, A. P., & van Oudenhoven, A. P. (2022). The grey–green spectrum: A review of coastal protection interventions. [[VERIFY CITATION: journal name, volume and pages are missing in the proposal]]",
    "Sun, W., Chen, C., Liu, W., Yang, G., Meng, X., Wang, L., & Ren, K. (2023). Coastline extraction using remote sensing: A review. GIScience & Remote Sensing, 60(1), 2243671.",
    "Taber, K. S. (2018). The use of Cronbach’s alpha when developing and reporting research instruments in science education. Research in Science Education, 48(6), 1273–1296. https://link.springer.com/article/10.1007/s11165-016-9602-2",
    "Thieler, E. R., Himmelstoss, E. A., Zichichi, J. L., & Ergul, A. (2009). The Digital Shoreline Analysis System (DSAS) version 4.0 — an ArcGIS extension for calculating shoreline change (Open-File Report 2008-1278). U.S. Geological Survey. https://pubs.usgs.gov/publication/ofr20081278",
    "Tikekar, O., Saha, S., Deshpande, G., & Sengupta, S. (2026). Integrated DSAS–InVEST modeling for quantitative assessment of shoreline dynamics and coastal exposure along the Raigad coast, India. Environmental Systems Research.",
    "Tora, D., Fontolan, G., Fracaros, S., & Bezzi, A. (2026). Coastal vulnerability and risk analysis along the littoral of Togo. Coasts, 6(2), 18. https://www.mdpi.com/2673-964X/6/2/18",
    "Tsiakos, C. A. D., & Chalkias, C. (2023). Use of machine learning and remote sensing techniques for shoreline monitoring: A review of recent literature. Applied Sciences, 13(5), 3268.",
    "Tzepkenlis, A., Grammalidis, N., Kontopoulos, C., Charalampopoulou, V., Kitsiou, D., Pataki, Z., ... & Nitis, T. (2022). An integrated monitoring system for coastal and riparian areas based on remote sensing and machine learning. Journal of Marine Science and Engineering, 10(9), 1322.",
    "U.S. Geological Survey. (2023). Coastal Change Hazards Program. https://www.usgs.gov/programs/cmhrp",
    "Wilson, E. T., & Liberia, T. N. A. E. P. A. (2019). Coastal zone’s technology needs assessment for climate change adaptation. https://ekmsliberia.info/wp-content/uploads/2020/12/tna-report-coastal-zone-liberia.pdf",
    "Woodroffe, C. D., Evelpidou, N., Delgado-Fernandez, I., Green, D., Sengupta, D., Karkani, A., & Ciavola, P. (2025). Coastline changes: A reconsideration of the prevalence of recession on sandy shorelines. Cambridge Prisms: Coastal Futures, 3, e18.",
    "Zhang, Y., Ouyang, Z., Xu, C., Wu, T., & Lu, F. (2024). A multi-hazard framework for coastal vulnerability assessment and climate-change adaptation planning. Environmental and Sustainability Indicators, 21, 100327.",
    "Zhao, K., Wang, Y., & Liu, P. L. F. (2024). A guide for selecting periodic water wave theories — Le Méhauté (1976)’s graph revisited. Coastal Engineering, 188, 104432. https://doi.org/10.1016/j.coastaleng.2023.104432",
]



def build_guide():
    """One-page plain-language guide for the students (what the file is, what to fill in, QGIS answer)."""
    m = Manuscript()
    m.first_section(header=False)
    m.h("START HERE — Plain-Language Guide", 1)
    m.p("**What you have.** Thesis_Manuscript_FINAL_DRAFT.docx is your complete thesis: cover, approval sheet, "
        "abstract, contents, Chapters I–V, references and appendices, in the department format. Chapters I–II, the "
        "questionnaire and the survey tables are your own text. Chapters III–V were rewritten with the finished "
        "results (maps, tables, ranking, framework).", indent=False)
    m.p("**What the yellow brackets mean.** Every yellow [bracket] is something only you can supply, because it is not "
        "in the files and nothing was invented: the defense date, the acknowledgment, who prepared the shoreline lines "
        "and from which images, the number invited and the response rate, the reliability (Cronbach’s alpha), the "
        "result of the significance test, field visits (if any), the attachments of the appendices, and a few "
        "references to double-check. Fill in or delete each one before printing.", indent=False)
    m.p("**Three things to do first.** (1) Open the file in Word and, when asked, click **Yes** to update the fields; "
        "this fills in page numbers in the Table of Contents, List of Tables and List of Figures. (2) Show Chapter IV, "
        "Section 4.11 (Table 4.8, the framework) to your adviser: it is a proposal written for you and needs approval. "
        "(3) Tell your adviser that the risk map was rebuilt: the old proposal map showed High risk at Bulala, but the "
        "recomputed result is Medium (explained in Section 4.6).", indent=False)
    m.p("**Explanation of the main terms.**", indent=False, keep_next=True)
    m.lst(["**Shoreline change rate (EPR):** how many meters per year the shoreline moved between 1990 and 2025. "
           "Minus means the sea took land.",
           "**Low / Medium / High:** under 2, 2 to 5, and over 5 meters per year of land lost.",
           "**Transect:** an imaginary straight line across the beach, every 50 m, used as a measuring tape.",
           "**GIS:** mapping software; it measured and drew everything automatically from your shoreline files.",
           "**Weighted mean:** the average of the experts’ ratings; the higher, the better rated."])
    m.p("**Do I need to install QGIS? Is it free?** QGIS is a free, open-source mapping program (download from "
        "qgis.org for Windows, Mac or Linux). You do **not** need it to finish or defend the thesis. The manuscript "
        "already contains the maps and tables. To look at the maps yourself you only need a web browser: open "
        "outputs/web/index.html. QGIS is optional, only if you want to open the project file "
        "outputs/layers/Aparri_v2.qgz and make your own maps. That project file could not be opened and tested in QGIS "
        "in the environment where it was made; if it does not open properly, use the pictures and the web map.",
        indent=False)
    m.p("**Where the maps are.** Pictures: outputs/maps/. Excel/Word tables: outputs/tables/. Interactive map: "
        "outputs/web/index.html. Defense slides: outputs/defense/. Questions the panel may ask, with answers: "
        "docs/04_defense_qa.md.", indent=False)
    path = OUT / "START_HERE_Guide.docx"
    m.doc.save(path)
    return path


if __name__ == "__main__":
    print(build())
    print(build_guide())
