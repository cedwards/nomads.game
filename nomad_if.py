#!/usr/bin/env python3
# Nomad IF — Utah slice (cleaned build)
# - Seasons/items loaded from YAML with robust parsing
# - Colorized CLI prompt with time, net current, cash, level/XP
# - Hiking: daylight-only, auto-limits near dusk
# - Camping: sleeps to next 06:00, not 24h+
# - EXP system (work, hike, camp, cook, drive)
# - Shop from items.yaml; fallback defaults if YAML missing
# - Weather includes temperature, humidity, UV; solar input scales with UV
# - Safer shop.buy handling (purchased always defined); tent enables dispersed
# - Device toggles and fuel consumption

import yaml
import os, sys, math, json, random
from collections import defaultdict

TURN_MINUTES = 15
DAY_MINUTES  = 24 * 60
SYSTEM_VOLTAGE = 12.0

# ---------------------------- ANSI Colors -----------------------------

class COL:
    RESET = "\033[0m"
    blue  = lambda s: f"\033[34m{s}\033[0m"
    bold  = lambda s: f"\033[1m{s}\033[0m"
    cyan  = lambda s: f"\033[36m{s}\033[0m"
    green = lambda s: f"\033[32m{s}\033[0m"
    grey  = lambda s: f"\033[90m{s}\033[0m"
    prompt= lambda s: f"\033[36m{s}\033[0m"
    red   = lambda s: f"\033[31m{s}\033[0m"
    yellow= lambda s: f"\033[33m{s}\033[0m"

def load_npcs():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "npcs.yaml")
    if not os.path.exists(p): return {}
    import yaml
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    lst = raw.get("npcs", [])
    return {n["id"]: n for n in lst}

def clamp(v, lo, hi): return max(lo, min(hi, v))

def draw_bar(pct, width=20):
    pct = clamp(pct, 0, 1)
    full = int(round(pct*width))
    return "[" + "█"*full + "·"*(width-full) + "]"

def minutes_to_hhmm(total_minutes):
    d = total_minutes // DAY_MINUTES + 1
    m = total_minutes % DAY_MINUTES
    hh = m // 60
    mm = m % 60
    return f"Day {d} {hh:02d}:{mm:02d}"

def is_daylight(total_minutes):
    m = total_minutes % DAY_MINUTES
    return 6*60 <= m < 20*60  # 06:00–20:00

def daylight_sine(total_minutes):
    """0..1 bell centered midday, 0 at night; window 06:00..20:00 mapped to sin(pi*t)"""
    m = total_minutes % DAY_MINUTES
    if m < 360 or m > 1200: return 0.0
    t = (m - 360) / (1200 - 360)
    return max(0.0, math.sin(math.pi * t))

def seeded_rng(*parts):
    seed = 0xABCDEF
    for p in parts:
        seed ^= hash(p) & 0xFFFFFFFF
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
    return random.Random(seed)

# ---------------------------- Archetypes ------------------------------

with open("vehicles.yaml", "r", encoding="utf-8") as f:
    VEHICLES = yaml.safe_load(f)

with open("jobs.yaml", "r", encoding="utf-8") as f:
    JOBS = yaml.safe_load(f)

# ---------------------------- Seasons (YAML) --------------------------

SEASONS = None  # list of tuples: [(name, days, meta), ...]
REF_ELEV_FT = 4000.0
LAPSE_F_PER_KFT = -3.5  # ambient temp lapse vs reference per 1000 ft

def merge_list_of_maps(lst):
    meta = {}
    for item in lst:
        if isinstance(item, dict):
            meta.update(item)
    return meta

def load_seasons():
    """Load seasons from seasons.yaml next to script; robust to odd YAML forms.
    Returns list of (name, days, meta). Falls back to sane defaults."""
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "seasons.yaml")
    default = [
        ("spring", 90, {"uv_peak":7.5, "temp_base":60.0, "diurnal_amp":14.0, "humidity_base":35.0}),
        ("summer",120, {"uv_peak":10.5,"temp_base":88.0, "diurnal_amp":18.0, "humidity_base":25.0}),
        ("autumn", 90, {"uv_peak":6.0, "temp_base":65.0, "diurnal_amp":12.0, "humidity_base":30.0}),
        ("winter", 60, {"uv_peak":3.5, "temp_base":38.0, "diurnal_amp":10.0, "humidity_base":35.0}),
    ]
    if not os.path.exists(p):
        return default
    try:
        import yaml
        with open(p, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            return default
        out = []
        for name in ("spring","summer","autumn","winter"):
            val = raw.get(name)
            if val is None:
                # if missing, use default
                out.append([x for x in default if x[0]==name][0]); continue
            span = None; meta = {}
            if isinstance(val, dict):
                # case A: {'days': 90, 'diurnal_amp':..., ...}
                if 'days' in val:
                    span = int(val.get('days', 90))
                    meta = {k:v for k,v in val.items() if k != 'days'}
                else:
                    # case B: {'90': [ {diurnal_amp:...}, ... ]}  (user's odd style)
                    # or {'90': {'diurnal_amp': ... , ...}}
                    if len(val)==1:
                        k, v = list(val.items())[0]
                        try:
                            span = int(k)
                        except Exception:
                            span = None
                        if isinstance(v, list):
                            meta = merge_list_of_maps(v)
                        elif isinstance(v, dict):
                            meta = dict(v)
            elif isinstance(val, list):
                # case C: list-of-dicts, but days absent → use default span for that season
                meta = merge_list_of_maps(val)
            # fallback span if still unknown
            if span is None:
                span = [x for x in default if x[0]==name][0][1]
            # ensure required keys exist
            dmeta = [x for x in default if x[0]==name][0][2]
            for k, dv in dmeta.items():
                meta.setdefault(k, dv)
            out.append((name, span, meta))
        return out
    except Exception:
        return default

def get_season(total_minutes):
    """Return (season_name, meta) for the current in-game day."""
    global SEASONS
    if SEASONS is None:
        SEASONS = load_seasons()
    total_days = sum(span for _, span, _ in SEASONS)
    day_index = (total_minutes // DAY_MINUTES) % total_days + 1
    acc = 0
    for name, span, meta in SEASONS:
        acc += span
        if day_index <= acc:
            return name, meta
    # fallback
    name, _, meta = SEASONS[-1]
    return name, meta

# ---------------------------- World -----------------------------------

class World:
    def __init__(self, nodes):
        self.nodes = {n['id']: n for n in nodes}
        self._ensure_bidirectional()

    def _ensure_bidirectional(self):
        for nid, node in self.nodes.items():
            for c in node.get('connections', []):
                other = c['to']
                if other not in self.nodes:
                    continue
                back = None
                for bc in self.nodes[other].get('connections', []):
                    if bc['to'] == nid:
                        back = bc; break
                if not back:
                    rev = dict(c); rev['to'] = nid
                    self.nodes[other].setdefault('connections', []).append(rev)

    def find_node(self, key):
        key_l = key.strip().lower()
        if key_l in self.nodes: return key_l
        for nid, n in self.nodes.items():
            if n.get('name','').lower() == key_l: return nid
        for nid, n in self.nodes.items():
            if key_l in nid or key_l in n.get('name','').lower():
                return nid
        return None

# ---- Time windows & helpers ----

def current_time_windows(total_minutes, node):
    m = total_minutes % DAY_MINUTES
    w = derive_weather(node, total_minutes)
    tags = set()
    if 330 <= m <= 450: tags.add("sunrise"); tags.add("golden_hour")
    if 360 <= m <= 480: tags.add("golden_hour")
    if 420 <= m <= 660: tags.add("morning"); tags.add("daylight")
    if 660 < m < 1110: tags.add("daylight")
    if 1110 <= m <= 1200: tags.add("golden_hour"); tags.add("daylight")
    if not (360 <= m < 1200):
        tags.add("night")
        if (not w['monsoon']) and (w['wind'] != 'high') and (not w['flood_watch']):
            tags.add("night_clear")
    return tags, w

def window_multiplier(tag, windows):
    if tag not in windows: return 0.6
    return {"sunrise":1.6,"golden_hour":1.5,"morning":1.15,"daylight":1.0,"night":0.9,"night_clear":1.4}.get(tag,1.0)

# ---------------------------- Weather ---------------------------------

def derive_weather(node, total_minutes):
    """Stochastic-but-seasonal weather with numeric temp/humidity/UV."""
    day = total_minutes // DAY_MINUTES + 1
    rng = seeded_rng(node['id'], day)

    # Season & diurnal
    season_name, meta = get_season(total_minutes)
    uv_peak = float(meta.get("uv_peak", 8.0))
    temp_base = float(meta.get("temp_base", 70.0))
    diurnal_amp = float(meta.get("diurnal_amp", 15.0))
    humidity_base = float(meta.get("humidity_base", 30.0))

    # Wind category
    wind = rng.choices(['low','medium','high'], weights=[4,3,2])[0]

    # Site elevation effect
    elev = float(node.get('elevation_ft', REF_ELEV_FT))
    lapse = (elev - REF_ELEV_FT)/1000.0 * LAPSE_F_PER_KFT

    # Diurnal variation (colder nights, hotter days)
    diel = daylight_sine(total_minutes)  # 0..1
    temp = temp_base + lapse + (diurnal_amp * (diel*2 - 1))  # swing around base
    temp = round(temp, 1)

    # Humidity jitter
    humid = clamp(humidity_base + rng.uniform(-5, 5) - 8*(diel), 5, 95)

    # UV index
    uv = round(uv_peak * diel, 1)

    # Monsoon / flood watch by node rules
    season_rules = " ".join(node.get('season_rules', [])).lower()
    monsoon = ('monsoon' in season_rules) and rng.random() < 0.20
    flood_watch = (('flash_flood' in season_rules) or ('monsoon' in season_rules)) and rng.random() < 0.12

    return {'heat': ('hot' if temp>=85 else 'mild' if temp>=55 else 'cold'),
            'wind': wind, 'monsoon': monsoon, 'flood_watch': flood_watch,
            'temp_f': temp, 'humidity': round(humid,1), 'uv': uv, 'season': season_name}

def weather_speed_mod(w):
    mod = 1.0
    if w['heat'] == 'hot': mod *= 0.95
    if w['wind'] == 'high': mod *= 0.92
    if w['flood_watch']: mod *= 0.90
    return mod

def describe_weather(w):
    base = {'cold':"cold",'mild':"mild",'hot':"hot"}[w['heat']]
    wind = {'low':"light winds",'medium':"breezy",'high':"windy"}[w['wind']]
    extra = []
    if w['monsoon']: extra.append("monsoon cells around")
    if w['flood_watch']: extra.append("flash-flood watch")
    return f"{base}, {wind}, {w['temp_f']}°F, {w['humidity']}% RH, UV {w['uv']}" + ("" if not extra else f" ({', '.join(extra)})")

# ---------------------------- Travel ----------------------------------

BASE_SPEED = {'interstate':65.0,'highway':55.0,'scenic':45.0,'mixed':40.0,'gravel':30.0,'trail':10.0}
GRADE_MOD  = {'flat':1.00,'light':0.95,'moderate':0.85,'mixed':0.90,'steep':0.70}

def edge_drive_turns(world, start_node_id, conn, total_minutes):
    node = world.nodes[start_node_id]
    w = derive_weather(node, total_minutes)
    speed = BASE_SPEED.get(conn.get('road','mixed'), 40.0)
    speed *= GRADE_MOD.get(conn.get('grade','mixed'), 0.90)
    speed *= weather_speed_mod(w)
    speed = max(15.0, speed)
    miles = float(conn.get('miles', 10))
    hours = miles / speed
    turns = max(1, math.ceil(hours * 60 / TURN_MINUTES))
    return turns, w

def dijkstra_route(world, src, dst, total_minutes):
    dist = {nid: math.inf for nid in world.nodes}
    prev = {nid: None for nid in world.nodes}
    dist[src] = 0
    visited = set()
    while True:
        cur, cur_dist = None, math.inf
        for nid, d in dist.items():
            if nid in visited: continue
            if d < cur_dist: cur, cur_dist = nid, d
        if cur is None or cur == dst: break
        visited.add(cur)
        for c in world.nodes[cur].get('connections', []):
            turns, _ = edge_drive_turns(world, cur, c, total_minutes + dist[cur]*TURN_MINUTES)
            nd = dist[cur] + turns
            if nd < dist[c['to']]:
                dist[c['to']] = nd
                prev[c['to']] = (cur, c)
    if dist[dst] == math.inf: return None, None
    path = []
    nid = dst
    while nid != src:
        p = prev[nid]
        if not p: break
        path.append((p[0], nid, p[1]))
        nid = p[0]
    path.reverse()
    return path, dist[dst]

# ---------------------------- Items (YAML) ----------------------------

def load_items_catalog():
    """Load items.yaml Returns dict keyed by item id."""
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "items.yaml")
    catalog = {}
    if os.path.exists(p):
        try:
            import yaml
            with open(p, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            items = raw.get("items") if isinstance(raw, dict) else raw
            if isinstance(items, dict):
                for k, v in items.items():
                    v = dict(v or {})
                    v.setdefault("name", k)
                    v.setdefault("price", 0)
                    v.setdefault("effects", {})
                    v.setdefault("requires", {})
                    catalog[k] = v
        except Exception as e:
            print(COL.red(f"items.yaml load failed: {e}. Using default catalog."))
    if not catalog:
        print("required file missing: items.yaml")
        exit(1)
    return catalog

# ---------------------------- XP / Leveling ---------------------------

def xp_needed_for_level(level):
    # Gentle curve
    if level <= 1: return 0
    return int(100 * (level-1) ** 1.35 + 0.5)

def level_from_xp(xp):
    lvl = 1
    while xp >= xp_needed_for_level(lvl+1):
        lvl += 1
    return lvl

# ---------------------------- Pets ------------------------------------

class Pet:
    def __init__(self, name, breed):
        self.name = name
        self.breed = breed
        self.bond = 30
        self.energy = 70
        self.obedience = 60
        self.paw = 100
        self.alert = 50
        self.guard_mode = False

    def tick(self, minutes):
        self.energy = clamp(self.energy - (minutes/60)*2, 0, 100)

# ---------------------------- Game State ------------------------------

class Game:
    def __init__(self, world, config, catalog, npcs=None):
        self.world = world
        self.location = 'moab' if 'moab' in world.nodes else next(iter(world.nodes.keys()))
        self.minutes = 8*60  # start Day 1 morning

        # Player & role
        self.player_name   = config.get("name", "Traveler")
        self.vehicle_type  = config.get("vehicle_key", "van")
        self.vehicle_color = config.get("color", "white")
        self.job           = config.get("job_key", "photographer")
        self.job_perks     = JOBS.get(self.job, {})
        self.mode          = config.get("mode", "electric")

        # Vehicle archetype
        v = VEHICLES[self.vehicle_type]
        self.water_cap_gallons = v["base_water_cap"]
        self.food_cap_rations = v["base_food_cap"]
        self.max_water_cap    = v["max_water_cap"]
        self.max_food_cap     = v["max_food_cap"]
        self.house_cap        = v["house_cap_factor"]
        self.solar_cap_watts  = v["solar_cap_watts"]
        self.wind_cap_watts   = v["wind_cap_watts"]
        self.house_cap_ah = 100.0 * self.house_cap

        # Upgrades (house systems)
        self.solar_watts = 0.0
        self.wind_watts  = 0.0
        self.has_tent    = False

        # House battery (0–100%)
        self.battery = 75.0

        # Stores
        self.water = min(8.0, self.water_cap_gallons)   # gallons
        self.food  = min(6,   self.food_cap_rations)   # rations

        # Cash & morale/energy
        self.cash   = float(config.get("start_cash", 120.0))
        self.morale = 60.0
        self.energy = 80.0

        # XP
        self.xp = 0
        self.level = 1

        # Pet
        self.pet = None
        self.pet_name = None
        self.pet_type = None

        # Routing
        self.route = None
        self.route_idx = 0

        # EV / Fuel systems
        self.ev_battery   = 80.0  # traction battery %
        self.ev_range_mi  = v["ev_range"]
        self.fuel_gal     = 0.0
        self.mpg          = v["mpg"]
        self.fuel_tank_gal= v["fuel_tank_gal"]
        if self.mode == 'fuel':
            self.fuel_gal = 0.6 * self.fuel_tank_gal  # start with some fuel

        # Dispersed stay tracking
        self.last_camp_node = None
        self.camp_nights_here = 0

        # Work tracking
        self.work_hours_day = -1
        self.work_hours_today = {}
        self.gig_cooldowns = {}

        # Electrical loads
        self.base_draw_amps = 0.8  # standby draw
        self.devices = {
            'camera':        {'owned': False, 'on': False, 'amps': 1.0},
            'heater':        {'owned': False, 'on': False, 'amps': 1.2},
            'fridge':        {'owned': False, 'on': False, 'amps': 2.0},
            'laptop':        {'owned': False, 'on': False, 'amps': 3.0},
            'starlink':      {'owned': False, 'on': False, 'amps': 4.0},
            'stove':         {'owned': False},
            'jetboil':       {'owned': False},
        }
        self.diesel_can_gal = 0.0
        self.propane_lb     = 0.0
        self.butane_can     = 0.0

        # Items catalog
        self.catalog = catalog

        # NPCs
        self.npcs = npcs or {}
        self.npc_state = {}  # per-npc: rep, flags, quest progress

    def report_pet_status(self):
        print(f"Name: {self.pet.name}")
        print(f"Breed: {self.pet.breed}")
        print(f"Bond: {self.pet.bond}")
        print(f"Energy: {self.pet.energy}")
        print(f"Obedience: {self.pet.obedience}")
        print(f"Paw: {self.pet.paw}")
        print(f"Alert: {self.pet.alert}")
        print(f"Guard Mode: {self.pet.guard_mode}")

    def report_morale(self):
        print(f"Your morale is: {self.morale:.0f}")

    def report_energy(self):
        print(f"Your energy is: {self.energy:.0f}")

    def _parse_hhmm(self, s):
        h,m = s.split(":"); return int(h)*60 + int(m)

    def _is_weekend(self):
        day_idx = (self.minutes // DAY_MINUTES) % 7  # 0..6
        return day_idx in (5,6)
    
    def npcs_here_now(self):
        """Return list of NPC dicts present at current node and time/season."""
        here = self.location
        m = self.minutes % DAY_MINUTES
        season, _meta = get_season(self.minutes)
        present = []
        for npc in self.npcs.values():
            for slot in npc.get("presence", []):
                if slot.get("at") != here: continue
                when = (slot.get("when") or "daily").lower()
                if when == "weekday" and self._is_weekend(): continue
                if when == "weekend" and not self._is_weekend(): continue
                if when == "season":
                    seasons = [s.lower() for s in slot.get("seasons",[])]
                    if season not in seasons: continue
                # hour window
                hh = slot.get("hours", "00:00-23:59")
                start, end = [self._parse_hhmm(x) for x in hh.split("-")]
                if not (start <= m <= end): continue
                present.append(npc); break
        return present


    def _check_for_truck_camper(self):
        if self.vehicle_type == 'truck_camper':
            self.adopt_pet()
        else:
            return

    def read_book(self):
        print(COL.grey(f"You read another chapter in your latest book."))
        xp = clamp(self.xp + 10, 0, 10)
        self.advance(30)
        self.add_xp(int(xp), "self care")

    def watch_something(self, something):
        print(COL.grey(f"You watch {something}. Spirits lift."))
        xp = clamp(self.xp + 10, 0, 15)
        self.advance(30)
        self.add_xp(int(xp), "self care")

    def battery_status(self):
        battery = self.battery
        solar_w = self._solar_input_watts_now()
        wind_w  = self._wind_input_watts_now()
        solar_a = solar_w / SYSTEM_VOLTAGE
        wind_a  = wind_w  / SYSTEM_VOLTAGE
        load_a  = self._load_amps_now()
        net_a   = (solar_a + wind_a) - load_a
        print(COL.grey(f" Load: {load_a:.1f}A"))
        print(COL.grey(f" Battery: {battery:.0f}%"))
        print(COL.grey(f" Capacity: {self.house_cap_ah:.0f}Ah"))
        if battery == 0:
            print(COL.red(f" Remaining: 0 hours"))
        elif net_a < 0:
            print(COL.yellow(f" Remaining: {self.house_cap_ah / self._load_amps_now():.2f} hours"))
        elif net_a > 0:
            print(COL.green(f" Remaining: infinite"))

    def report_time(self):
        t = minutes_to_hhmm(self.minutes)
        print(COL.grey(f"{t}"))

    def fuel_status(self):
        if self.mode == 'electric':
            print(COL.red("You don't have a fuel-based vehicle"))
            return
        else:
            print(COL.grey(f"Fuel Status:{self.fuel_gal}G"))
            print(COL.grey(f"Fuel MPG:   {self.mpg} mpg"))
            print(COL.grey(f"Fuel Tank:  {self.fuel_tank_gal} gallons"))

    def ev_status(self):
        if self.mode == 'fuel':
            print(COL.red("You don't have an electric vehicle"))
            return
        else:
            print(COL.grey(f"EV Battery: {self.ev_battery}%"))
            print(COL.grey(f"EV Range: {self.ev_range_mi} miles"))

    def solar_power_status(self):
        solar_current = self._solar_input_watts_now() / SYSTEM_VOLTAGE
        print(COL.grey(f"Solar Input: {self._solar_input_watts_now():.0f}W"))
        print(COL.grey(f"Solar Current: {solar_current:.2f}A"))
        print(COL.grey(f"Current Capacity: {self.solar_watts:.0f}W"))
        print(COL.grey(f"Vehicle Capacity: {self.solar_cap_watts:.0f}W"))

    def wind_power_status(self):
        wind_current = self._wind_input_watts_now() / SYSTEM_VOLTAGE
        print(COL.grey(f"Wind Input: {self._wind_input_watts_now():.0f}W"))
        print(COL.grey(f"Wind Current: {wind_current:.2f}A"))
        print(COL.grey(f"Current Capacity: {self.wind_watts:.0f}W"))
        print(COL.grey(f"Vehicle Capacity: {self.wind_cap_watts:.0f}W"))

    def bank(self):
        print(COL.green(f"You have ${self.cash:.0f} dollars"))

    def inventory(self):
        water_cap = self.water_cap_gallons
        food_cap = self.food_cap_rations
        if self.food >= 0:
            print(COL.grey(f"Food: {self.food:.0f}/{food_cap} meals"))
        if self.water >= 0:
            print(COL.grey(f"Water: {self.water:.2f}/{water_cap} gallons"))
        if self.propane_lb >= 0:
            print(COL.grey(f"Propane: {self.propane_lb:.2f} lbs"))
        if self.butane_can >= 0:
            print(COL.grey(f"Butane: {self.butane_can:.2f} canisters"))

    def elevation(self):
        elev_ft = self.node().get('elevation_ft','?')
        elev_m  = elev_ft / 3.281
        print(COL.grey(f"Elevation: {elev_ft:.0f} ft / {elev_m:.0f} meters above sea level"))

    def exp(self):
        print(COL.grey(f"Level: {self.level} | Experience: {self.xp} | Needed: {xp_needed_for_level(self.level+1)-self.xp}"))


    def people(self):
        crew = self.npcs_here_now()
        if not crew:
            print(COL.grey("No one around right now.")); return
        print("People here:")
        for npc in crew:
            print(COL.blue(f"  - {npc['name']} — {npc.get('title','')} [{npc['id']}]"))

    def talk(self, who):
        who = (who or "").lower()
        npc = next((n for n in self.npcs_here_now() if n["id"]==who or n["name"].lower()==who), None)
        if not npc:
            print(COL.yellow("They're not here.")); return
        greet = npc.get("dialogue", {}).get("greeting", ["They nod."])
        print(random.choice(greet))
        topics = list((npc.get("dialogue", {}).get("topics") or {}).keys())
        if topics:
            print("Topics:", ", ".join(topics))
        if "shop" in npc:
            print("Hint: TRADE", npc["id"])
        if npc.get("quests"):
            print("Hint: ASK", npc["id"], "ABOUT quests")

    def ask(self, who, topic):
        who = (who or "").lower(); topic = (topic or "").lower()
        npc = next((n for n in self.npcs_here_now() if n["id"]==who or n["name"].lower()==who), None)
        if not npc:
            print(COL.yellow("They're not here.")); return
        topics = (npc.get("dialogue", {}).get("topics") or {})
        lines = topics.get(topic)
        if not lines:
            if topic in ("quest","quests") and npc.get("quests"):
                print(COL.grey("Available quests:", ", ".join(q["id"] for q in npc["quests"])));
            else:
                print(COL.grey("They shrug."))
            return
        print(random.choice(lines))
        # micro-hooks: grant a gig, flag a tip, etc. (later)

    def trade(self, who):
        who = (who or "").lower()
        npc = next((n for n in self.npcs_here_now() if n["id"]==who or n["name"].lower()==who), None)
        if not npc or "shop" not in npc:
            print("No trading with them."); return
        inv = npc["shop"].get("inventory", [])
        mult = float(npc["shop"].get("price_mult", 1.0))
        print(f"{npc['name']}'s pack — BUY <item> [qty]")
        for item_id in inv:
            item = self.catalog.get(item_id)
            if not item: continue
            price = int(round(item.get("price",0) * mult))
            print(f"  {item_id:<12} ${price:<5} — {item.get('name', item_id)}")
        print(f"Cash: ${self.cash:.0f}")

    def _pct_per_ah(self):
        # how many percentage points is 1Ah
        return 100.0 / max(1.0, self.house_cap_ah)

    # ------------------ UI helpers ------------------
    def rig_level(self):
        score = (self.solar_watts/100.0) + (self.wind_watts/100.0)
        score += (self.water_cap_gallons - 50)/10.0
        score += (self.food_cap_rations - 12)/5.0
        score += 2 if self.has_tent else 0
        return max(1, min(10, int(1 + score/3)))

    def compute_current(self):
        solar_w = self._solar_input_watts_now()
        wind_w  = self._wind_input_watts_now()
        solar_a = solar_w / SYSTEM_VOLTAGE
        wind_a  = wind_w  / SYSTEM_VOLTAGE
        load_a  = self._load_amps_now()
        net_a   = (solar_a + wind_a) - load_a
        return (net_a, solar_a, wind_a, load_a)

    def electrical_panel(self):
        battery = self.battery
        solar_w = self._solar_input_watts_now()
        wind_w  = self._wind_input_watts_now()
        solar_a = solar_w / SYSTEM_VOLTAGE
        wind_a  = wind_w  / SYSTEM_VOLTAGE
        load_a  = self._load_amps_now()
        net_a   = (solar_a + wind_a) - load_a
        print(COL.grey(f" Solar: {solar_w:.0f}W | {solar_a:.1f}A"))
        print(COL.grey(f" Wind: {wind_w:.0f}W | {wind_a:.1f}A"))
        print(COL.grey(f" Load: {load_a:.1f}A"))
        print(COL.grey(f" Net: {net_a:.1f}A"))
        print(COL.grey(f" Battery: {battery:.0f}%"))
        print(COL.grey(f" Capacity: {self.house_cap_ah:.0f}Ah"))
        if battery == 0:
            print(COL.red(f" Remaining: 0 hours"))
        elif net_a < 0:
            print(COL.yellow(f" Remaining: {self.house_cap_ah / self._load_amps_now():.2f} hours"))
        elif net_a > 0:
            print(COL.green(f" Remaining: infinite"))
        print(COL.grey(f" EV Battery: {self.ev_battery:.0f}%"))
        print(COL.grey(f" EV Range: {self.ev_range_mi:.0f} miles"))

    def _solar_input_watts_now(self):
        node = self.node()
        sol = (node.get('resources', {}) or {}).get('solar', 'fair')
        site = {'excellent':1.0,'good':0.75,'fair':0.5,'poor':0.25}.get(sol, 0.5)
        if self.solar_watts <= 0: return 0.0
        w = derive_weather(node, self.minutes)
        # Scale by UV (0..uv_peak) normalized to peak
        uv_norm = clamp(w['uv'] / max(1e-6, float(get_season(self.minutes)[1].get('uv_peak', 8.0))), 0, 1)
        return self.solar_watts * site * uv_norm

    def _wind_input_watts_now(self):
        if self.wind_watts <= 0: return 0.0
        w = derive_weather(self.node(), self.minutes)
        frac = {'low':0.2,'medium':0.6,'high':1.0}[w['wind']]
        return self.wind_watts * frac

    def _load_amps_now(self):
        amps = self.base_draw_amps
        if self.devices['fridge']['owned'] and self.devices['fridge']['on']:
            amps += self.devices['fridge']['amps']
        if self.devices['starlink']['owned'] and self.devices['starlink']['on']:
            amps += self.devices['starlink']['amps']
        if self.devices['laptop']['owned'] and self.devices['laptop']['on']:
            amps += self.devices['laptop']['amps']
        if self.devices['heater']['owned'] and self.devices['heater']['on']:
            if self.diesel_can_gal > 0:
                amps += self.devices['heater']['amps']
            else:
                self.devices['heater']['on'] = False
        return amps

    def node(self):
        return self.world.nodes[self.location]

    # ------------------ XP helpers ------------------
    def add_xp(self, amount, reason=""):
        amount = max(0, int(round(amount)))
        if amount <= 0: return
        prev_level = self.level
        self.xp += amount
        self.level = level_from_xp(self.xp)
        msg = f"+{amount} XP"
        if reason: msg += f" ({reason})"
        if self.level > prev_level:
            print(COL.bold(f"{msg} → Level up! You are now Lv{self.level}."))
        else:
            print(COL.green(msg))

    # ------------------ Devices ------------------
    def devices_panel(self):
        print("Devices:")
        for k in ('fridge','starlink','heater','stove','jetboil', 'laptop'):
            d = self.devices[k]
            owned = d.get('owned', False)
            on    = d.get('on', False)
            amps  = d.get('amps', 0)
            if not owned:
                print(f"  - {k}: not installed")
            else:
                if 'on' in d:
                    print(f"  - {k}: {'ON ' if on else 'off'}  (~{amps}A when on)")
                else:
                    print(f"  - {k}: installed (uses fuel when cooking)")

    def toggle_device(self, name, state):
        name = (name or '').lower()
        if name not in self.devices:
            print(COL.yellow("Unknown device. Try: fridge, starlink, heater, stove, jetboil")); return
        d = self.devices[name]
        if not d.get('owned', False):
            print("You don't own that device."); return
        if 'on' not in d:
            print(COL.yellow(f"{name} has no on/off; it only consumes fuel when cooking.")); return
        on = True if state.lower() in ('on','true','1') else False
        if name == 'heater' and on and self.diesel_can_gal <= 0:
            print("No diesel in the can. BUY diesel_can <gallons> first."); return
        d['on'] = on
        print(COL.green(f"{name} set to {'ON' if on else 'off'}."))

    # ------------------ Time advance ------------------
    def advance(self, minutes):
        for _ in range(max(1, minutes // TURN_MINUTES)):
            net_a, solar_a, wind_a, load_a = self.compute_current()
            delta_ah  = net_a * (TURN_MINUTES/60.0)
            cap_ah    = max(1.0, self.house_cap_ah)
            delta_pct = (delta_ah / cap_ah) * 100.0
            self.battery = clamp(self.battery + delta_pct, 0, 100)

            # Diesel heater fuel
            if self.devices['heater']['owned'] and self.devices['heater']['on']:
                burn = 0.15 * (TURN_MINUTES/60.0)
                if self.diesel_can_gal >= burn: self.diesel_can_gal -= burn
                else: self.diesel_can_gal = 0.0; self.devices['heater']['on'] = False

            self.minutes += TURN_MINUTES
            self.water  = clamp(self.water - 0.03, 0, self.water_cap_gallons)
            self.energy = clamp(self.energy - 0.8, 0, 100)
            if self.pet: self.pet.tick(TURN_MINUTES)

            if self.mode == 'electric':
                if is_daylight(self.minutes) and self.solar_watts > 0:
                    node = self.node()
                    site = {'excellent':1.0,'good':0.75,'fair':0.5,'poor':0.25}.get((node.get('resources',{}) or {}).get('solar','fair'),0.5)
                    uv_norm = clamp(derive_weather(node, self.minutes)['uv'] / max(1.0, get_season(self.minutes)[1].get('uv_peak', 8.0)), 0, 1)
                    self.ev_battery = clamp(self.ev_battery + (self.solar_watts/1000.0)*4.0*site*uv_norm/4.0, 0, 100)
                if self.wind_watts > 0:
                    w = derive_weather(self.node(), self.minutes)
                    ev_level = {'low':0.2,'medium':0.6,'high':1.0}[w['wind']]
                    self.ev_battery = clamp(self.ev_battery + (self.wind_watts/300.0)*ev_level/4.0, 0, 100)

    # ------------------ Actions ------------------
    def print_hud(self):
        netA, pvA, windA, loadA = self.compute_current()
        mode_line = (f"EV {self.ev_battery:.0f}%" if self.mode=='electric'
                     else f"Fuel {self.fuel_gal:.1f} gal")
        print(COL.grey(f"Power Current {netA:+.1f}A (PV {pvA:.1f}, Wind {windA:.1f}, Load {loadA:.1f})  {mode_line}"))
        print(COL.grey(f"Stores H₂O {self.water:.1f}/{self.water_cap_gallons:.0f}G  Food {self.food}/{self.food_cap_rations}  Cash ${self.cash:.0f}  Rig L{self.rig_level()}  Lv{self.level} ({self.xp} XP)"))

    def look(self):
        n = self.node()
        w = derive_weather(n, self.minutes)
        biome = n.get('biome','').replace('_',' ')
        elev = n.get('elevation_ft','?')
        print()
        #print(f"You are at {n['name']}. {biome} at {elev} ft.")
        # intentionally no bar HUD (per your earlier preference)
        desc = n.get('description')
        ansi = n.get('ansi')
        if desc: print(COL.green(desc))
        input(COL.blue("Press ENTER to continue..."))
        if ansi: 
            with open(ansi, "r", encoding="utf-8") as f: 
                ansi_content = f.read()
                print(ansi_content)
        #print(f"Time: {minutes_to_hhmm(self.minutes)}")
        print(COL.grey(f"Weather: {describe_weather(w)}."))
        #print(f"Resources — water: {n['resources'].get('water','?')}, "
              #f"food: {n['resources'].get('food','?')}, "
              #f"solar: {n['resources'].get('solar','?')}, "
        print(COL.grey(f"wind: {n['resources'].get('wind','?')}."))
        crew = self.npcs_here_now()
        if crew:
            print("Also here:", ", ".join(f"{n['name']} ({n.get('title','')})" for n in crew))
        if n.get('pet_adoption') and not self.pet and not self.vehicle_type == 'truck_camper': print("You spot a rescue meetup. You could ADOPT PET here.")
        if self.pet: 
            comp = random.choice(["companion","pet","partner","ride-or-die","best friend","constant shadow"])
            action = random.choice(["carefully watches the horizon","shuffles around the cab","raises their head briefly and goes back to sleep","barks at something unseen","whines about being fed","jumps down from the passenger seat","jumps into the passenger seat"])
            print(COL.green(f"\nYour {comp} {self.pet.name} {action}. Bond {int(self.pet.bond)}%. Energy {int(self.pet.energy)}%."))

    def status(self):
        print(COL.grey(f"{self.player_name} — {self.vehicle_color.title()} {VEHICLES[self.vehicle_type]['label']} | Job: {JOBS[self.job]['label']}"))
        print(COL.grey(f"Location: {self.node()['name']} | {minutes_to_hhmm(self.minutes)}"))
        self.print_hud()

    def show_map(self):
        n = self.node()
        print(COL.grey(f"From {n['name']} you can reach:"))
        for c in n.get('connections', []):
            other = self.world.nodes[c['to']]
            print(COL.grey(f"  - {other['name']} ({c.get('road','?')}, {c.get('miles','?')} mi, grade {c.get('grade','mixed')})"))
        print(COL.grey("Use: ROUTE TO <place>"))

    def route_to(self, dest_key):
        nid = self.world.find_node(dest_key)
        if not nid: print("I don't recognize that destination."); return
        if nid == self.location: print(COL.yellow("You're already here.")); return
        path, total_turns = dijkstra_route(self.world, self.location, nid, self.minutes)
        if not path: print(COL.red("No route found.")); return
        self.route = path; self.route_idx = 0
        hours = total_turns * TURN_MINUTES / 60
        names = " → ".join(self.world.nodes[a]['name'] for a,_,_ in path) + f" → {self.world.nodes[nid]['name']}"
        print(COL.grey(f"Route plotted ({hours:.1f}h est): {names}"))
        print(COL.grey("Use: DRIVE to set off."))

    def drive(self):
        if not self.route: print(COL.red("No route plotted. Use: ROUTE TO <place>")); return
        if self.route_idx >= len(self.route): print(COL.yellow("Route already complete.")); return
        frm, to, conn = self.route[self.route_idx]
        turns, w = edge_drive_turns(self.world, frm, conn, self.minutes)
        hours = turns * TURN_MINUTES / 60.0
        miles = float(conn.get('miles', 10))
        # Energy check
        if self.mode == 'electric':
            needed_pct = (miles / max(1.0, self.ev_range_mi)) * 100.0
            if self.ev_battery < needed_pct:
                print(COL.red(f"Not enough charge for {miles:.0f} mi. Need ~{needed_pct:.1f}% EV; have {self.ev_battery:.1f}%."))
                print(COL.yellow("Try: CHARGE station (Moab), CHARGE solar, or CHARGE wind.")); return
            self.ev_battery = clamp(self.ev_battery - needed_pct, 0, 100)
        else:
            needed_gal = miles / max(1.0, self.mpg)
            if self.fuel_gal < needed_gal:
                print(COL.red(f"Not enough fuel for {miles:.0f} mi. Need ~{needed_gal:.1f} gal; have {self.fuel_gal:.1f}."))
                print(COL.yellow("Try: REFUEL in Moab or adjust your route.")); return
            self.fuel_gal = max(0.0, self.fuel_gal - needed_gal)
            self.battery = clamp(self.battery + (2.0*hours)/self._pct_per_ah(), 0, 100)
        # Travel drains
        self.water  = clamp(self.water - 0.1*hours, 0, self.water_cap_gallons)
        self.energy = clamp(self.energy - 6.0*hours, 0, 100)
        if self.pet:
            self.pet.energy = clamp(self.pet.energy - 4.0*hours, 0, 100)
            self.pet.alert  = clamp(self.pet.alert + 5.0, 0, 100)
        # Detour chance
        rng = seeded_rng(frm, to, int(self.minutes/60))
        if rng.random() < 0.06:
            delay = rng.randint(1,3)
            print(COL.yellow(f"A detour slows you down (+{delay} turns).")); turns += delay; hours = turns * TURN_MINUTES / 60.0
        self.advance(turns*TURN_MINUTES)
        self.location = to
        self.route_idx += 1
        print(COL.grey(f"You arrive at {self.node()['name']} after {hours:.1f}h and {miles:.0f} mi. Weather en route: {describe_weather(w)}."))
        if self.route_idx >= len(self.route): print(COL.grey("Route complete."))
        # XP: reward per mile & road difficulty
        road = conn.get('road','mixed'); grade = conn.get('grade','mixed')
        xp = miles * {'interstate':0.25,'highway':0.3,'scenic':0.4,'mixed':0.35,'gravel':0.6,'trail':1.0}.get(road,0.3)
        xp *= {'flat':1.0,'light':1.05,'moderate':1.15,'mixed':1.1,'steep':1.3}.get(grade,1.0)
        self.add_xp(int(xp), "driving")

    def check_weather(self):
        w = derive_weather(self.node(), self.minutes)
        daylight = "daylight" if is_daylight(self.minutes) else "night"
        print(COL.grey(f"At {self.node()['name']} ({daylight}): {describe_weather(w)}."))

    def camp(self, style):
        style = (style or '').lower()
        if style not in ('stealth','paid','dispersed'):
            print(COL.yellow("CAMP how? Options: stealth | paid | dispersed")); return
        # Sleep until next 06:00 (not 24h+)
        now = self.minutes % DAY_MINUTES
        if now <= 6*60: sleep_minutes = 6*60 - now
        else: sleep_minutes = (24*60 - now) + 6*60
        hours = sleep_minutes / 60.0

        # Weather for wind bonus
        w = derive_weather(self.node(), self.minutes)
        wind_level = {'low':0.0,'medium':0.8,'high':1.5}[w['wind']]
        wind_scale = (self.wind_watts / 300.0) if self.wind_watts > 0 else 0.2
        wind_bonus = wind_level * wind_scale  # % per hour to HOUSE battery (applied by advance anyway)

        # Base gains/risks
        if style == 'paid':
            energy_gain, morale_gain, pet_energy, pet_bond = 20, 10, 18, 2
            ranger_knock = 0.01; note = "Paid site: services, permits, quiet-ish."
        elif style == 'stealth':
            energy_gain, morale_gain, pet_energy, pet_bond = 15, 6, 14, 2
            ranger_knock = 0.08; note = "Stealth spot: close to town, but keep it low-key."
            if self.node().get('pet_rules') == 'strict': ranger_knock += 0.06
            if self.pet and self.pet.alert > 60:         ranger_knock += 0.04
        else:  # dispersed
            energy_gain, morale_gain, pet_energy, pet_bond = 23, 12, 20, 3
            if self.has_tent: energy_gain += 4; morale_gain += 3; pet_energy += 3; note = "Dispersed with tent: free, solitary, and cozy under the stars."
            else: note = "Dispersed site: free, solitary, sky for days."
            in_park = self.location in {'zion','bryce','arches','canyonlands','capitol_reef'}
            ranger_knock = 0.04 if in_park else 0.005

        # Apply overnight effects (before time advance)
        self.water   = clamp(self.water - 0.08*hours, 0, self.water_cap_gallons)
        self.food    = max(0, self.food - 1)
        self.energy  = clamp(self.energy + energy_gain, 0, 100)
        self.morale  = clamp(self.morale + morale_gain, 0, 100)
        if self.pet:
            self.pet.energy = clamp(self.pet.energy + pet_energy, 0, 100)
            self.pet.bond   = clamp(self.pet.bond   + pet_bond, 0, 100)

        # Events
        if style == 'dispersed':
            biome = (self.node().get('biome') or '').lower()
            maybe_remote = any(k in biome for k in ['desert','swell','salt','mesa','canyon'])
            rng_sig = seeded_rng(self.location, int(self.minutes/60), 'signal')
            has_signal = not (maybe_remote and rng_sig.random() < 0.6)
            if not has_signal: print(COL.yellow("No bars out here. Your phone becomes a very expensive paperweight tonight."))
            inc = self.job_perks.get('remote_camp_income', 0)
            if inc and has_signal:
                self.cash += inc; print(COL.green(f"You push a little code under the stars (+${inc})."))
        rng = seeded_rng(self.location, int(self.minutes/60), style)
        if rng.random() < ranger_knock:
            print(COL.yellow("A flashlight sweeps your curtains. A ranger checks on you."))
            if style == 'paid': print(COL.green("Your permit checks out. You roll over and go back to sleep."))
            elif style == 'dispersed': print(COL.yellow("Friendly reminder about tread-lightly and stay limits. You chat stars and keep it mellow."))
            else: self.cash = max(0, self.cash - 25); self.morale = clamp(self.morale - 6, 0, 100); print(COL.yellow("You get a warning and a $25 fine. Morale dips."))

        self.advance(sleep_minutes)
        print(COL.grey(f"{note} You camp {style} for {hours:.1f}h. Morning at {minutes_to_hhmm(self.minutes)}. Battery {int(self.battery)}%."))
        # XP
        self.add_xp({'paid':10,'stealth':15,'dispersed':18}[style], f"camp ({style})")

    def cook(self):
        if self.food <= 0: print(COL.red("You rummage for crumbs. No food to cook.")); return
        used = "cold"
        if self.devices['stove']['owned'] and self.propane_lb >= 0.2:
            self.propane_lb -= 0.2; used = "stove"
        elif self.devices['jetboil']['owned'] and self.butane_can >= 0.25:
            self.butane_can -= 0.25; used = "jetboil"
        else:
            used = "pan + inverter"
        use_water = 0.5 if self.water >= 0.5 else 0.0
        self.food -= 1
        self.water = clamp(self.water - use_water, 0, self.water_cap_gallons)
        morale_boost = 9 if used in ("stove","jetboil") else 6
        self.morale = clamp(self.morale + morale_boost, 0, 100)
        self.energy = clamp(self.energy + 6, 0, 100)
        self.advance(TURN_MINUTES)
        print(COL.grey(f"You cook with {used} (+morale, +energy). Water used: {use_water:.1f}G."))
        self.add_xp(5 if used != "cold" else 3, "cooking")

    def sleep(self):
        self.advance(120)
        self.energy = clamp(self.energy + 20, 0, 100)
        if self.pet: self.pet.energy = clamp(self.pet.energy + 10, 0, 100)
        print(COL.grey(f"You nap for 2h. It's now {minutes_to_hhmm(self.minutes)}."))

    def hike(self):
        # Daylight-only hiking; auto-limit to dusk
        m = self.minutes % DAY_MINUTES
        if not (6*60 <= m < 18*60) and self.job != 'trail_guide':
            print(COL.yellow("It’s not safe to start a hike right now. Try between 06:00 and 18:00.")); return
        base_hours = random.randint(1,5)
        node = self.node()
        hours = max(1.0, round(base_hours, 1))
        # Trim so we don't go past dusk (18:00; a little cushion)
        minutes_left = (18*60) - m
        hours = min(hours, max(1.0, minutes_left/60.0))
        ticks = int((hours * 60) // TURN_MINUTES) or 1
        print(COL.grey(f"You set out on a ~{hours:.1f}h hike."))
        found = False
        windows, _w0 = current_time_windows(self.minutes, node)
        for _ in range(ticks):
            if self.mode == 'electric' and self.solar_watts > 0 and is_daylight(self.minutes):
                sol_quality = (node.get('resources', {}) or {}).get('solar', 'fair')
                site = {'excellent':1.0,'good':0.75,'fair':0.5,'poor':0.25}.get(sol_quality, 0.5)
                uv_norm = clamp(derive_weather(node, self.minutes)['uv'] / max(1.0, get_season(self.minutes)[1].get('uv_peak', 8.0)), 0, 1)
                self.ev_battery = clamp(self.ev_battery + (self.solar_watts / 1000.0) * 4.0 * site * uv_norm / 4.0, 0, 100)
            if self.wind_watts > 0:
                w = derive_weather(node, self.minutes)
                house_level = {'low':0.0, 'medium':0.8, 'high':1.5}[w['wind']]
                ev_level    = {'low':0.2, 'medium':0.6, 'high':1.0}[w['wind']]
                self.battery   = clamp(self.battery   + (self.wind_watts / 300.0) * house_level / 4.0 / self._pct_per_ah(), 0, 100)
                if self.mode=='electric':
                    self.ev_battery = clamp(self.ev_battery + (self.wind_watts / 300.0) * ev_level / 4.0, 0, 100)
            self.advance(TURN_MINUTES)
            if not found and random.random() < 0.08:
                found = True; self.morale = clamp(self.morale + 4, 0, 100); print(COL.green("You crest a ridge to a ridiculous view. Morale soars."))
        extra_energy = min(12, int(hours * 3))
        extra_water  = round(0.12 * hours, 2)
        mult = self.job_perks.get('hike_energy_mult', 1.0)
        self.energy = clamp(self.energy - int(extra_energy * mult), 0, 100)
        self.water  = clamp(self.water  - extra_water, 0, self.water_cap_gallons)
        if self.pet:
            self.pet.energy = clamp(self.pet.energy - max(6, int(hours * 2)), 0, 100)
            self.pet.bond   = clamp(self.pet.bond + 2, 0, 100)
        print(COL.grey(f"You return after ~{hours:.1f}h. Battery {int(self.battery)}% | "
              f"{'EV ' + str(int(self.ev_battery)) + '%' if self.mode=='electric' else 'Fuel ' + f'{self.fuel_gal:.1f} gal'} | "
              f"Water {self.water:.1f}G | Energy {int(self.energy)}."))
        # XP: hikes worth a solid chunk
        w_now = derive_weather(node, self.minutes)
        diff = 1.0 + (0.15 if w_now['wind']=='high' else 0) + (0.10 if w_now['heat']=='hot' else 0)
        if self.job == 'trail_guide': diff *= 1.10
        self.add_xp(int(hours*10*diff), "hiking")

    def work(self, kind='', hours=None):
        node = self.node()
        kind = (kind or '').lower().strip()
        if not kind or kind == 'job':
            jk = self.job
            kind = {'photographer':'photo','remote_dev':'dev','mechanic':'mechanic','trail_guide':'guide','artist':'artist'}.get(jk, 'photo')
        if hours is None:
            hours = random.randint(1,4)
        try: hours = float(hours)
        except Exception: hours = 2.0
        hours = max(1.0, min(6.0, hours))
        ticks = int((hours*60) // TURN_MINUTES) or 1

        today = self.minutes // DAY_MINUTES
        if self.work_hours_day != today: self.work_hours_day = today; self.work_hours_today = {}

        windows, cur_weather = current_time_windows(self.minutes, node)
        biome = (node.get('biome') or '').lower()
        photogenic = 1.0
        if any(k in biome for k in ['arches','canyon']): photogenic = 1.35
        if 'desert' in biome: photogenic = max(photogenic, 1.25)
        if 'salt' in biome: photogenic = max(photogenic, 1.30)
        if 'alpine' in biome: photogenic = max(photogenic, 1.15)
        in_moab = (self.location == 'moab')

        base = 18.0; tip_mult = 1.0
        fail_prereq = None

        if kind == 'photo':
            base = 22.0 * photogenic
            peak = max(window_multiplier("golden_hour", windows), window_multiplier("sunrise", windows), window_multiplier("night_clear", windows))
            tip_mult *= peak
        elif kind == 'dev':
            # signal heuristic (use starlink as override)
            has_signal = any(t in windows for t in ('daylight','night'))  # time doesn't matter; use node+daily roll
            # crude per-node signal: reuse helper below (simple)
            if not self.devices['starlink']['owned']:
                # 50/50 coarse chance outside towns
                biome_signal = 0.95 if 'town' in biome else 0.55
                rng = seeded_rng(self.location, today, 'signal')
                has_signal = rng.random() < biome_signal
            if not has_signal: fail_prereq = "No usable signal here; try Moab or move for coverage."
            base = 28.0 * (1.2 if in_moab else 1.0)
        elif kind == 'mechanic':
            base = 30.0 if in_moab else 22.0
        elif kind == 'guide':
            near_park = self.location in {'zion','bryce','arches','canyonlands','capitol_reef'}
            base = 24.0 if near_park or in_moab else 18.0
            tip_mult *= max(window_multiplier("morning", windows), window_multiplier("golden_hour", windows))
        elif kind == 'artist':
            base = 18.0 * 1.05
            tip_mult *= max(1.0, window_multiplier("golden_hour", windows))
        elif kind == 'gig':
            # treat as generic short work with random pay
            rng = seeded_rng(self.location, today, 'gig')
            hours = rng.uniform(1.5, 3.0); ticks = int((hours*60)//TURN_MINUTES) or 1
            base = rng.uniform(18, 32); tip_mult *= rng.uniform(0.9, 1.2)
        else:
            print(COL.yellow("Unknown work type. Try: WORK photo|dev|mechanic|guide|artist|gig [hours]")); return

        if fail_prereq: print(fail_prereq); return

        # Fatigue
        prev = self.work_hours_today.get(kind, 0.0)
        fatigue_mult = 1.0 if prev < 4 else 0.85 if prev < 6 else 0.7 if prev < 8 else 0.55

        # Job perks
        perk_mult = 1.0
        if kind == 'photo':   perk_mult *= (1.0 + self.job_perks.get('epic_bonus', 0.0) * 0.5)
        if kind == 'artist':  perk_mult *= (1.0 + self.job_perks.get('epic_bonus', 0.0) * 0.25)
        if kind == 'dev' and self.job == 'remote_dev': perk_mult *= 1.10
        if kind == 'mechanic' and self.job == 'mechanic': perk_mult *= 1.10
        if kind == 'guide' and self.job == 'trail_guide': perk_mult *= 1.10

        rng = seeded_rng(self.location, today, kind)
        variance = rng.uniform(0.9, 1.15)
        hourly = base * tip_mult * perk_mult * fatigue_mult * variance
        gross = hourly * hours

        if kind in ('photo','artist'):
            if rng.random() < (0.15 + 0.05 * (1 if 'golden_hour' in windows else 0)):
                bonus = rng.randint(40, 140); bonus = int(bonus * (1.0 + self.job_perks.get('epic_bonus', 0.0))); gross += bonus
                print(COL.green(f"A client buys a photo print (+${bonus})."))

        for _ in range(ticks):
            if self.mode == 'electric' and self.solar_watts > 0 and is_daylight(self.minutes):
                sol = (node.get('resources', {}) or {}).get('solar', 'fair')
                site = {'excellent':1.0,'good':0.75,'fair':0.5,'poor':0.25}.get(sol,0.5)
                uv_norm = clamp(derive_weather(node, self.minutes)['uv'] / max(1.0, get_season(self.minutes)[1].get('uv_peak', 8.0)), 0, 1)
                self.ev_battery = clamp(self.ev_battery + (self.solar_watts/1000.0)*4.0*site*uv_norm/4.0, 0, 100)
            if self.wind_watts > 0:
                w = derive_weather(node, self.minutes)
                house_level = {'low':0.0,'medium':0.8,'high':1.5}[w['wind']]
                ev_level    = {'low':0.2,'medium':0.6,'high':1.0}[w['wind']]
                self.battery    = clamp(self.battery + (self.wind_watts/300.0)*house_level/4.0 / self._pct_per_ah(), 0, 100)
                if self.mode=='electric':
                    self.ev_battery = clamp(self.ev_battery + (self.wind_watts/300.0)*ev_level/4.0, 0, 100)
            self.advance(TURN_MINUTES)

        extra_energy = int((2.5 if kind!='dev' else 1.5) * hours)
        extra_water  = round(0.06 * hours, 2)
        self.energy = clamp(self.energy - extra_energy, 0, 100)
        self.water  = clamp(self.water - extra_water, 0, self.water_cap_gallons)
        gross = int(round(gross)); self.cash += gross; self.work_hours_today[kind] = self.work_hours_today.get(kind, 0.0) + hours
        print(COL.grey(f"You work {kind} for ~{hours:.1f}h at ~${hourly:.0f}/h. Paid ${gross}."))
        print(COL.green(f"Now: Cash ${self.cash:.0f} | House {int(self.battery)}% | "
              f"{('EV '+str(int(self.ev_battery))+'%') if self.mode=='electric' else ('Fuel '+f'{self.fuel_gal:.1f} gal')} | "
              f"Water {self.water:.1f}G | Energy {int(self.energy)}."))
        # XP: based on hours and difficulty (wind/heat add challenge)
        diff = 1.0 + (0.1 if cur_weather['wind']=='high' else 0) + (0.1 if cur_weather['heat']=='hot' else 0)
        self.add_xp(int(hours*12*diff), f"work:{kind}")

    # ---------- Moab Shop ----------
    def shop(self):
        if self.location != 'moab': print(COL.yellow("No outfitter here. Try Moab.")); return
        print(COL.blue("Moab Outfitters — items (BUY <item_id> [qty])"))
        for key, it in self.catalog.items():
            name = it.get("name", key)
            price = it.get("price", 0)
            requires = it.get("requires", {})
            lvl = requires.get("level")
            print(COL.grey(f"  {key:<12} ${price:<5} — {name:<18} (requires level {lvl})."))
        print(f"Cash: {COL.green(f'${self.cash:.0f}')}")

    def _apply_effect(self, key, qty):
        """Resolve one catalog effect key for quantity qty."""
        purchased = None
        if key == "food_rations":
            before = self.food; self.food = min(self.food + qty, self.food_cap_rations); purchased = self.food - before
        elif key == "water_gallons":
            before = self.water; self.water = clamp(self.water + 1.0*qty, 0, self.water_cap_gallons); purchased = round(self.water - before, 1)
        elif key == "solar_watts":
            before = self.solar_watts
            self.solar_watts = min(self.solar_watts + qty, self.solar_cap_watts)
            purchased = self.solar_watts - before
        elif key == "wind_watts":
            before = self.wind_watts
            self.wind_watts = min(self.wind_watts + qty, self.wind_cap_watts)
            purchased = self.wind_watts - before
        elif key == "ev_range_mi":
            before = self.ev_range_mi; self.ev_range_mi = min(self.ev_range_mi + 40*qty, 400); purchased = self.ev_range_mi - before
        elif key == "water_cap_gallons":
            before = self.water_cap_gallons; self.water_cap_gallons = min(self.water_cap_gallons + 10*qty, self.max_water_cap); purchased = self.water_cap_gallons - before
        elif key == "food_cap_rations":
            before = self.food_cap_rations; self.food_cap_rations = min(self.food_cap_rations + 5*qty, self.max_food_cap); purchased = self.food_cap_rations - before
        elif key == "house_cap_ah":
            before = self.house_cap_ah
            self.house_cap_ah = clamp(self.house_cap_ah + float(qty), 50.0, 800.0)
            purchased = f"+{int(self.house_cap_ah - before)} Ah"
        elif key == "has_tent":
            if self.has_tent: return "already"
            self.has_tent = True; purchased = "installed"
        elif key.startswith("device:"):
            dev = key.split(":",1)[1]
            if self.devices.get(dev,{}).get('owned', False): return "already"
            if dev not in self.devices: self.devices[dev] = {'owned': False}
            self.devices[dev]['owned'] = True; purchased = "installed"
        elif key.startswith("device_amps:"):
            dev = key.split(":",1)[1]
            try:
                amps = float(str(qty))  # overload qty for amps? we'll set from effect value separately
            except Exception:
                amps = None
            # ignore here; amps set via value string of effect; handled in buy()
        elif key == "diesel_can_gal":
            self.diesel_can_gal = max(0.0, self.diesel_can_gal + qty); purchased = f"{qty} gal"
        elif key == "propane_lb":
            self.propane_lb = max(0.0, self.propane_lb + qty); purchased = f"{qty} lb"
        elif key == "butane_can":
            self.butane_can = max(0.0, self.butane_can + qty); purchased = f"{qty} can"
        return purchased

    def buy(self, item_id, qty=1):
        if self.location != 'moab': print(COL.yellow("You need to be in Moab to buy gear.")); return
        item_id = (item_id or '').lower()
        try: qty = int(qty)
        except Exception: qty = 1
        if qty <= 0: qty = 1
        if item_id not in self.catalog:
            print(COL.red("Unknown item id. Type SHOP to list items.")); return
        item = self.catalog[item_id]
        price = float(item.get("price", 0)) * qty
        # job discount for upgrades/devices (heuristic: price >= $150)
        if item.get("price", 0) >= 150:
            price *= (1.0 - self.job_perks.get('shop_discount', 0.0))
        if self.cash < price:
            print(COL.yellow(f"Not enough cash (${self.cash:.0f}). This costs ${price:.0f}.")); return

        purchased = None
        effects = item.get("effects", {})
        # If any effect values are strings like "+200", parse magnitude
        for eff_key, eff_val in effects.items():
            if eff_key.startswith("device_amps:"):
                dev = eff_key.split(":",1)[1]
                try:
                    amps = float(str(eff_val))
                    self.devices.setdefault(dev, {})['amps'] = amps
                except Exception:
                    pass
                continue

        for eff_key, eff_val in effects.items():
            if isinstance(eff_val, str) and eff_val.startswith("+"):
                try:
                    mag = float(eff_val[1:]) * qty
                except Exception:
                    mag = 0
                purchased = self._apply_effect(eff_key, mag)
            elif eff_val == "install":
                purchased = self._apply_effect(eff_key, 1)
            else:
                try:
                    mag = float(eff_val) * qty
                except Exception:
                    mag = 0
                purchased = self._apply_effect(eff_key, mag)

        if item.get("requires"):
            requires = item.get("requires", {})
            if requires.get("exp") and requires.get("level"): 
                exp = requires.get("exp")
                lvl = requires.get("level")
                if self.xp < int(exp) or self.level < int(lvl):
                    print(COL.yellow(f"Requires level {lvl}. You are only level {self.level}."))
                    print(COL.yellow(f"Requires {exp} experience. You only have {self.xp} experience."))
                    return
            elif requires.get("level"): 
                lvl = requires.get("level")
                if self.level < int(lvl):
                    print(COL.yellow(f"Requires level {lvl}. You are only level {self.level}."))
                    return
            elif requires.get("exp"): 
                exp = requires.get("exp")
                if self.xp < int(exp):
                    print(COL.yellow(f"Requires {exp} experience. You only have {self.xp} experience."))
                    return

        self.cash -= price
        print(COL.grey(f"Purchased {qty} × {item_id} for ${price:.0f}. Cash left: ${self.cash:.0f}."))
        if any(k in effects for k in ('solar_watts','wind_watts','ev_range_mi','water_cap_gallons','food_cap_rations')):
            print(COL.grey(f"Upgrades — solar: {self.solar_watts:.0f}W | wind: {self.wind_watts:.0f}W | EV range: {self.ev_range_mi} mi | caps: {self.water_cap_gallons:.0f}G/{self.food_cap_rations} rations"))

    # ---------- Mode / Energy ----------
    def set_mode(self, mode):
        m = (mode or '').lower()
        if m not in ('electric','fuel'): print(COL.red("MODE electric | MODE fuel")); return
        self.mode = m; print(COL.green(f"Drivetrain set to {self.mode.upper()}."))

    def charge(self, method):
        method = (method or '').lower()
        if self.mode != 'electric': print(COL.yellow("You're not in electric mode. Switch with: MODE electric")); return
        if method not in ('station','solar','wind'): print(COL.yellow("CHARGE how? Options: station | solar | wind")); return

        if method == 'station':
            if self.location != 'moab': print(COL.yellow("Fast charger unavailable here. Try Moab.")); return
            hours = 1.0; add_pct = 40.0; cost = add_pct * 0.5
            if self.cash < cost: print(COL.grey(f"Charging costs ${cost:.0f}. You have ${self.cash:.0f}.")); return
            self.cash -= cost; self.ev_battery = clamp(self.ev_battery + add_pct, 0, 100); self.advance(int(hours*60))
            print(COL.grey(f"Charged {add_pct:.0f}% at station in {hours:.1f}h. EV battery: {self.ev_battery:.0f}% | Cash ${self.cash:.0f}."))
        elif method == 'solar':
            hours = 2.0
            sol = (self.node().get('resources', {}) or {}).get('solar', 'fair')
            site = {'excellent':1.0, 'good':0.75, 'fair':0.5, 'poor':0.25}.get(sol, 0.5)
            uv_norm = clamp(derive_weather(self.node(), self.minutes)['uv'] / max(1.0, get_season(self.minutes)[1].get('uv_peak', 8.0)), 0, 1)
            add_pct = (self.solar_watts / 1000.0) * 8.0 * site * uv_norm
            if add_pct <= 0.1: print("You need solar panels installed to gain meaningful charge.")
            self.ev_battery = clamp(self.ev_battery + add_pct, 0, 100)
            self.battery = clamp(self.battery + add_pct, 0, 100)
            self.advance(int(hours*60))
            print(COL.green(f"Solar charging for {hours:.1f}h adds ~{add_pct:.1f}%. EV battery: {self.ev_battery:.0f}%."))
        else:
            hours = 2.0
            w = derive_weather(self.node(), self.minutes)
            wind_factor = {'low':0.2,'medium':0.6,'high':1.0}[w['wind']]
            add_pct = (self.wind_watts / 300.0) * 2.0 * wind_factor
            if add_pct <= 0.1: print("You need a wind turbine (and some wind) to gain meaningful charge.")
            self.ev_battery = clamp(self.ev_battery + add_pct, 0, 100)
            self.battery = clamp(self.battery + add_pct, 0, 100)
            self.advance(int(hours*60))
            print(COL.green(f"Wind charging for {hours:.1f}h adds ~{add_pct:.1f}%. EV battery: {self.ev_battery:.0f}%."))

    def refuel(self, gallons):
        if self.mode != 'fuel': print("You're not in fuel mode. Switch with: MODE fuel"); return
        if self.location != 'moab': print(COL.yellow("No reliable fuel here. Try Moab.")); return
        try: g = float(gallons)
        except Exception: print("REFUEL <gallons>"); return
        if g <= 0: print("That’s not how fuel works."); return
        price = 4.00; cost = g * price
        if self.cash < cost: print(COL.yellow(f"Need ${cost:.0f}; you have ${self.cash:.0f}.")); return
        self.cash -= cost; self.fuel_gal += g; self.advance(10)
        print(COL.green(f"Added {g:.1f} gal for ${cost:.0f}. Fuel now {self.fuel_gal:.1f} gal. Cash ${self.cash:.0f}."))

    # ----- Pets -----
    def adopt_pet(self):
        if not self.node().get('pet_adoption'): print(COL.yellow("No adoption event here. Try a larger town/rescue hub.")); return
        if self.pet: print(COL.yellow("You already travel with a loyal companion.")); return

        if self.vehicle_type == "subaru":
            self.pet_type = "cat"
        elif self.vehicle_type == "truck_camper":
            self.pet_type = "dog"
        else:
            self.pet_type = random.choice(["dog","cat"])

        if self.pet_type == "dog":
            breed = random.choice(["French Bulldog","Golden Retriever","Labrador Retriever","Rottweiler","Beagle","Bulldog","Poodle","Dachsund","German Shorthair Pointer","German Shepherd","Shih Tzu","Terrier","Golden Doodle","Australian Sheepdog"])
            name = random.choice(["Oreo","Mesa","Juniper","Pixel","Bowie","Zion","Havasu","Spot","Flash","The Dude","Max","Scooter"])
            spirit = random.choice(["spirited","lazy","young","overweight","timid","large","small","playful","youthful","energetic"])
            action = random.choice(["licks your face","claims the passenger seat","looks at you with big brown eyes","wags their tail","barks excitedly"])
            self.pet = Pet(name, breed); self.morale = clamp(self.morale + 10, 0, 100)
            print(COL.grey(f"You meet {name}, a {spirit} {breed}, who promptly {action}. Bond +10."))
        if self.pet_type == "cat":
            breed = random.choice(["Siamese","Persian","Maine Coon","Ragdoll","Sphynx","American Shorthair","Burmese","British Shorthair","Longhair","Bobtail"])
            name = random.choice(["Swazi","Whiskers","Patches","Satan","Grouchy Pants","Moo","Olaf","Chandler","Joey","Monica","Ross","Phoebe","Rachael"])
            spirit = random.choice(["spirited","lazy","young","overweight","timid","large","small","playful","youthful","energetic"])
            action = random.choice(["disappears into the back of the vehicle","makes their way onto the dash","winds between your legs","meows hungrily"])
            self.pet = Pet(name, breed); self.morale = clamp(self.morale + 10, 0, 100)
            print(COL.grey(f"You meet {name}, a {spirit} {breed} cat, who promptly {action}. Bond +6."))
        xp = clamp(self.xp + 10, 0, 30)
        self.add_xp(int(xp), "pet adoption")

    def feed_pet(self):
        if not self.pet: print("You travel alone."); return
        if self.food <= 0: print(COL.red("You have nothing to share.")); return
        self.food -= 1; self.pet.bond = clamp(self.pet.bond + 6, 0, 100); self.advance(TURN_MINUTES)
        print(COL.grey(f"You feed {self.pet.name}. Bond warms."))
        xp = clamp(self.xp + 5, 0, 20)
        self.add_xp(int(xp), "pet care")

    def water_pet(self):
        if not self.pet: print("You travel alone."); return
        if self.water < 0.3: print(COL.red("Water is too low.")); return
        self.water = clamp(self.water - 0.3, 0, self.water_cap_gallons); self.pet.bond = clamp(self.pet.bond + 3, 0, 100); self.advance(TURN_MINUTES//2)
        print(COL.grey(f"{self.pet.name} drinks happily."))
        xp = clamp(self.xp + 5, 0, 20)
        self.add_xp(int(xp), "pet care")

    def walk_pet(self):
        if not self.pet: print("You travel alone."); return
        self.energy = clamp(self.energy + 2, 0, 100); self.pet.energy = clamp(self.pet.energy + 5, 0, 100); self.pet.bond = clamp(self.pet.bond + 4, 0, 100); self.advance(30)
        print(COL.grey(f"You walk {self.pet.name}. Spirits lift."))
        xp = clamp(self.xp + 10, 0, 25)
        self.add_xp(int(xp), "pet care")

    def play_with_pet(self):
        if not self.pet: print("You travel alone."); return
        self.pet.bond = clamp(self.pet.bond + 5, 0, 100); self.morale = clamp(self.morale + 4, 0, 100); self.advance(20)
        vehicle = self.vehicle_type.replace('_',' ')
        print(COL.grey(f"You play tug and fetch with {self.pet.name}. Laughter echoes in the {vehicle}."))
        xp = clamp(self.xp + 15, 0, 30)
        self.add_xp(int(xp), "play")

    def command_pet(self, verb):
        if not self.pet: print("You travel alone."); return
        v = (verb or '').strip().upper()
        if v == 'GUARD':
            self.pet.guard_mode = True; self.pet.alert = clamp(self.pet.alert + 10, 0, 100)
            print(COL.grey(f"{self.pet.name} settles by the door, ears up. Guard mode ON."))
        elif v == 'CALM':
            self.pet.guard_mode = False; self.pet.alert = clamp(self.pet.alert - 10, 0, 100)
            print(COL.grey(f"{self.pet.name} relaxes. Guard mode OFF."))
        elif v == 'SEARCH':
            rng = seeded_rng(self.location, int(self.minutes/60), 'search')
            if rng.random() < 0.4:
                self.water = clamp(self.water + 1.0, 0, self.water_cap_gallons)
                print(COL.green(f"{self.pet.name} finds fresh water. +1.0G water."))
                xp = 20
                self.add_xp(int(xp), "search")
            else:
                print(COL.grey(f"{self.pet.name} sniffs around but finds nothing today."))
            self.advance(TURN_MINUTES)
        elif v == 'HEEL':
            print(COL.grey(f"{self.pet.name} falls in line. It's the little things."))
        elif v == 'FETCH':
            self.morale = clamp(self.morale + 2, 0, 100)
            print(COL.grey(f"{self.pet.name} returns triumphantly with... a glove? Sure, that tracks."))
        else:
            print("Available: HEEL, SEARCH, GUARD, CALM, FETCH.")

# ---------------------------- IO & Loop -------------------------------

HELP_TEXT = """Commands:
  ADOPT PET | FEED PET | WATER PET | WALK PET | PLAY WITH PET
  CAMP [stealth|paid|dispersed]
  COMMAND PET <HEEL|SEARCH|GUARD|CALM|FETCH>
  COOK | EAT
  NAP
  DEVICES | TURN <device> <on|off>
  ELEVATION
  EV
  FUEL
  HIKE
  INVENTORY | INV | I
  LOOK | STATUS | MAP
  MODE <electric|fuel> | CHARGE <station|solar|wind> | REFUEL <gallons>
  PET
  POWER | ELECTRICAL | BATTERY
  READ
  ROUTE TO <place> | DRIVE
  SHOP | BUY <item_id> [qty]
  SOLAR
  WATCH <something>
  WEATHER
  WIND
  WORK [photo|dev|mechanic|guide|artist|gig] [hours]
  HELP | QUIT
"""

def make_cli_prompt(game):
    t = minutes_to_hhmm(game.minutes)
    netA, _, _, _ = game.compute_current()
    mode = f"EV {int(game.ev_battery)}%" if game.mode=='electric' else f"Fuel {game.fuel_gal:.1f}g"
    return COL.prompt(f"[{t}] > ")

def load_world():
    here = os.path.dirname(os.path.abspath(__file__))
    cand_yaml = os.path.join(here, "utah.yaml")
    cand_json = os.path.join(here, "utah.json")
    nodes = None
    if os.path.exists(cand_yaml):
        try:
            import yaml
            with open(cand_yaml, "r", encoding="utf-8") as f:
                nodes = yaml.safe_load(f)["nodes"]
        except Exception as e:
            print(COL.red(f"YAML load failed: {e}. Falling back to JSON."))
    if nodes is None and os.path.exists(cand_json):
        with open(cand_json, "r", encoding="utf-8") as f:
            nodes = json.load(f)["nodes"]
    if not nodes:
        print(COL.red("No world data found. Place utah.yaml (or utah.json) next to this script."))
        sys.exit(1)
    return World(nodes)

def pick_from_dict(title, dct):
    print(COL.blue(title))
    keys = list(dct.keys())
    for i, k in enumerate(keys, 1):
        lab = dct[k].get("label", k)
        print(f"  {i}) {lab} [{k}]")
    while True:
        ans = input(COL.prompt("> ")).strip().lower()
        if ans.isdigit():
            idx = int(ans)-1
            if 0 <= idx < len(keys): return keys[idx]
        if ans in dct: return ans
        print(COL.red("Pick by number or key from the list above."))

def character_creation():
    print(COL.blue("=== Character & Vehicle Setup ==="))
    name = input(COL.prompt("Vehicle Name (enter to randomize): ")).strip()
    if not name:
        name = random.choice(["Rocinante","Casper","River","Juniper","Sky","Ash","Indigo","Cedar","Rook","Raven"])
    color = input(COL.prompt("Vehicle color: ")).strip() or "white"
    vkey = pick_from_dict("Pick a vehicle type:", VEHICLES)
    jkey = pick_from_dict("Pick a job:", JOBS)
    mode = ""
    while mode not in ("electric", "fuel"):
        mode = input(COL.prompt("Drivetrain [electric|fuel]: ")).strip().lower() or "electric"
    rng = seeded_rng(name, color, vkey, jkey, mode)
    start_cash = rng.randint(1000, 10000)
    cfg = {"name": name, "color": color, "vehicle_key": vkey, "job_key": jkey, "mode": mode, "start_cash": float(start_cash)}
    print(COL.blue(f"Welcome, {name}. {color.title()} {VEHICLES[vkey]['label']} | {JOBS[jkey]['label']} | Start cash: {COL.green(f'${start_cash}')}"))
    return cfg

def main():
    world = load_world()
    catalog = load_items_catalog()
    npcs = load_npcs()

    with open('WELCOME', "r", encoding="utf-8") as f:
        welcome_txt = f.read()
    print(COL.blue(welcome_txt))
    input(COL.blue("Press ENTER to continue..."))

    cfg = character_creation()
    game = Game(world, cfg, catalog, npcs=npcs)

    print(COL.cyan("Welcome to Nomads!"))
    game.look()
    game._check_for_truck_camper()
    print("Type HELP for commands.\n")

    while True:
        try:
            line = input("\n" + make_cli_prompt(game)).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGood roads and tailwinds."); break
        if not line: continue
        u = line.upper()

        if u in ('HELP','?'): print(COL.grey(HELP_TEXT))
        elif u in ('LOOK','L'): game.look()
        elif u in ('STATUS','STATS'): game.status()
        elif u == 'MAP': game.show_map()
        elif u.startswith('ROUTE TO THE '): game.route_to(line.split(' ', 3)[3])
        elif u.startswith('ROUTE TO '): game.route_to(line.split(' ', 2)[2])
        elif u == 'DRIVE': game.drive()
        elif u == 'WEATHER': game.check_weather()
        elif u.startswith('CAMP'):
            parts = line.split(); style = parts[1] if len(parts)>1 else ''
            game.camp(style)
        elif u in ('COOK','EAT'): game.cook()
        elif u == 'NAP': game.sleep()
        elif u == 'HIKE': game.hike()
        elif u == 'SHOP': game.shop()
        elif u.startswith('BUY '):
            parts = line.split(); item = parts[1] if len(parts) > 1 else ''
            qty  = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
            game.buy(item, qty)
        elif u.startswith('MODE '): game.set_mode(line.split(' ', 1)[1])
        elif u.startswith('CHARGE'):
            parts = line.split(); method = parts[1] if len(parts) > 1 else ''
            game.charge(method)
        elif u.startswith('REFUEL'):
            parts = line.split(); gallons = parts[1] if len(parts) > 1 else ''
            game.refuel(gallons)
        elif u == 'ADOPT PET': game.adopt_pet()
        elif u == "FEED PET": game.feed_pet()
        elif u == 'WATER PET': game.water_pet()
        elif u == 'WALK PET': game.walk_pet()
        elif u == 'PLAY WITH PET': game.play_with_pet()
        elif u.startswith('COMMAND PET'):
            verb = line.split(' ', 2)[2] if len(line.split(' ', 2))>2 else ''
            game.command_pet(verb)
        elif u in ('QUIT','EXIT'):
            print("You turn off the vehicle and end the adventure. Bye."); break
        elif u.startswith('WORK'):
            parts = line.split()
            kind  = parts[1] if len(parts)>1 and parts[1].lower() not in ('1','2','3','4','5','6') else ''
            hours = parts[2] if len(parts)>2 else (parts[1] if len(parts)>1 and parts[1].isdigit() else None)
            game.work(kind, hours)
        elif u == 'DEVICES': game.devices_panel()
        elif u.startswith('TURN'):
            parts = line.split()
            if len(parts) >= 3: game.toggle_device(parts[1], parts[2])
            else: print("TURN <device> <on|off>")
        elif u in ('ELECTRICAL','POWER'): game.electrical_panel()
        elif u == 'BATTERY': game.battery_status()
        elif u == 'EXP': game.exp()
        elif u == 'ELEVATION': game.elevation()
        elif u in ('INVENTORY','INV','I'): game.inventory()
        elif u in ('CASH','BANK','MONEY'): game.bank()
        elif u == "SOLAR": game.solar_power_status()
        elif u == "WIND": game.wind_power_status()
        elif u == "EV": game.ev_status()
        elif u == "FUEL": game.fuel_status()
        elif u == "TIME": game.report_time()
        elif u == "READ": game.read_book()
        elif u == "PEOPLE": game.people()
        elif u == "MORALE": game.report_morale()
        elif u == "ENERGY": game.report_energy()
        elif u == "PET": game.report_pet_status()
        elif u.startswith('WATCH '): game.watch_something(line.split(' ', 1)[1])
        elif u.startswith('TRADE '): game.trade(line.split(' ', 1)[1])
        elif u.startswith('TALK '): game.talk(line.split(' ', 1)[1])
        else:
            print(COL.red("Unknown command. Type HELP."))

if __name__ == "__main__":
    main()
