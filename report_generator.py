import os
import json
import logging
from datetime import datetime, timezone, timedelta
from jinja2 import Template
from collections import defaultdict
import openpyxl

logger = logging.getLogger("BBMP_FW_Report.ReportGenerator")

class ReportGenerator:
    def __init__(self, analysis_result, panels_raw_data):
        self.data = analysis_result
        self.panels = panels_raw_data

    def generate_html_dashboard(self, output_path="fw_dashboard_preview.html"):
        logger.info(f"Generating email-safe HTML dashboard at {output_path}...")
        
        region_list = []
        for reg_name, reg_data in sorted(self.data["regions"].items()):
            v55 = reg_data["versions"]["SL530.55"]
            v54 = reg_data["versions"]["SL530.54"]
            v47 = reg_data["versions"]["SL530.47"]
            
            zone_list = []
            for z_name, z_data in sorted(reg_data["zones"].items()):
                zv55 = z_data["versions"]["SL530.55"]
                zv54 = z_data["versions"]["SL530.54"]
                zv47 = z_data["versions"]["SL530.47"]
                zone_list.append({
                    "zone_name": z_name,
                    "total": z_data["total"],
                    "v55": zv55,
                    "v54": zv54,
                    "v47": zv47,
                    "other": z_data["other_count"],
                    "online": z_data["online"],
                    "offline": z_data["offline"],
                    "offline_pf": z_data["offline_pf"]
                })

            region_list.append({
                "region_name": reg_name,
                "total": reg_data["total"],
                "v55": v55,
                "v54": v54,
                "v47": v47,
                "other": reg_data["other_count"],
                "online": reg_data["online"],
                "offline": reg_data["offline"],
                "offline_pf": reg_data["offline_pf"],
                "zones": zone_list
            })

        # Lookup dictionary for fast access in KPI cards & progress bar
        v_map = {row["version"]: row for row in self.data["summary_rows"]}
        v55 = v_map.get("SL530.55", {"count": 0, "percentage": 0, "online": 0, "offline": 0, "offline_pf": 0, "online_pct": 0})
        v54 = v_map.get("SL530.54", {"count": 0, "percentage": 0, "online": 0, "offline": 0, "offline_pf": 0, "online_pct": 0})
        v47 = v_map.get("SL530.47", {"count": 0, "percentage": 0, "online": 0, "offline": 0, "offline_pf": 0, "online_pct": 0})
        v_other = v_map.get("Other Versions", {"count": 0, "percentage": 0, "online": 0, "offline": 0, "offline_pf": 0, "online_pct": 0})

        # Ultra-clean, robust, email-client compliant HTML layout (no hidden/clipped text)
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BBMP Panels - Firmware Version Status Dashboard</title>
<style>
  body {
    margin: 0;
    padding: 0;
    background-color: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #334155;
    -webkit-font-smoothing: antialiased;
  }
  table {
    border-collapse: collapse;
    mso-table-lspace: 0pt;
    mso-table-rspace: 0pt;
  }
  td {
    padding: 0;
  }
</style>
</head>
<body style="margin: 0; padding: 20px 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">

<center>
<table width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width: 860px; background-color: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0;">
  <!-- Header -->
  <tr>
    <td style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #172554 100%); padding: 28px 32px; border-bottom: 3px solid #3b82f6;">
      <div style="display: inline-block; background: rgba(59, 130, 246, 0.25); color: #93c5fd; border: 1px solid rgba(147, 197, 253, 0.4); padding: 3px 10px; border-radius: 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
        Live BBMP Telemetry Audit
      </div>
      <h1 style="margin: 0 0 4px 0; font-size: 22px; font-weight: 800; color: #ffffff;">BBMP Panels &bull; Firmware Version Dashboard</h1>
      <p style="margin: 0; font-size: 12px; color: #cbd5e1;">Generated: {{ data.timestamp }} &bull; Schnell IoT Platform</p>
    </td>
  </tr>

  <!-- Main Body Content -->
  <tr>
    <td style="padding: 24px 32px 32px 32px;">
      
      <!-- Horizontal KPI Cards Table (Direct inline styling to prevent any client clipping) -->
      <table width="100%" border="0" cellpadding="0" cellspacing="10" style="margin-bottom: 24px;">
        <tr>
          <!-- Card 1: .55 (Latest Version) -->
          <td width="20%" style="background-color: #fffbeb; border: 1px solid #fde68a; border-top: 4px solid #f59e0b; border-radius: 8px; padding: 12px 10px; text-align: center; vertical-align: top;">
            <div style="font-size: 10px; font-weight: 800; color: #b45309; text-transform: uppercase; letter-spacing: 0.5px; line-height: 14px;">Latest Version</div>
            <div style="font-size: 13px; font-weight: 800; color: #92400e; margin-top: 2px;">SL530.55</div>
            <div style="font-size: 26px; font-weight: 900; color: #92400e; margin: 4px 0 2px 0; line-height: 1.1;">{{ "{:,}".format(v55.count) }}</div>
            <div style="font-size: 11px; font-weight: 700; color: #b45309;">{{ "%.2f"|format(v55.percentage) }}% Share</div>
            <div style="font-size: 10px; font-weight: 600; color: #64748b; margin-top: 2px;"><span style="color: #15803d;">{{ "{:,}".format(v55.online) }} On</span> &bull; <span style="color: #b91c1c;">{{ "{:,}".format(v55.offline) }} Off</span>{% if v55.offline_pf > 0 %} &bull; <span style="color: #b45309;">{{ v55.offline_pf }} PF</span>{% endif %}</div>
          </td>

          <!-- Card 2: .54 -->
          <td width="20%" style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-top: 4px solid #10b981; border-radius: 8px; padding: 12px 10px; text-align: center; vertical-align: top;">
            <div style="font-size: 10px; font-weight: 800; color: transparent; line-height: 14px;">&nbsp;</div>
            <div style="font-size: 13px; font-weight: 800; color: #065f46; margin-top: 2px;">SL530.54</div>
            <div style="font-size: 26px; font-weight: 900; color: #065f46; margin: 4px 0 2px 0; line-height: 1.1;">{{ "{:,}".format(v54.count) }}</div>
            <div style="font-size: 11px; font-weight: 700; color: #047857;">{{ "%.2f"|format(v54.percentage) }}% Share</div>
            <div style="font-size: 10px; font-weight: 600; color: #64748b; margin-top: 2px;"><span style="color: #15803d;">{{ "{:,}".format(v54.online) }} On</span> &bull; <span style="color: #b91c1c;">{{ "{:,}".format(v54.offline) }} Off</span>{% if v54.offline_pf > 0 %} &bull; <span style="color: #b45309;">{{ v54.offline_pf }} PF</span>{% endif %}</div>
          </td>

          <!-- Card 3: .47 -->
          <td width="20%" style="background-color: #fef2f2; border: 1px solid #fecaca; border-top: 4px solid #ef4444; border-radius: 8px; padding: 12px 10px; text-align: center; vertical-align: top;">
            <div style="font-size: 10px; font-weight: 800; color: transparent; line-height: 14px;">&nbsp;</div>
            <div style="font-size: 13px; font-weight: 800; color: #991b1b; margin-top: 2px;">SL530.47</div>
            <div style="font-size: 26px; font-weight: 900; color: #991b1b; margin: 4px 0 2px 0; line-height: 1.1;">{{ "{:,}".format(v47.count) }}</div>
            <div style="font-size: 11px; font-weight: 700; color: #b91c1c;">{{ "%.2f"|format(v47.percentage) }}% Share</div>
            <div style="font-size: 10px; font-weight: 600; color: #64748b; margin-top: 2px;"><span style="color: #15803d;">{{ "{:,}".format(v47.online) }} On</span> &bull; <span style="color: #b91c1c;">{{ "{:,}".format(v47.offline) }} Off</span>{% if v47.offline_pf > 0 %} &bull; <span style="color: #b45309;">{{ v47.offline_pf }} PF</span>{% endif %}</div>
          </td>

          <!-- Card 4: Park Slots -->
          <td width="20%" style="background-color: #f3e8ff; border: 1px solid #e9d5ff; border-top: 4px solid #a855f7; border-radius: 8px; padding: 12px 10px; text-align: center; vertical-align: top;">
            <div style="font-size: 10px; font-weight: 800; color: #6b21a8; text-transform: uppercase; letter-spacing: 0.5px; line-height: 14px;">Park Slots</div>
            <div style="font-size: 13px; font-weight: 800; color: #581c87; margin-top: 2px;">SL530.59</div>
            <div style="font-size: 26px; font-weight: 900; color: #581c87; margin: 4px 0 2px 0; line-height: 1.1;">{{ "{:,}".format(data.park_slots.completed) }}<span style="font-size: 14px; color: #7e22ce;">/{{ data.park_slots.total }}</span></div>
            <div style="font-size: 11px; font-weight: 700; color: #7e22ce;">{{ "%.1f"|format(data.park_slots.percentage) }}% Completed</div>
            <div style="font-size: 10px; font-weight: 600; color: #64748b; margin-top: 2px;"><span style="color: #15803d;">{{ "{:,}".format(data.park_slots.online) }} On</span> &bull; <span style="color: #b91c1c;">{{ "{:,}".format(data.park_slots.offline) }} Off</span>{% if data.park_slots.offline_pf > 0 %} &bull; <span style="color: #b45309;">{{ data.park_slots.offline_pf }} PF</span>{% endif %}</div>
          </td>

          <!-- Card 5: Total Panels -->
          <td width="20%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-top: 4px solid #0f172a; border-radius: 8px; padding: 12px 10px; text-align: center; vertical-align: top;">
            <div style="font-size: 10px; font-weight: 800; color: transparent; line-height: 14px;">&nbsp;</div>
            <div style="font-size: 13px; font-weight: 800; color: #0f172a; margin-top: 2px;">Total Panels</div>
            <div style="font-size: 26px; font-weight: 900; color: #0f172a; margin: 4px 0 2px 0; line-height: 1.1;">{{ "{:,}".format(data.total_panels) }}</div>
            <div style="font-size: 11px; font-weight: 700; color: #334155;">{{ "%.1f"|format(data.online_pct) }}% Online</div>
            <div style="font-size: 10px; font-weight: 600; color: #64748b; margin-top: 2px;"><span style="color: #15803d;">{{ "{:,}".format(data.online_total) }} On</span> &bull; <span style="color: #b91c1c;">{{ "{:,}".format(data.offline_total) }} Off</span>{% if data.offline_pf_total > 0 %} &bull; <span style="color: #b45309;">{{ "{:,}".format(data.offline_pf_total) }} PF</span>{% endif %}</div>
          </td>
        </tr>
      </table>

      <!-- Fleet Share Progress Bar -->
      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 24px;">
        <tr>
          <td>
            <div style="font-size: 12px; font-weight: 700; color: #475569; margin-bottom: 8px; display: flex; justify-content: space-between;">
              <span>Fleet Firmware Share</span>
              <span>{{ "{:,}".format(data.total_panels) }} Panels</span>
            </div>
            <!-- Multi segment bar -->
            <table width="100%" height="12" border="0" cellpadding="0" cellspacing="0" style="background-color: #e2e8f0; border-radius: 6px; overflow: hidden;">
              <tr>
                <td width="{{ '%.2f'|format(v55.percentage) }}%" style="background-color: #f59e0b;" title="SL530.55 ({{ '%.2f'|format(v55.percentage) }}%)"></td>
                <td width="{{ '%.2f'|format(v54.percentage) }}%" style="background-color: #10b981;" title="SL530.54 ({{ '%.2f'|format(v54.percentage) }}%)"></td>
                <td width="{{ '%.2f'|format(v47.percentage) }}%" style="background-color: #ef4444;" title="SL530.47 ({{ '%.2f'|format(v47.percentage) }}%)"></td>
                {% if v_other.count > 0 %}
                <td width="{{ '%.2f'|format(v_other.percentage) }}%" style="background-color: #94a3b8;" title="Others ({{ '%.2f'|format(v_other.percentage) }}%)"></td>
                {% endif %}
              </tr>
            </table>
            <!-- Legend -->
            <div style="margin-top: 8px; font-size: 11px; font-weight: 600; color: #475569;">
              <span style="color: #b45309;">&#9632; SL530.55: {{ "{:,}".format(v55.count) }} ({{ "%.2f"|format(v55.percentage) }}%)</span> &nbsp;&bull;&nbsp;
              <span style="color: #047857;">&#9632; SL530.54: {{ "{:,}".format(v54.count) }} ({{ "%.2f"|format(v54.percentage) }}%)</span> &nbsp;&bull;&nbsp;
              <span style="color: #b91c1c;">&#9632; SL530.47: {{ "{:,}".format(v47.count) }} ({{ "%.2f"|format(v47.percentage) }}%)</span>
              {% if v_other.count > 0 %}
              &nbsp;&bull;&nbsp; <span style="color: #64748b;">&#9632; Others: {{ "{:,}".format(v_other.count) }} ({{ "%.2f"|format(v_other.percentage) }}%)</span>
              {% endif %}
            </div>
          </td>
        </tr>
      </table>

      <!-- Section Title: Summary Table -->
      <div style="font-size: 15px; font-weight: 800; color: #0f172a; margin: 24px 0 10px 0; border-left: 4px solid #2563eb; padding-left: 8px;">
        Firmware Version Summary
      </div>
      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-bottom: 24px; font-size: 13px;">
        <thead>
          <tr style="background-color: #0f172a; color: #ffffff;">
            <th style="padding: 10px 14px; text-align: left; font-size: 12px; font-weight: 700;">Firmware Version</th>
            <th style="padding: 10px 14px; text-align: right; font-size: 12px; font-weight: 700;">Total Panels</th>
            <th style="padding: 10px 14px; text-align: right; font-size: 12px; font-weight: 700;">Share (%)</th>
            <th style="padding: 10px 14px; text-align: center; font-size: 12px; font-weight: 700; color: #86efac;">ONLINE</th>
            <th style="padding: 10px 14px; text-align: center; font-size: 12px; font-weight: 700; color: #fca5a5;">OFFLINE (Real)</th>
            <th style="padding: 10px 14px; text-align: center; font-size: 12px; font-weight: 700; color: #fde68a;">OFFLINE (PF)</th>
            <th style="padding: 10px 14px; text-align: center; font-size: 12px; font-weight: 700;">Online Rate</th>
          </tr>
        </thead>
        <tbody>
          {% for row in data.summary_rows %}
          <tr style="border-bottom: 1px solid #f1f5f9; background-color: {% if loop.index is even %}#fafbfc{% else %}#ffffff{% endif %};">
            <td style="padding: 10px 14px;">
              {% if row.version == "SL530.55" %}
                <span style="background-color: #fef3c7; color: #92400e; font-weight: 800; padding: 3px 8px; border-radius: 4px; font-size: 12px; border: 1px solid #fde68a;">SL530.55</span>
              {% elif row.version == "SL530.54" %}
                <span style="background-color: #dcfce7; color: #166534; font-weight: 800; padding: 3px 8px; border-radius: 4px; font-size: 12px; border: 1px solid #bbf7d0;">SL530.54</span>
              {% elif row.version == "SL530.47" %}
                <span style="background-color: #fee2e2; color: #991b1b; font-weight: 800; padding: 3px 8px; border-radius: 4px; font-size: 12px; border: 1px solid #fecaca;">SL530.47</span>
              {% else %}
                <span style="font-weight: 700; color: #64748b;">{{ row.version }}</span>
              {% endif %}
            </td>
            <td style="padding: 10px 14px; text-align: right; font-weight: 800; font-size: 14px; color: #0f172a;">{{ "{:,}".format(row.count) }}</td>
            <td style="padding: 10px 14px; text-align: right; font-weight: 600; color: #334155;">{{ "%.2f"|format(row.percentage) }}%</td>
            <td style="padding: 10px 14px; text-align: center; color: #15803d; font-weight: 700;">{{ "{:,}".format(row.online) }}</td>
            <td style="padding: 10px 14px; text-align: center; color: #b91c1c; font-weight: 700;">{{ "{:,}".format(row.offline) }}</td>
            <td style="padding: 10px 14px; text-align: center; color: #b45309; font-weight: 700;">{{ "{:,}".format(row.offline_pf) }}</td>
            <td style="padding: 10px 14px; text-align: center; font-weight: 700; color: #0f172a;">{{ "%.1f"|format(row.online_pct) }}%</td>
          </tr>
          {% endfor %}
          <!-- Total Footer Row -->
          <tr style="background-color: #f1f5f9; font-weight: 800; border-top: 2px solid #cbd5e1;">
            <td style="padding: 10px 14px; color: #0f172a;">TOTAL BBMP PANELS</td>
            <td style="padding: 10px 14px; text-align: right; color: #0f172a; font-size: 14px;">{{ "{:,}".format(data.total_panels) }}</td>
            <td style="padding: 10px 14px; text-align: right; color: #0f172a;">100.00%</td>
            <td style="padding: 10px 14px; text-align: center; color: #15803d;">{{ "{:,}".format(data.online_total) }}</td>
            <td style="padding: 10px 14px; text-align: center; color: #b91c1c;">{{ "{:,}".format(data.offline_total) }}</td>
            <td style="padding: 10px 14px; text-align: center; color: #b45309;">{{ "{:,}".format(data.offline_pf_total) }}</td>
            <td style="padding: 10px 14px; text-align: center; color: #0f172a;">{{ "%.1f"|format(data.online_pct) }}%</td>
          </tr>
        </tbody>
      </table>

      <!-- Section Title: Region & Zone Matrix -->
      <div style="font-size: 15px; font-weight: 800; color: #0f172a; margin: 24px 0 10px 0; border-left: 4px solid #0f766e; padding-left: 8px;">
        Region &amp; Zone Distribution
      </div>
      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; font-size: 13px;">
        <thead>
          <tr style="background-color: #0f172a; color: #ffffff;">
            <th style="padding: 10px 14px; text-align: left; font-size: 12px; font-weight: 700;">Region / Zone</th>
            <th style="padding: 10px 14px; text-align: right; font-size: 12px; font-weight: 700;">Total Panels</th>
            <th style="padding: 10px 14px; text-align: right; font-size: 12px; font-weight: 700; color: #fde68a;">SL530.55</th>
            <th style="padding: 10px 14px; text-align: right; font-size: 12px; font-weight: 700; color: #bbf7d0;">SL530.54</th>
            <th style="padding: 10px 14px; text-align: right; font-size: 12px; font-weight: 700; color: #fecaca;">SL530.47</th>
            <th style="padding: 10px 14px; text-align: center; font-size: 12px; font-weight: 700;">Connectivity</th>
          </tr>
        </thead>
        <tbody>
          {% for reg in region_list %}
          <!-- Region Row -->
          <tr style="background-color: #e2e8f0; font-weight: 800; border-top: 1px solid #cbd5e1;">
            <td style="padding: 10px 14px; color: #0f172a;">{{ reg.region_name }}</td>
            <td style="padding: 10px 14px; text-align: right; color: #0f172a;">{{ "{:,}".format(reg.total) }}</td>
            <td style="padding: 10px 14px; text-align: right; color: #b45309; font-weight: 800;">{{ "{:,}".format(reg.v55) }}</td>
            <td style="padding: 10px 14px; text-align: right; color: #047857; font-weight: 800;">{{ "{:,}".format(reg.v54) }}</td>
            <td style="padding: 10px 14px; text-align: right; color: #b91c1c; font-weight: 800;">{{ "{:,}".format(reg.v47) }}</td>
            <td style="padding: 10px 14px; text-align: center; font-size: 11px;">
              <span style="color: #15803d; font-weight: 700;">{{ reg.online }} On</span> &bull; <span style="color: #b91c1c; font-weight: 700;">{{ reg.offline }} Off</span>{% if reg.offline_pf > 0 %} &bull; <span style="color: #b45309; font-weight: 700;">{{ reg.offline_pf }} PF</span>{% endif %}
            </td>
          </tr>
          <!-- Zone Rows -->
          {% for z in reg.zones %}
          <tr style="border-bottom: 1px solid #f1f5f9; background-color: {% if loop.index is even %}#fafbfc{% else %}#ffffff{% endif %};">
            <td style="padding: 8px 14px 8px 24px; color: #475569;">&bull; {{ z.zone_name }}</td>
            <td style="padding: 8px 14px; text-align: right; font-weight: 600; color: #334155;">{{ "{:,}".format(z.total) }}</td>
            <td style="padding: 8px 14px; text-align: right; color: #b45309; font-weight: 700;">{{ "{:,}".format(z.v55) }}</td>
            <td style="padding: 8px 14px; text-align: right; color: #047857; font-weight: 700;">{{ "{:,}".format(z.v54) }}</td>
            <td style="padding: 8px 14px; text-align: right; color: #b91c1c; font-weight: 700;">{{ "{:,}".format(z.v47) }}</td>
            <td style="padding: 8px 14px; text-align: center; font-size: 11px; color: #64748b;">
              <span style="color: #15803d; font-weight: 600;">{{ z.online }}</span> / <span style="color: #b91c1c; font-weight: 600;">{{ z.offline }}</span>{% if z.offline_pf > 0 %} / <span style="color: #b45309; font-weight: 600;">{{ z.offline_pf }} PF</span>{% endif %}
            </td>
          </tr>
          {% endfor %}
          {% endfor %}
        </tbody>
      </table>

    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 32px; font-size: 12px; color: #64748b;">
      <table width="100%" border="0" cellpadding="0" cellspacing="0">
        <tr>
          <td style="font-weight: 700; color: #1e293b;">BBMP Smart Street Light Monitoring System</td>
          <td style="text-align: right; color: #64748b;">Schnell Energy IoT Platform</td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</center>

</body>
</html>
"""
        template = Template(html_template)
        rendered_html = template.render(
            data=self.data,
            region_list=region_list,
            v55=v55,
            v54=v54,
            v47=v47,
            v_other=v_other
        )
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)
            
        logger.info(f"Email-safe HTML dashboard generated successfully at {output_path}")
        return output_path

    def generate_ward_breakdown_excel(self, output_path="Ward_FW_Breakdown.xlsx"):
        logger.info(f"Generating ward breakdown excel at {output_path}...")
        
        # Group by Zone -> Ward
        # Target structure: ward_data[zone][ward] = {"total": 0, "SL530.55": 0, "SL530.54": 0, "SL530.47": 0, "Others": 0}
        ward_data = defaultdict(lambda: defaultdict(lambda: {"total": 0, "SL530.55": 0, "SL530.54": 0, "SL530.47": 0, "Others": 0}))
        
        for p in self.panels:
            z = p.get("zone", "Unknown")
            w = p.get("ward", "Unknown")
            fw = p.get("fw_version", "Unknown")
            
            ward_data[z][w]["total"] += 1
            if fw in ["SL530.55", "SL530.54", "SL530.47"]:
                ward_data[z][w][fw] += 1
            else:
                ward_data[z][w]["Others"] += 1

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Ward Breakdown"
        
        headers = ["Zone", "Ward", "Total Panels", "SL530.55", "SL530.54", "SL530.47", "Others"]
        ws.append(headers)
        
        # Header formatting
        for cell in ws[1]:
            cell.font = openpyxl.styles.Font(bold=True)
            cell.fill = openpyxl.styles.PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
            
        # Write rows sorted by Zone, then Ward
        for z in sorted(ward_data.keys()):
            for w in sorted(ward_data[z].keys()):
                d = ward_data[z][w]
                row = [z, w, d["total"], d["SL530.55"], d["SL530.54"], d["SL530.47"], d["Others"]]
                ws.append(row)
                
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter 
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column].width = adjusted_width
            
        wb.save(output_path)
        logger.info(f"Ward breakdown excel generated successfully at {output_path}")
        return output_path

