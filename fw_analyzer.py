import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("BBMP_FW_Report.Analyzer")
IST = timezone(timedelta(hours=5, minutes=30))

# Order: .55 first, then .54, then .47 as requested
FOCUSED_VERSIONS = ["SL530.55", "SL530.54", "SL530.47"]

class FirmwareAnalyzer:
    def __init__(self, panels_data):
        self.panels = panels_data
        self.focused_versions = FOCUSED_VERSIONS

    def analyze(self):
        total_panels = len(self.panels)
        if total_panels == 0:
            return {}

        now_str = datetime.now(IST).strftime("%d-%b-%Y %I:%M %p IST")
        
        # 1. Classify each panel into focused versions or "Other Versions"
        version_stats = {
            v: {"count": 0, "online": 0, "offline": 0} for v in self.focused_versions
        }
        version_stats["Other Versions"] = {"count": 0, "online": 0, "offline": 0, "breakdown": Counter()}

        online_total = 0
        offline_total = 0

        # Region & Zone Breakdown
        regions = defaultdict(lambda: {
            "total": 0,
            "online": 0,
            "offline": 0,
            "versions": {v: 0 for v in self.focused_versions},
            "other_count": 0,
            "zones": defaultdict(lambda: {
                "total": 0,
                "online": 0,
                "offline": 0,
                "versions": {v: 0 for v in self.focused_versions},
                "other_count": 0
            })
        })

        for p in self.panels:
            raw_fw = p.get("fw_version", "Unknown")
            is_on = p.get("is_online", False)
            reg = p.get("region") or "Unknown"
            zone = p.get("zone") or "Unknown"

            if is_on:
                online_total += 1
            else:
                offline_total += 1

            # Match focused version
            matched_v = None
            for fv in self.focused_versions:
                if raw_fw == fv:
                    matched_v = fv
                    break

            if matched_v:
                version_stats[matched_v]["count"] += 1
                if is_on:
                    version_stats[matched_v]["online"] += 1
                else:
                    version_stats[matched_v]["offline"] += 1
            else:
                version_stats["Other Versions"]["count"] += 1
                version_stats["Other Versions"]["breakdown"][raw_fw] += 1
                if is_on:
                    version_stats["Other Versions"]["online"] += 1
                else:
                    version_stats["Other Versions"]["offline"] += 1

            # Regional Aggregation
            regions[reg]["total"] += 1
            if is_on:
                regions[reg]["online"] += 1
            else:
                regions[reg]["offline"] += 1

            if matched_v:
                regions[reg]["versions"][matched_v] += 1
            else:
                regions[reg]["other_count"] += 1

            # Zone Aggregation
            regions[reg]["zones"][zone]["total"] += 1
            if is_on:
                regions[reg]["zones"][zone]["online"] += 1
            else:
                regions[reg]["zones"][zone]["offline"] += 1

            if matched_v:
                regions[reg]["zones"][zone]["versions"][matched_v] += 1
            else:
                regions[reg]["zones"][zone]["other_count"] += 1

        # Summary Table Construction
        summary_rows = []
        for v in self.focused_versions:
            c = version_stats[v]["count"]
            on_c = version_stats[v]["online"]
            off_c = version_stats[v]["offline"]
            pct = (c / total_panels * 100) if total_panels else 0
            on_pct = (on_c / c * 100) if c else 0
            summary_rows.append({
                "version": v,
                "count": c,
                "percentage": pct,
                "online": on_c,
                "offline": off_c,
                "online_pct": on_pct,
                "is_main": (v == "SL530.54")
            })

        # Add Others row if count > 0
        oth = version_stats["Other Versions"]
        if oth["count"] > 0:
            pct = (oth["count"] / total_panels * 100) if total_panels else 0
            on_pct = (oth["online"] / oth["count"] * 100) if oth["count"] else 0
            summary_rows.append({
                "version": "Other Versions",
                "count": oth["count"],
                "percentage": pct,
                "online": oth["online"],
                "offline": oth["offline"],
                "online_pct": on_pct,
                "is_main": False,
                "note": ", ".join([f"{k}:{v}" for k, v in oth["breakdown"].items()])
            })

        # Panels on .55 and .47
        upgrade_panels = [p for p in self.panels if p.get("fw_version") in ["SL530.55", "SL530.47"]]

        return {
            "timestamp": now_str,
            "total_panels": total_panels,
            "online_total": online_total,
            "offline_total": offline_total,
            "online_pct": (online_total / total_panels * 100) if total_panels else 0,
            "focused_versions": self.focused_versions,
            "summary_rows": summary_rows,
            "regions": regions,
            "upgrade_panels": upgrade_panels
        }
