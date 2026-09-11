import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import json
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config

logger = logging.getLogger("BBMP_FW_Report.TBClient")

IST = timezone(timedelta(hours=5, minutes=30))

class ThingsBoardClient:
    def __init__(self, host=None, username=None, password=None, customer_id=None):
        self.host = (host or Config.TB_HOST).rstrip("/")
        self.username = username or Config.TB_USERNAME
        self.password = password or Config.TB_PASSWORD
        self.customer_id = customer_id or Config.BBMP_CUSTOMER_ID
        self.token = None
        
        self.session = requests.Session()
        retries = Retry(
            total=4,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=50)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def authenticate(self):
        url = f"{self.host}/api/auth/login"
        payload = {"username": self.username, "password": self.password}
        logger.info(f"Authenticating with ThingsBoard at {self.host} as {self.username}...")
        try:
            resp = self.session.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                self.token = resp.json().get("token")
                self.session.headers.update({
                    "X-Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                })
                logger.info("Authentication successful.")
                return True
            else:
                logger.error(f"Authentication failed ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return False

    def fetch_all_devices(self, page_size=1000):
        if not self.token:
            if not self.authenticate():
                raise ConnectionError("Could not authenticate with ThingsBoard.")
                
        all_devices = []
        page = 0
        logger.info(f"Fetching device infos for customer {self.customer_id}...")
        
        while True:
            url = f"{self.host}/api/customer/{self.customer_id}/deviceInfos?pageSize={page_size}&page={page}"
            try:
                r = self.session.get(url, timeout=20)
                if r.status_code != 200:
                    logger.error(f"Failed to fetch page {page}: {r.status_code} - {r.text}")
                    break
                data = r.json()
                batch = data.get("data", [])
                all_devices.extend(batch)
                total_elements = data.get("totalElements", 0)
                logger.info(f"Fetched page {page} ({len(batch)} devices) - Total: {len(all_devices)} / {total_elements}")
                if not data.get("hasNext"):
                    break
                page += 1
            except Exception as e:
                logger.error(f"Exception fetching device page {page}: {e}")
                break
                
        logger.info(f"Total devices retrieved: {len(all_devices)}")
        return all_devices

    def _fetch_single_device_info(self, dev):
        dev_id = dev["id"]["id"]
        dev_name = dev.get("name", "").strip()
        dev_label = dev.get("label", "").strip()
        dev_type = dev.get("type", "").strip()
        created_time = dev.get("createdTime", 0)
        
        fw_ver = "Unknown"
        gsm_ver = "Unknown"
        region = "Unknown"
        zone = "Unknown"
        ward = "Unknown"
        active = None
        device_type_attr = dev_type
        imei = ""
        ccid = ""
        last_activity_ts = 0
        systime = 0
        pkt = None

        # 1. Fetch attributes
        attr_keys = "ver,gsmVersion,region,zoneName,wardName,active,deviceType,imeiNumber,gsmCCID,lastActivityTime,cs_ver,cs_gsmVersion"
        try:
            r_attr = self.session.get(
                f"{self.host}/api/plugins/telemetry/DEVICE/{dev_id}/values/attributes?keys={attr_keys}",
                timeout=12
            )
            if r_attr.status_code == 200:
                for item in r_attr.json():
                    k = item.get("key")
                    v = item.get("value")
                    if k == "ver" and v:
                        fw_ver = str(v).strip()
                    elif k == "cs_ver" and v and fw_ver == "Unknown":
                        fw_ver = str(v).strip()
                    elif k == "gsmVersion" and v:
                        gsm_ver = str(v).strip()
                    elif k == "cs_gsmVersion" and v and gsm_ver == "Unknown":
                        gsm_ver = str(v).strip()
                    elif k == "region" and v:
                        region = str(v).strip()
                    elif k == "zoneName" and v:
                        zone = str(v).strip()
                    elif k == "wardName" and v:
                        ward = str(v).strip()
                    elif k == "active":
                        active = bool(v)
                    elif k == "deviceType" and v:
                        device_type_attr = str(v).strip()
                    elif k == "imeiNumber" and v:
                        imei = str(v).strip()
                    elif k == "gsmCCID" and v:
                        ccid = str(v).strip()
                    elif k == "lastActivityTime" and v:
                        last_activity_ts = int(v)
        except Exception as e:
            pass

        # 2. Fetch timeseries if ver is unknown or for systime/pkt
        try:
            r_ts = self.session.get(
                f"{self.host}/api/plugins/telemetry/DEVICE/{dev_id}/values/timeseries?keys=ver,cs_ver,systime,pkt,fault",
                timeout=12
            )
            if r_ts.status_code == 200:
                ts_data = r_ts.json()
                if fw_ver == "Unknown":
                    if "ver" in ts_data and ts_data["ver"]:
                        fw_ver = str(ts_data["ver"][0]["value"]).strip()
                    elif "cs_ver" in ts_data and ts_data["cs_ver"]:
                        fw_ver = str(ts_data["cs_ver"][0]["value"]).strip()
                if "systime" in ts_data and ts_data["systime"]:
                    try:
                        systime = int(ts_data["systime"][0]["value"])
                    except (ValueError, TypeError):
                        pass
                if "pkt" in ts_data and ts_data["pkt"]:
                    pkt = str(ts_data["pkt"][0]["value"]).strip()
        except Exception as e:
            pass

        # Determine online / offline status based on systime (4 hour threshold as per BBMP standard)
        now_ts = int(time.time())
        is_online = False
        last_comm_dt = None

        if systime > 0:
            last_comm_dt = datetime.fromtimestamp(systime, tz=timezone.utc).astimezone(IST).strftime("%Y-%m-%d %H:%M:%S")
            if (now_ts - systime) < 14400:  # 4 hours
                is_online = True
        elif last_activity_ts > 0:
            last_comm_dt = datetime.fromtimestamp(last_activity_ts / 1000.0, tz=timezone.utc).astimezone(IST).strftime("%Y-%m-%d %H:%M:%S")
            if (now_ts - (last_activity_ts / 1000.0)) < 14400:
                is_online = True
        elif active is True:
            is_online = True

        # Clean region/zone naming
        clean_region = region
        if clean_region.lower() in ["east", "e", "east zone"]:
            clean_region = "EAST"
        elif "bommanahalli" in clean_region.lower() or "bommanahali" in clean_region.lower() or "bom" in clean_region.lower():
            clean_region = "BOMMANAHALLI"
        elif clean_region == "Unknown" or not clean_region:
            # Try to infer from zone
            if any(z in zone.lower() for z in ["shanthi", "sarvagna", "cv raman", "shivaji", "pulakeshi"]):
                clean_region = "EAST"
            elif any(z in zone.lower() for z in ["bommanahalli", "hsr", "arekere", "anugraha", "hongasandra"]):
                clean_region = "BOMMANAHALLI"

        return {
            "device_id": dev_id,
            "panel_name": dev_name,
            "panel_label": dev_label,
            "device_type": device_type_attr,
            "fw_version": fw_ver,
            "gsm_version": gsm_ver,
            "region": clean_region,
            "zone": zone,
            "ward": ward,
            "active": active,
            "is_online": is_online,
            "systime": systime,
            "last_comm_time": last_comm_dt or "Never",
            "imei": imei,
            "ccid": ccid
        }

    def fetch_all_panel_data(self, max_workers=35, limit=None):
        devices = self.fetch_all_devices()
        if limit:
            devices = devices[:limit]
            
        logger.info(f"Fetching FW version & metadata for {len(devices)} panels using {max_workers} threads...")
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_dev = {executor.submit(self._fetch_single_device_info, dev): dev for dev in devices}
            completed_count = 0
            total = len(devices)
            
            for future in as_completed(future_to_dev):
                res = future.result()
                results.append(res)
                completed_count += 1
                if completed_count % 500 == 0 or completed_count == total:
                    elapsed = time.time() - start_time
                    logger.info(f"Progress: {completed_count}/{total} panels processed ({completed_count/total*100:.1f}%) in {elapsed:.1f}s")
                    
        elapsed = time.time() - start_time
        logger.info(f"Successfully processed all {len(results)} panels in {elapsed:.2f}s")
        return results
