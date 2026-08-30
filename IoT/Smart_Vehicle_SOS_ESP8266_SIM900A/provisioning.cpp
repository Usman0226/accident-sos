// provisioning.cpp — SoftAP + HTTP setup portal for AccidentSOS
//
// The setup wizard HTML/CSS/JS is stored entirely in PROGMEM (flash),
// so it does not consume SRAM.  All fetch() calls go to 192.168.4.1
// (same origin) — no internet required.
//
// ArduinoJson v7 is required.  Install via Library Manager.
#include "provisioning.h"
#include <ArduinoJson.h>

#if ARDUINOJSON_VERSION_MAJOR < 7
  #error "ArduinoJson v7 required. Update in Arduino Library Manager."
#endif

// ─── Externs — defined in main .ino ──────────────────────────────────────────
extern bool        mpuAvailable;   // true if MPU6050 responded at startup
extern bool        simAvailable;   // true if SIM900A responded at startup (NEW)
extern float       batteryPct;     // stub 100.0 — no ADC measurement yet
extern const char *VEHICLE_ID;     // firmware constant e.g. "VEHICLE-001"

// ─── Module state ─────────────────────────────────────────────────────────────
bool inProvisioningMode  = false;
bool provisioningComplete = false;

static ESP8266WebServer webServer(80);
static DNSServer        dnsServer;
static unsigned long    provStartMs = 0;

// ─── PROGMEM HTML wizard ──────────────────────────────────────────────────────
// 6-screen mobile-first wizard.  Inline CSS + vanilla JS only.
// No CDN, no external fonts, fully offline after loading from device.
static const char SETUP_HTML[] PROGMEM = R"rawliteral(<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#0f172a">
<title>AccidentSOS Setup</title>
<style>
:root{--bg:#0f172a;--card:#1e293b;--bdr:#334155;--org:#f97316;--grn:#22c55e;--amb:#f59e0b;--red:#ef4444;--txt:#f1f5f9;--mut:#94a3b8}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh}
.wrap{max-width:440px;margin:0 auto;padding:0 16px 56px}
.hd{text-align:center;padding:32px 0 6px}
.hd-tag{font-size:10px;letter-spacing:4px;color:var(--org);text-transform:uppercase;margin-bottom:6px}
.hd-ttl{font-size:26px;font-weight:800;letter-spacing:-0.5px}
.hd-sub{font-size:13px;color:var(--mut);margin-top:4px}
.dots{display:flex;justify-content:center;gap:7px;padding:20px 0}
.dot{width:8px;height:8px;border-radius:50%;background:var(--bdr);transition:all .3s}
.dot.cur{width:24px;border-radius:4px;background:var(--org)}
.dot.done{background:var(--grn)}
.scr{display:none;animation:fd .22s ease}
.scr.on{display:block}
@keyframes fd{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
.card{background:var(--card);border:1px solid var(--bdr);border-radius:16px;padding:22px;margin-bottom:12px}
.ctag{font-size:10px;letter-spacing:3px;color:var(--mut);text-transform:uppercase;margin-bottom:12px}
.card h2{font-size:20px;font-weight:700;margin-bottom:6px}
.card p{font-size:14px;color:var(--mut);line-height:1.6}
.hero{text-align:center;padding:10px 0}
.hico{font-size:52px;margin-bottom:10px}
.badge{display:inline-block;background:#f9731618;border:1px solid #f9731640;color:var(--org);border-radius:8px;padding:6px 16px;font-size:13px;font-weight:700;margin-top:10px;letter-spacing:1px}
.fg{margin-bottom:16px}
.fg label{display:block;font-size:11px;color:var(--mut);margin-bottom:5px;letter-spacing:.6px;text-transform:uppercase}
.irow{display:flex}
.pfx{background:#0f172a;border:1px solid var(--bdr);border-right:none;border-radius:10px 0 0 10px;padding:0 11px;font-size:15px;color:var(--mut);display:flex;align-items:center;white-space:nowrap;user-select:none}
input[type=tel]{flex:1;background:#0f172a;border:1px solid var(--bdr);border-radius:0 10px 10px 0;padding:13px 13px;font-size:16px;color:var(--txt);outline:none;transition:border-color .2s;min-width:0}
input[type=text]{background:#0f172a;border:1px solid var(--bdr);border-radius:10px;padding:13px 13px;font-size:16px;color:var(--txt);outline:none;transition:border-color .2s;width:100%;display:block}
input:focus{border-color:var(--org)}
input[readonly]{color:var(--mut);cursor:default}
.ferr{color:var(--red);font-size:12px;margin-top:4px;display:none}
.btn{display:block;width:100%;padding:15px;border:none;border-radius:12px;font-size:15px;font-weight:700;letter-spacing:.3px;cursor:pointer;transition:filter .15s;margin-top:10px}
.bp{background:var(--org);color:#fff}
.bp:hover{filter:brightness(1.1)}
.bp:disabled{background:var(--bdr);color:var(--mut);cursor:not-allowed;filter:none}
.bs{background:transparent;color:var(--org);border:1.5px solid var(--org)}
.bd{background:var(--red);color:#fff}
.bd:disabled{opacity:.5;cursor:not-allowed}
.sr{display:flex;justify-content:space-between;align-items:center;padding:11px 0;border-bottom:1px solid var(--bdr)}
.sr:last-child{border-bottom:none}
.sl{font-size:14px}.sv{font-size:13px;font-weight:600}
.ok{color:var(--grn)}.wa{color:var(--amb)}.er{color:var(--red)}
.wbox{background:#f9731610;border:1px solid #f9731630;border-radius:12px;padding:14px;font-size:13px;color:#fdba74;line-height:1.7;margin-bottom:14px}
.rbox{border-radius:10px;padding:14px;font-size:14px;margin-top:12px;display:none;font-weight:600}
.rok{background:#16a34a15;border:1px solid #22c55e30;color:var(--grn)}
.rer{background:#dc262615;border:1px solid #ef444430;color:var(--red)}
.smr{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--bdr);font-size:14px}
.smr:last-child{border-bottom:none}
.smv{color:var(--grn);font-weight:600}
.sp{display:inline-block;width:13px;height:13px;border:2px solid #fff4;border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:5px}
@keyframes spin{to{transform:rotate(360deg)}}
.back{display:inline-block;color:var(--mut);font-size:13px;text-decoration:none;cursor:pointer;margin-bottom:6px;padding:4px 0}
.back:hover{color:var(--txt)}
</style></head>
<body><div class="wrap">
<div class="hd">
 <div class="hd-tag">AccidentSOS</div>
 <div class="hd-ttl">Device Setup</div>
 <div class="hd-sub">One-time configuration wizard</div>
</div>
<div class="dots">
 <div class="dot cur" id="d0"></div><div class="dot" id="d1"></div>
 <div class="dot" id="d2"></div><div class="dot" id="d3"></div>
 <div class="dot" id="d4"></div><div class="dot" id="d5"></div>
</div>

<!-- S0: Welcome -->
<div class="scr on" id="s0">
 <div class="card hero">
  <div class="hico">🛡️</div>
  <h2>Welcome</h2>
  <p style="margin:10px 0">Configure your emergency contacts and verify hardware before driving.</p>
  <div class="badge" id="wvid">VEHICLE-001</div>
 </div>
 <button class="btn bp" onclick="go(1)">START SETUP →</button>
</div>

<!-- S1: Vehicle -->
<div class="scr" id="s1">
 <span class="back" onclick="go(0)">← Back</span>
 <div class="card">
  <div class="ctag">Step 1 of 5 · Vehicle</div>
  <h2>Vehicle Details</h2>
  <div style="margin-top:18px">
   <div class="fg">
    <label>Vehicle Name</label>
    <input type="text" id="vn" maxlength="31" placeholder="e.g. My Activa, Family Bolero">
    <div class="ferr" id="vn-e">Please enter a vehicle name.</div>
   </div>
   <div class="fg" style="margin-bottom:0">
    <label>Device ID (read-only)</label>
    <input type="text" id="vid" readonly>
   </div>
  </div>
 </div>
 <button class="btn bp" onclick="stepVehicle()">CONTINUE →</button>
</div>

<!-- S2: Contacts -->
<div class="scr" id="s2">
 <span class="back" onclick="go(1)">← Back</span>
 <div class="card">
  <div class="ctag">Step 2 of 5 · Contacts</div>
  <h2>Emergency Contacts</h2>
  <p style="margin:6px 0 18px">Indian mobile numbers only. Primary contact is required.</p>
  <div class="fg">
   <label>Primary Contact *</label>
   <div class="irow"><span class="pfx">+91</span><input type="tel" id="c1" maxlength="10" placeholder="9XXXXXXXXX" inputmode="numeric"></div>
   <div class="ferr" id="c1-e">Enter a valid 10-digit number starting with 6–9.</div>
  </div>
  <div class="fg">
   <label>Secondary Contact</label>
   <div class="irow"><span class="pfx">+91</span><input type="tel" id="c2" maxlength="10" placeholder="9XXXXXXXXX" inputmode="numeric"></div>
   <div class="ferr" id="c2-e">Enter a valid 10-digit number starting with 6–9.</div>
  </div>
  <div class="fg" style="margin-bottom:0">
   <label>Additional Contact</label>
   <div class="irow"><span class="pfx">+91</span><input type="tel" id="c3" maxlength="10" placeholder="9XXXXXXXXX" inputmode="numeric"></div>
   <div class="ferr" id="c3-e">Enter a valid 10-digit number starting with 6–9.</div>
  </div>
 </div>
 <button class="btn bp" id="s2btn" onclick="stepContacts()">SAVE &amp; CONTINUE →</button>
</div>

<!-- S3: Diagnostics -->
<div class="scr" id="s3">
 <span class="back" onclick="go(2)">← Back</span>
 <div class="card">
  <div class="ctag">Step 3 of 5 · Hardware</div>
  <h2>Device Diagnostics</h2>
  <div style="margin-top:14px">
   <div class="sr"><span class="sl">MPU6050 (Accel/Gyro)</span><span class="sv" id="st-mpu"><span class="wa">…</span></span></div>
   <div class="sr"><span class="sl">GPS Module</span><span class="sv" id="st-gps"><span class="wa">…</span></span></div>
   <div class="sr"><span class="sl">GPS Fix</span><span class="sv" id="st-fix"><span class="wa">…</span></span></div>
   <div class="sr"><span class="sl">SIM Module</span><span class="sv" id="st-sim"><span class="wa">…</span></span></div>
   <div class="sr"><span class="sl">Buzzer</span><span class="sv" id="st-buz"><span class="wa">…</span></span></div>
   <div class="sr"><span class="sl">Battery</span><span class="sv" id="st-bat"><span class="wa">…</span></span></div>
  </div>
 </div>
 <button class="btn bs" onclick="loadStatus()" style="margin-bottom:8px">↻ REFRESH STATUS</button>
 <button class="btn bp" onclick="go(4)">CONTINUE →</button>
</div>

<!-- S4: Test SOS -->
<div class="scr" id="s4">
 <span class="back" onclick="go(3)">← Back</span>
 <div class="card hero" style="padding:26px 22px 18px">
  <div class="hico">🔔</div>
  <div class="ctag" style="margin-top:4px">Step 4 of 5 · Test Alert</div>
  <h2>Send Test Alert</h2>
 </div>
 <div class="card">
  <div class="wbox">⚠️ This sends a <strong>real SMS</strong> to your saved contacts. It is clearly marked as a TEST. No emergency has occurred.</div>
  <p style="font-size:13px;color:var(--mut);margin-bottom:16px">Message sent:<br><em>"[TEST] AccidentSOS device active. No emergency."</em></p>
  <button class="btn bd" id="tb" onclick="doTest()">SEND TEST ALERT</button>
  <div class="rbox rok" id="tok">✓ Test alert sent to your contacts.</div>
  <div class="rbox rer" id="terr">✗ Could not send. Check SIM module and contact numbers.</div>
 </div>
 <button class="btn bs" onclick="go(5)" style="margin-top:8px">SKIP TEST →</button>
 <button class="btn bp" id="tnxt" onclick="go(5)" style="display:none;margin-top:8px">CONTINUE →</button>
</div>

<!-- S5: Complete -->
<div class="scr" id="s5">
 <div class="card hero" style="padding:32px 22px">
  <div class="hico">✅</div>
  <h2>Setup Complete</h2>
  <p style="margin:10px 0">Your AccidentSOS device is ready to protect you.</p>
 </div>
 <div class="card">
  <div class="ctag">Summary</div>
  <div class="smr"><span>Vehicle</span><span class="smv" id="sum-v">—</span></div>
  <div class="smr"><span>Emergency Contacts</span><span class="smv" id="sum-c">—</span></div>
  <div class="smr"><span>MPU6050</span><span class="smv" id="sum-m">—</span></div>
  <div class="smr"><span>SIM Module</span><span class="smv" id="sum-s">—</span></div>
 </div>
 <button class="btn bp" id="fb" onclick="doFinish()">ACTIVATE DEVICE →</button>
 <div class="rbox rok" id="fok" style="margin-top:12px">✓ Device activated. You may disconnect from this Wi-Fi. The device will restart into normal mode.</div>
 <div class="rbox rer" id="ferr" style="margin-top:12px">✗ Could not finalise. Please retry.</div>
</div>

</div><!-- .wrap -->
<script>
var C={vn:'',c1:'',c2:'',c3:''},ST={mpu6050:false,sim:false,battery_pct:100},cur=0;
function go(n){
 document.getElementById('s'+cur).classList.remove('on');
 document.getElementById('s'+n).classList.add('on');
 for(var i=0;i<6;i++){
  var d=document.getElementById('d'+i);
  d.className='dot'+(i<n?' done':i===n?' cur':'');
 }
 cur=n;if(n===3)loadStatus();if(n===5)fillSummary();window.scrollTo(0,0);
}
function load(){
 fetch('/config').then(function(r){return r.json();}).then(function(d){
  var vid=d.device_id||'VEHICLE-001';
  document.getElementById('wvid').textContent=vid;
  document.getElementById('vid').value=vid;
  if(d.vehicle_name){document.getElementById('vn').value=d.vehicle_name;C.vn=d.vehicle_name;}
  function s91(v){return v?(v.startsWith('+91')?v.slice(3):v):'';}
  if(d.emergency_contact_1){document.getElementById('c1').value=s91(d.emergency_contact_1);C.c1=d.emergency_contact_1;}
  if(d.emergency_contact_2){document.getElementById('c2').value=s91(d.emergency_contact_2);C.c2=d.emergency_contact_2;}
  if(d.emergency_contact_3){document.getElementById('c3').value=s91(d.emergency_contact_3);C.c3=d.emergency_contact_3;}
 }).catch(function(){});
}
function ind(n){return/^[6-9]\d{9}$/.test(n);}
function err(id,v){document.getElementById(id).style.display=v?'block':'none';}
function ico(v,y,n){return v?'<span class="ok">'+y+'</span>':'<span class="er">'+n+'</span>';}
function stepVehicle(){
 var v=document.getElementById('vn').value.trim();
 if(!v){err('vn-e',true);return;}err('vn-e',false);C.vn=v;go(2);
}
function stepContacts(){
 var c1=document.getElementById('c1').value.trim();
 var c2=document.getElementById('c2').value.trim();
 var c3=document.getElementById('c3').value.trim();
 var ok=true;
 if(!ind(c1)){err('c1-e',true);ok=false;}else err('c1-e',false);
 if(c2&&!ind(c2)){err('c2-e',true);ok=false;}else err('c2-e',false);
 if(c3&&!ind(c3)){err('c3-e',true);ok=false;}else err('c3-e',false);
 if(!ok)return;
 C.c1='+91'+c1;C.c2=c2?'+91'+c2:'';C.c3=c3?'+91'+c3:'';
 var btn=document.getElementById('s2btn');
 btn.disabled=true;btn.innerHTML='<span class="sp"></span>Saving\u2026';
 fetch('/config',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({vehicle_name:C.vn,emergency_contact_1:C.c1,emergency_contact_2:C.c2,emergency_contact_3:C.c3})
 }).then(function(r){return r.json();}).then(function(d){
  btn.disabled=false;btn.textContent='SAVE & CONTINUE \u2192';
  if(d.status==='success')go(3);else alert('Save failed: '+d.message);
 }).catch(function(){btn.disabled=false;btn.textContent='SAVE & CONTINUE \u2192';alert('Connection error. Ensure you are on ACCIDENT-SOS Wi-Fi.');});
}
function loadStatus(){
 ['mpu','gps','fix','sim','buz','bat'].forEach(function(i){document.getElementById('st-'+i).innerHTML='<span class="wa">\u2026</span>';});
 fetch('/status').then(function(r){return r.json();}).then(function(d){
  ST=d;
  document.getElementById('st-mpu').innerHTML=ico(d.mpu6050,'\u2713 Connected','\u2717 Not found');
  document.getElementById('st-gps').innerHTML=ico(d.gps,'\u2713 Detected','\u2717 Not found');
  document.getElementById('st-fix').innerHTML=d.gps?(d.gps_fix?'<span class="ok">\u2713 Fixed</span>':'<span class="wa">\u29d6 Searching\u2026</span>'):'<span class="er">\u2014</span>';
  document.getElementById('st-sim').innerHTML=ico(d.sim,'\u2713 Connected','\u2717 Not found');
  document.getElementById('st-buz').innerHTML=ico(d.buzzer,'\u2713 Ready','\u2717 Error');
  document.getElementById('st-bat').innerHTML='<span class="ok">'+d.battery_pct+'%</span>';
 }).catch(function(){
  ['mpu','gps','fix','sim','buz','bat'].forEach(function(i){document.getElementById('st-'+i).innerHTML='<span class="er">Error</span>';});
 });
}
function doTest(){
 var btn=document.getElementById('tb');
 btn.disabled=true;btn.innerHTML='<span class="sp"></span>Sending\u2026';
 document.getElementById('tok').style.display='none';document.getElementById('terr').style.display='none';
 fetch('/test-sos',{method:'POST'}).then(function(r){return r.json();}).then(function(d){
  btn.disabled=false;btn.textContent='SEND TEST ALERT';
  if(d.status==='success'){document.getElementById('tok').style.display='block';document.getElementById('tnxt').style.display='block';}
  else document.getElementById('terr').style.display='block';
 }).catch(function(){btn.disabled=false;btn.textContent='SEND TEST ALERT';document.getElementById('terr').style.display='block';});
}
function fillSummary(){
 document.getElementById('sum-v').textContent=C.vn||'\u2014';
 var n=(C.c1?1:0)+(C.c2?1:0)+(C.c3?1:0);
 document.getElementById('sum-c').textContent=n+' configured';
 document.getElementById('sum-m').innerHTML=ico(ST.mpu6050,'\u2713','\u2717');
 document.getElementById('sum-s').innerHTML=ico(ST.sim,'\u2713','\u2717');
}
function doFinish(){
 var btn=document.getElementById('fb');
 btn.disabled=true;btn.innerHTML='<span class="sp"></span>Activating\u2026';
 fetch('/finish-setup',{method:'POST'}).then(function(r){return r.json();}).then(function(d){
  if(d.status==='success'){document.getElementById('fok').style.display='block';btn.style.display='none';}
  else{document.getElementById('ferr').style.display='block';btn.disabled=false;btn.textContent='ACTIVATE DEVICE \u2192';}
 }).catch(function(){document.getElementById('ferr').style.display='block';btn.disabled=false;btn.textContent='ACTIVATE DEVICE \u2192';});
}
load();
</script>
</body></html>)rawliteral";

// ─── Static helpers ───────────────────────────────────────────────────────────
static void sendJSON(int code, const String &body) {
  webServer.sendHeader(F("Cache-Control"), F("no-cache, no-store"));
  webServer.send(code, F("application/json"), body);
}

// Validates an Indian mobile number.
// Accepts: "+91XXXXXXXXXX" or "XXXXXXXXXX" (10 digits, leading digit 6–9).
// Empty string always passes (optional contacts).
static bool validIndianMobile(const char *num) {
  if (!num || num[0] == '\0') return true;  // optional contact — empty OK
  const char *d = num;
  if (strncmp(d, "+91", 3) == 0)      d += 3;
  else if (d[0] == '0')               d += 1;
  if (strlen(d) != 10) return false;
  if (d[0] < '6' || d[0] > '9') return false;
  for (int i = 0; i < 10; i++) if (!isDigit((uint8_t)d[i])) return false;
  return true;
}

// ─── Route handlers ───────────────────────────────────────────────────────────

// GET / — serve the full setup wizard from PROGMEM
static void handleRoot() {
  webServer.send_P(200, PSTR("text/html; charset=utf-8"), SETUP_HTML);
}

// Catch-all for captive-portal detection (Android/iOS connectivity checks).
// Redirecting to http://192.168.4.1 triggers the "Sign in to network" prompt.
static void handleNotFound() {
  webServer.sendHeader(F("Location"), F("http://192.168.4.1"), true);
  webServer.send(302, F("text/plain"), F(""));
}

// GET /status — hardware state snapshot
static void handleStatus() {
  String j;
  j.reserve(140);
  j  = F("{\"configured\":");   j += isConfigured()  ? F("true") : F("false");
  j += F(",\"mpu6050\":");      j += mpuAvailable    ? F("true") : F("false");
  j += F(",\"gps\":false");     // No GPS module in current hardware
  j += F(",\"gps_fix\":false");
  j += F(",\"sim\":");          j += simAvailable    ? F("true") : F("false");
  j += F(",\"buzzer\":true");   // Buzzer has no detection — hardware assumed present
  j += F(",\"battery_pct\":"); j += (int)batteryPct;
  j += F("}");
  sendJSON(200, j);
}

// GET /config — current persisted configuration
static void handleGetConfig() {
  String j;
  j.reserve(200);
  j  = F("{\"device_id\":\"");            j += VEHICLE_ID;
  j += F("\",\"vehicle_name\":\"");       j += deviceConfig.vehicle_name;
  j += F("\",\"emergency_contact_1\":\"");j += deviceConfig.emergency_contact_1;
  j += F("\",\"emergency_contact_2\":\"");j += deviceConfig.emergency_contact_2;
  j += F("\",\"emergency_contact_3\":\"");j += deviceConfig.emergency_contact_3;
  j += F("\",\"configured\":");           j += isConfigured() ? F("true") : F("false");
  j += F("}");
  sendJSON(200, j);
}

// POST /config — validate and save contact configuration
static void handleSaveConfig() {
  if (!webServer.hasArg("plain")) {
    sendJSON(400, F("{\"status\":\"error\",\"message\":\"No body\"}"));
    return;
  }

  JsonDocument doc;
  DeserializationError de = deserializeJson(doc, webServer.arg("plain"));
  if (de) {
    sendJSON(400, F("{\"status\":\"error\",\"message\":\"Invalid JSON\"}"));
    return;
  }

  const char *vn = doc["vehicle_name"]        | "";
  const char *c1 = doc["emergency_contact_1"] | "";
  const char *c2 = doc["emergency_contact_2"] | "";
  const char *c3 = doc["emergency_contact_3"] | "";

  if (vn[0] == '\0') {
    sendJSON(400, F("{\"status\":\"error\",\"message\":\"vehicle_name is required\"}"));
    return;
  }
  if (c1[0] == '\0') {
    sendJSON(400, F("{\"status\":\"error\",\"message\":\"emergency_contact_1 is required\"}"));
    return;
  }
  // Validate all provided numbers (empty optional contacts always pass)
  if (!validIndianMobile(c1) || !validIndianMobile(c2) || !validIndianMobile(c3)) {
    sendJSON(400, F("{\"status\":\"error\",\"message\":\"Invalid Indian mobile number — must be 10 digits starting with 6-9\"}"));
    return;
  }

  // Copy validated values into global config struct
  strncpy(deviceConfig.vehicle_name,        vn, sizeof(deviceConfig.vehicle_name)        - 1);
  deviceConfig.vehicle_name[sizeof(deviceConfig.vehicle_name) - 1] = '\0';

  strncpy(deviceConfig.emergency_contact_1, c1, sizeof(deviceConfig.emergency_contact_1) - 1);
  deviceConfig.emergency_contact_1[sizeof(deviceConfig.emergency_contact_1) - 1] = '\0';

  strncpy(deviceConfig.emergency_contact_2, c2, sizeof(deviceConfig.emergency_contact_2) - 1);
  deviceConfig.emergency_contact_2[sizeof(deviceConfig.emergency_contact_2) - 1] = '\0';

  strncpy(deviceConfig.emergency_contact_3, c3, sizeof(deviceConfig.emergency_contact_3) - 1);
  deviceConfig.emergency_contact_3[sizeof(deviceConfig.emergency_contact_3) - 1] = '\0';

  if (!saveDeviceConfig()) {
    sendJSON(500, F("{\"status\":\"error\",\"message\":\"EEPROM write failed — try again\"}"));
    return;
  }
  sendJSON(200, F("{\"status\":\"success\",\"message\":\"Configuration saved\"}"));
}

// POST /test-sos — trigger test SMS via SIM900A (defined in main .ino)
// IMPORTANT: sendTestSOSMessage() must NOT create a real accident event.
static void handleTestSOS() {
  if (getEmergencyContactCount() == 0) {
    sendJSON(400, F("{\"status\":\"error\",\"message\":\"No contacts configured — save contacts first\"}"));
    return;
  }
  // sendTestSOSMessage() is blocking; may take 30–60 s for multiple contacts.
  bool ok = sendTestSOSMessage();
  if (ok) {
    sendJSON(200, F("{\"status\":\"success\",\"message\":\"Test SOS initiated\"}"));
  } else {
    sendJSON(503, F("{\"status\":\"error\",\"message\":\"Unable to initiate test SOS — check SIM module and cellular signal\"}"));
  }
}

// POST /finish-setup — mark configured, persist, trigger restart
static void handleFinishSetup() {
  if (!validateDeviceConfig(deviceConfig)) {
    sendJSON(400, F("{\"status\":\"error\",\"message\":\"Configuration incomplete — vehicle name and at least one contact required\"}"));
    return;
  }
  deviceConfig.configured = 1;
  if (!saveDeviceConfig()) {
    deviceConfig.configured = 0;   // roll back in-memory flag
    sendJSON(500, F("{\"status\":\"error\",\"message\":\"EEPROM write failed — try again\"}"));
    return;
  }
  sendJSON(200, F("{\"status\":\"success\",\"message\":\"Setup complete\"}"));
  provisioningComplete = true;   // handleProvisioningClient() will restart
}

// ─── Public API ───────────────────────────────────────────────────────────────

// Detects a 5-second boot-hold on GPIO16 (SOS_BUTTON / D0).
// Must be called AFTER pinMode(SOS_BUTTON, INPUT_PULLUP).
// GPIO16 is used instead of GPIO2 (CANCEL_BUTTON / D4) because GPIO2
// is a strapping pin — holding it LOW during boot puts the ESP8266
// into firmware download mode on most NodeMCU boards.
bool isBootHoldForSetup() {
  if (digitalRead(16) != LOW) return false;

  Serial.println(F("BOOT HOLD DETECTED — keep holding SOS button for 5 s..."));
  unsigned long t = millis();
  while (millis() - t < 5000) {
    if (digitalRead(16) != LOW) {
      Serial.println(F("Released early — normal boot"));
      return false;
    }
    delay(50);
  }
  Serial.println(F("BOOT HOLD CONFIRMED — forcing SETUP MODE"));
  return true;
}

void startProvisioningMode(const char *vehicleId) {
  inProvisioningMode   = true;
  provisioningComplete = false;
  provStartMs          = millis();

  String ssid = F("ACCIDENT-SOS-");
  ssid += vehicleId;

  Serial.println();
  Serial.println(F("=============================================="));
  Serial.println(F("PROVISIONING MODE ACTIVE"));
  Serial.print(F("SSID : ")); Serial.println(ssid);
  Serial.println(F("IP   : 192.168.4.1"));
  Serial.println(F("URL  : http://192.168.4.1"));
  Serial.println(F("Connect your phone to this Wi-Fi, then open the URL."));
  Serial.println(F("=============================================="));

  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(PROV_AP_IP, PROV_AP_GW, PROV_AP_SUBNET);
  WiFi.softAP(ssid.c_str());   // Open AP — no password required

  // Captive portal: answer all DNS queries with 192.168.4.1.
  // Triggers "Sign in to Network" on Android/iOS automatically.
  dnsServer.start(PROV_DNS_PORT, "*", PROV_AP_IP);

  webServer.on(F("/"),             HTTP_GET,  handleRoot);
  webServer.on(F("/status"),       HTTP_GET,  handleStatus);
  webServer.on(F("/config"),       HTTP_GET,  handleGetConfig);
  webServer.on(F("/config"),       HTTP_POST, handleSaveConfig);
  webServer.on(F("/test-sos"),     HTTP_POST, handleTestSOS);
  webServer.on(F("/finish-setup"), HTTP_POST, handleFinishSetup);
  webServer.onNotFound(handleNotFound);
  webServer.begin();

  Serial.println(F("HTTP server started on port 80"));
}

// Called every loop() iteration while inProvisioningMode is true.
// Drives DNS, HTTP, timeout, and transition to normal mode.
void handleProvisioningClient() {
  if (!inProvisioningMode) return;

  dnsServer.processNextRequest();
  webServer.handleClient();

  // Auto-reboot after 10-minute idle timeout
  if (millis() - provStartMs > PROV_TIMEOUT_MS) {
    Serial.println(F("PROVISIONING TIMEOUT (10 min) — rebooting"));
    delay(200);
    ESP.restart();
  }

  // Restart into normal mode after successful setup
  if (provisioningComplete) {
    Serial.println(F("PROVISIONING COMPLETE — restarting into normal mode"));
    delay(1800);   // Give the browser time to receive /finish-setup response
    ESP.restart();
  }
}

void stopProvisioningMode() {
  webServer.stop();
  dnsServer.stop();
  WiFi.softAPdisconnect(true);
  inProvisioningMode   = false;
  provisioningComplete = false;
  Serial.println(F("Provisioning mode stopped"));
}
