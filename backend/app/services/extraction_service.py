from __future__ import annotations
import re
import json
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
import networkx as nx
import matplotlib.pyplot as plt
from babel.numbers import parse_decimal
import dateparser

from backend.app.schemas.extraction import (
    ClauseSegment,
    ExtractionResult,
    MoneyAmount,
    Percentage,
    DateFound,
    Thresholds,
    EntityGraph,
    GraphNode,
    GraphEdge,
    GraphQueryResult,
)
from backend.app.core.path_resolver import index_dir

CURR_MAP = {
    "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR",
}
CURR_CODE = r"(?:USD|EUR|GBP|JPY|INR|CAD|AUD|CHF|CNY|HKD|SGD|SEK|NOK|DKK)"
AMOUNT_PAT = re.compile(
    rf"(?P<cur>\$|€|£|¥|₹|{CURR_CODE})\s?(?P<val>\d[\d,\.]*)(\s?(?:million|billion|thousand|m|bn|k))?",
    flags=re.IGNORECASE
)
PCT_PAT = re.compile(r"(?P<val>\d{1,3}(?:\.\d+)?)\s?%")
DATE_PAT = re.compile(
    r"(?:(?:\d{1,2}[/-]){2}\d{2,4})|(?:\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4}\b)|(?:\b\d{4}-\d{2}-\d{2}\b)",
    re.IGNORECASE
)

# thresholds (caps/baskets/de minimis/aggregate)
CAP_PAT       = re.compile(r"(?i)\bcap(?:ped)?(?: at| of)?[: ]")
BASKET_PAT    = re.compile(r"(?i)\bbasket(?: amount)?[: ]")
DEMIN_PAT     = re.compile(r"(?i)\bde minimis\b")
AGG_PAT       = re.compile(r"(?i)\baggregate(?:d)?(?: amount)?[: ]")

PARTY_LINE_PAT = re.compile(
    r'(?i)\bbetween\b\s+(?P<p1>[A-Z][A-Za-z0-9&,\.\- ]{2,})\s+\("?(?:Company|Licensor|Lender|Seller|Party A|Party)"?\)\s+and\s+(?P<p2>[A-Z][A-Za-z0-9&,\.\- ]{2,})',
)
ROLE_PAT = re.compile(r'(?i)\b(Licensor|Licensee|Lender|Borrower|Supplier|Customer)\b')
AUTO_RENEW_PAT = re.compile(r"(?i)\bauto(?:matic)?\s*renew(?:al|s)?\b")
SERVICE_CREDIT_PAT = re.compile(r"(?i)\bservice credits?\b")
NOTICE_PAT = re.compile(r"(?i)\bnotice(?:s)?\b")
CURE_PAT = re.compile(r"(?i)\bcure(?:d|s|ing)?\b(?: within)?\s*(?P<days>\d{1,3})\s*day")
TERMINATION_PAT = re.compile(r"(?i)\bterminat(?:e|ion)\b")
RENEWAL_WINDOW_PAT = re.compile(r"(?i)\b(\d{1,3})\s*day(?:s)?\b.*\b(prior to|before)\b.*\brenew", re.DOTALL)

SCALE_WORDS = {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000, "k": 1_000, "m": 1_000_000, "bn": 1_000_000_000}

def _normalize_amount(m: re.Match) -> MoneyAmount:
    raw = m.group(0)
    cur = m.group("cur")
    val = m.group("val").replace(",", "")
    mult = 1.0
    if m.group(3):
        key = m.group(3).strip().lower()
        mult = SCALE_WORDS.get(key, 1.0)
    try:
        base = float(parse_decimal(val))
    except Exception:
        try:
            base = float(val)
        except Exception:
            base = None
    if cur in CURR_MAP:
        code = CURR_MAP[cur]
    else:
        code = cur.upper()
    return MoneyAmount(raw=raw, value=(base * mult if base is not None else None), currency=code,
                       normalized=(f"{code} {base * mult:.2f}" if base is not None else None))

def _normalize_pct(m: re.Match) -> Percentage:
    raw = m.group(0)
    try:
        val = float(m.group("val"))
    except Exception:
        val = None
    return Percentage(raw=raw, value=val)

def _normalize_date(txt: str) -> DateFound:
    iso = None
    try:
        dt = dateparser.parse(txt)
        if dt:
            iso = dt.date().isoformat()
    except Exception:
        pass
    return DateFound(raw=txt, iso=iso)

def _scan_thresholds(text: str) -> Thresholds:
    # naive approach: text vicinity of each term -> pick first amount near it
    def first_amount_after(pattern: re.Pattern) -> List[MoneyAmount]:
        out: List[MoneyAmount] = []
        for m in pattern.finditer(text):
            tail = text[m.end(): m.end() + 120]
            am = AMOUNT_PAT.search(tail)
            if am:
                out.append(_normalize_amount(am))
        return out

    return Thresholds(
        caps=first_amount_after(CAP_PAT),
        baskets=first_amount_after(BASKET_PAT),
        de_minimis=first_amount_after(DEMIN_PAT),
        aggregates=first_amount_after(AGG_PAT),
    )

class ExtractionService:
    def __init__(self):
        self._graph: Optional[nx.MultiDiGraph] = None
        self._graph_render_path: Optional[str] = None

    def extract(self, text: str, clauses: List[ClauseSegment]) -> ExtractionResult:
        amounts = [_normalize_amount(m) for m in AMOUNT_PAT.finditer(text)]
        pcts = [_normalize_pct(m) for m in PCT_PAT.finditer(text)]
        dates = [_normalize_date(m.group(0)) for m in DATE_PAT.finditer(text)]
        thresholds = _scan_thresholds(text)
        # stub FX snapshot date: "today"
        fx_date = datetime.utcnow().date().isoformat()
        return ExtractionResult(
            dates=dates,
            amounts=amounts,
            percentages=pcts,
            thresholds=thresholds,
            fx_snapshot_date=fx_date,
        )

    # -------- Graph building --------

    def _add_node(self, G: nx.MultiDiGraph, node_id: str, label: str, ntype: str, **attrs):
        if not G.has_node(node_id):
            G.add_node(node_id, label=label, type=ntype, **attrs)

    def _add_edge(self, G: nx.MultiDiGraph, u: str, v: str, label: str, **attrs):
        G.add_edge(u, v, label=label, **attrs)

    def build_graph(self, text: str, clauses: List[ClauseSegment]) -> EntityGraph:
        G = nx.MultiDiGraph()
        # Parties (very heuristic)
        m = PARTY_LINE_PAT.search(text)
        if m:
            p1 = m.group("p1").strip().strip(",.")
            p2 = m.group("p2").strip().strip(",.")
            self._add_node(G, "party:1", p1, "party")
            self._add_node(G, "party:2", p2, "party")
        else:
            # fallback roles
            parties = set()
            for r in ROLE_PAT.finditer(text):
                parties.add(r.group(1).title())
            for i, p in enumerate(sorted(parties), start=1):
                self._add_node(G, f"party:{i}", p, "party")

        # Clause nodes & edges from parties based on role mentions
        for cl in clauses or []:
            ctext = text[cl.start:cl.end]
            cid = cl.id
            title = cl.title or "Clause"
            auto_renew = bool(AUTO_RENEW_PAT.search(ctext))
            service_credit = SERVICE_CREDIT_PAT.search(ctext) is not None
            notice = NOTICE_PAT.search(ctext) is not None
            cure_m = CURE_PAT.search(ctext)
            cure_days = int(cure_m.group("days")) if cure_m else None
            termination = bool(TERMINATION_PAT.search(ctext))
            renew_window_days = None
            rw = RENEWAL_WINDOW_PAT.search(ctext)
            if rw:
                try:
                    renew_window_days = int(rw.group(1))
                except Exception:
                    pass

            self._add_node(G, cid, title, "clause",
                           auto_renewal=auto_renew,
                           service_credit=service_credit,
                           notice=notice,
                           cure_days=cure_days,
                           termination=termination,
                           renew_window_days=renew_window_days)
            # naive: link clauses to all parties seen
            for pid in [n for n, d in G.nodes(data=True) if d.get("type") == "party"]:
                self._add_edge(G, pid, cid, "subject_to")

            # obligation nodes: "shall/must/will"
            if re.search(r"(?i)\b(shall|must|will)\b", ctext):
                oid = f"obl:{cid}"
                self._add_node(G, oid, f"Obligation {cid}", "obligation")
                self._add_edge(G, cid, oid, "defines")

            # events: termination/renewal
            if termination:
                eid = f"event:term:{cid}"
                self._add_node(G, eid, "Termination Event", "event")
                self._add_edge(G, cid, eid, "triggers")
            if auto_renew:
                eid = f"event:renew:{cid}"
                self._add_node(G, eid, "Auto-Renewal", "event")
                self._add_edge(G, cid, eid, "triggers")

            if notice:
                nid = f"notice:{cid}"
                self._add_node(G, nid, "Notice", "notice")
                self._add_edge(G, cid, nid, "requires")

        self._graph = G
        # Render tiny PNG/SVG
        render_dir = index_dir().parent / "exports" / "graphs"
        render_dir.mkdir(parents=True, exist_ok=True)
        path = render_dir / f"entity_graph_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
        plt.figure(figsize=(6, 4))
        pos = nx.spring_layout(G, seed=42, k=0.75)
        labels = {n: d.get("label", n) for n, d in G.nodes(data=True)}
        colors = []
        for _, d in G.nodes(data=True):
            t = d.get("type")
            colors.append({
                "party": "#a6cee3",
                "clause": "#b2df8a",
                "obligation": "#fb9a99",
                "event": "#fdbf6f",
                "notice": "#cab2d6",
                "affiliate": "#ffff99",
            }.get(t, "#cccccc"))
        nx.draw_networkx_nodes(G, pos, node_size=500, node_color=colors)
        nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle="-|>", width=1.0)
        nx.draw_networkx_labels(G, pos, labels, font_size=8)
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        self._graph_render_path = str(path)

        # Serialize
        nodes = []
        for n, d in G.nodes(data=True):
            nodes.append(GraphNode(id=str(n), label=d.get("label", str(n)), type=d.get("type", "clause"), attrs={k:v for k,v in d.items() if k not in {"label","type"}}))
        edges = []
        for u, v, d in G.edges(data=True):
            edges.append({"from": str(u), "to": str(v), "label": d.get("label"), "attrs": {k:v for k,v in d.items() if k != "label"}})

        return EntityGraph(nodes=nodes, edges=edges, render_path=str(path))

    def has_graph(self) -> bool:
        return self._graph is not None

    # -------- Querying --------

    def sample_query_auto_renewals(self, days: int, service_credits_lt: Optional[float]) -> GraphQueryResult:
        """
        Example interpretation:
        - Find clause nodes with auto_renewal=True
        - If days given, prefer clauses mentioning '{days} day' windows near 'renew'
        - If service_credits_lt given, filter clauses that mention service credits with amounts below threshold
        """
        if self._graph is None:
            return GraphQueryResult(query="no-graph", matches=[])

        matches: List[str] = []
        for n, d in self._graph.nodes(data=True):
            if d.get("type") != "clause":
                continue
            if not d.get("auto_renewal"):
                continue
            ok = True
            rw = d.get("renew_window_days")
            if rw is not None and days is not None:
                ok = ok and (rw <= days)
            if ok and service_credits_lt is not None:
                # check a sibling "service credit" flag; we do not store value per clause, so heuristic: if any amount is present in attrs and < threshold
                # attrs might not have amounts, so we simply require service_credit flag; since values are not parsed per-clause here, treat as match.
                # (Can be extended to per-clause extraction later.)
                ok = d.get("service_credit", False)
            if ok:
                matches.append(str(n))

        return GraphQueryResult(
            query=f"auto-renewals in {days} days with service credits < {service_credits_lt}" if service_credits_lt is not None else f"auto-renewals in {days} days",
            matches=matches
        )
