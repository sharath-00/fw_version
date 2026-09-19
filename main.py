import argparse
import json
import os
import sys
import logging
from datetime import datetime
from config import Config
from tb_client import ThingsBoardClient
from fw_analyzer import FirmwareAnalyzer
from report_generator import ReportGenerator
from mail_sender import MailSender

logger = logging.getLogger("BBMP_FW_Report.Main")

DATA_CACHE_FILE = "latest_fw_data.json"
HTML_DASHBOARD_FILE = "fw_dashboard_preview.html"

def print_terminal_summary(analysis):
    print("\n" + "="*80)
    print("      BBMP SMART STREET LIGHTS - FIRMWARE VERSION DASHBOARD")
    print("="*80)
    print(f" Timestamp           : {analysis['timestamp']}")
    print(f" Total Panels Scanned: {analysis['total_panels']:,}")
    print(f" ONLINE Panels (<= 4h): {analysis['online_total']:,} ({analysis['online_pct']:.1f}%)")
    print(f" OFFLINE Panels (Real): {analysis['offline_total']:,} ({(analysis['offline_total']/analysis['total_panels']*100):.1f}%)")
    print(f" OFFLINE Panels (PF)  : {analysis.get('offline_pf_total', 0):,} ({(analysis.get('offline_pf_total', 0)/analysis['total_panels']*100):.1f}%)")
    print("-"*80)
    
    print("\n[+] FIRMWARE VERSIONS BREAKDOWN (.55 -> .54 -> .47):")
    print(f" {'Firmware Version':<18} | {'Count':<8} | {'Share (%)':<10} | {'Online':<8} | {'Offline':<8} | {'PF':<6} | {'Online Rate'}")
    print(" "+ "-"*85)
    for row in analysis["summary_rows"]:
        print(f" {row['version']:<18} | {row['count']:<8} | {row['percentage']:>6.2f}%    | {row['online']:<8} | {row['offline']:<8} | {row.get('offline_pf', 0):<6} | {row['online_pct']:>5.1f}%")

    print("\n[+] REGION & ZONE DISTRIBUTION:")
    for reg_name, reg_data in sorted(analysis["regions"].items()):
        v55 = reg_data["versions"]["SL530.55"]
        v54 = reg_data["versions"]["SL530.54"]
        v47 = reg_data["versions"]["SL530.47"]
        print(f" > Region: {reg_name} (Total: {reg_data['total']:,} | .55: {v55} | .54: {v54:,} | .47: {v47} | Online: {reg_data['online']:,})")
        for z_name, z_data in sorted(reg_data["zones"].items()):
            zv55 = z_data["versions"]["SL530.55"]
            zv54 = z_data["versions"]["SL530.54"]
            zv47 = z_data["versions"]["SL530.47"]
            print(f"    - {z_name:<20}: {z_data['total']:>5} panels (.55: {zv55:>3} | .54: {zv54:>5} | .47: {zv47:>2} | Online: {z_data['online']:>5})")

    print("\n" + "="*80 + "\n")

def run(args):
    panels_data = None
    
    if args.cached and os.path.exists(DATA_CACHE_FILE):
        logger.info(f"Loading cached panel data from {DATA_CACHE_FILE}...")
        with open(DATA_CACHE_FILE, "r", encoding="utf-8") as f:
            panels_data = json.load(f)
    else:
        client = ThingsBoardClient()
        limit = args.sample if args.sample else None
        panels_data = client.fetch_all_panel_data(max_workers=args.workers, limit=limit)
        
        with open(DATA_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(panels_data, f, indent=2)
        logger.info(f"Saved {len(panels_data)} panels data to {DATA_CACHE_FILE}")

    analyzer = FirmwareAnalyzer(panels_data)
    analysis = analyzer.analyze()

    print_terminal_summary(analysis)

    # Generate HTML Dashboard Only
    rep_gen = ReportGenerator(analysis, panels_data)
    html_path = rep_gen.generate_html_dashboard(HTML_DASHBOARD_FILE)

    print(f"[OK] HTML Dashboard generated: {os.path.abspath(html_path)}")

    # Generate Ward Breakdown Excel Attachment
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"Ward_FW_Breakdown_{timestamp_str}.xlsx"
    excel_path = rep_gen.generate_ward_breakdown_excel(excel_filename)
    print(f"[OK] Ward Breakdown Excel generated: {os.path.abspath(excel_path)}")

    # Email Dispatch if requested
    if args.send_now:
        logger.info("Dispatching email dashboard to recipient...")
        sender = MailSender()
        success = sender.send_email(
            html_content_path=html_path,
            attachment_path=excel_path
        )
        if success:
            print("\n[OK] Email successfully dispatched to recipient with Excel attachment!")
        else:
            print("\n[FAIL] Email dispatch failed. Please check logs.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BBMP Panels Firmware Version Fetcher & Mail Dashboard")
    parser.add_argument("--send-now", action="store_true", help="Send email dashboard immediately")
    parser.add_argument("--cached", action="store_true", help="Use locally cached data without fetching from ThingsBoard")
    parser.add_argument("--sample", type=int, default=None, help="Limit fetch to N sample panels for testing")
    parser.add_argument("--workers", type=int, default=35, help="Number of parallel worker threads (default: 35)")

    args = parser.parse_args()
    run(args)
