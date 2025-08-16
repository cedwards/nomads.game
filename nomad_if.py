#!/usr/bin/env python3
# Nomad IF prototype — Utah slice
# CLI game loop with basic verbs:
# LOOK, STATUS, MAP, ROUTE TO <place>, DRIVE, CHECK WEATHER,
# CAMP [stealth|paid], COOK, SLEEP,
# ADOPT PET, FEED PET, WATER PET, WALK PET, PLAY WITH PET,
# COMMAND PET <HEEL|SEARCH|GUARD|CALM|FETCH>, HELP, QUIT

import os, sys, math, json, re, random, datetime
from collections import defaultdict, deque

TURN_MINUTES = 15
DAY_MINUTES = 24 * 60

# ===== Archetypes & Jobs =====

VEHICLES = {
    # battery_capacity_factor affects how fast HOUSE battery % changes:
    # bigger pack => slower % drift and slower % charging (more real)
    "sedan": {
        "label": "Sedan (stealthy, light)",
        "base_water_cap": 25, "max_water_cap": 40,
        "base_food_cap": 8,   "max_food_cap": 14,
        "house_cap_factor": 0.7,
        "solar_cap_watts": 400, "wind_cap_watts": 300,
        "ev_range": 300, "mpg": 30, "fuel_tank_gal": 14
    },
    "van": {
        "label": "Van (classic nomad rig)",
        "base_water_cap": 50, "max_water_cap": 90,
        "base_food_cap": 12,  "max_food_cap": 20,
        "house_cap_factor": 1.0,
        "solar_cap_watts": 800, "wind_cap_watts": 300,
        "ev_range": 240, "mpg": 22, "fuel_tank_gal": 24
    },
    "truck_camper": {
        "label": "Truck + Camper (capable, off-grid)",
        "base_water_cap": 60, "max_water_cap": 110,
        "base_food_cap": 14,  "max_food_cap": 22,
        "house_cap_factor": 1.2,
        "solar_cap_watts": 1000, "wind_cap_watts": 600,
        "ev_range": 220, "mpg": 15, "fuel_tank_gal": 26
    },
    "skoolie": {
        "label": "Skoolie (roomy bus, slow)",
        "base_water_cap": 120, "max_water_cap": 200,
        "base_food_cap": 24,   "max_food_cap": 40,
        "house_cap_factor": 2.0,
        "solar_cap_watts": 1800, "wind_cap_watts": 900,
        "ev_range": 160, "mpg": 8, "fuel_tank_gal": 55
    }
}

JOBS = {
    "photographer": {
        "label": "Photographer (eye for light)",
        "epic_bonus": 0.25   # +25% on epic photo payouts
    },
    "mechanic": {
        "label": "Mechanic (handy with tools)",
        "shop_discount": 0.15  # 15% off shop upgrades
    },
    "remote_dev": {
        "label": "Remote Dev (wifi wizard)",
        "remote_camp_income": 30  # earn $ on camps with signal
    },
    "trail_guide": {
        "label": "Trail Guide (path whisperer)",
        "hike_energy_mult": 0.8,     # hikes cost 20% less energy
        "hike_find_bonus": 0.10      # +10% to scenic-find chance
    },
    "artist": {
        "label": "Artist (muse on wheels)",
        "morale_bonus_dispersed": 3,  # extra joy at dispersed camps
        "epic_bonus": 0.10
    }
}

# ---------------------------- Utility ---------------------------------

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def minutes_to_hhmm(total_minutes):
    d = total_minutes // DAY_MINUTES + 1
    m = total_minutes % DAY_MINUTES
    hh = m // 60
    mm = m % 60
    return f"Day {d} {hh:02d}:{mm:02d}"

def is_daylight(total_minutes):
    # Simple model: daylight 06:00 - 20:00
    m = total_minutes % DAY_MINUTES
    return 6*60 <= m < 20*60

def seeded_rng(*parts):
    seed = 0xABCDEF
    for p in parts:
        seed ^= hash(p) & 0xFFFFFFFF
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
    return random.Random(seed)

# ---------------------------- World -----------------------------------

class World:
    def __init__(self, nodes):
        self.nodes = {n['id']: n for n in nodes}
        self._ensure_bidirectional()

    def _ensure_bidirectional(self):
        # Make connections two-way if not already present
        for nid, node in self.nodes.items():
            conns = node.get('connections', [])
            for c in conns:
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
        if key_l in self.nodes:
            return key_l
        for nid, n in self.nodes.items():
            if n.get('name','').lower() == key_l:
                return nid
        for nid, n in self.nodes.items():
            if key_l in nid or key_l in n.get('name','').lower():
                return nid
        return None

# ---- Time of day windows & signal heuristics ----
def current_time_windows(total_minutes, node):
    """Return a set of window tags for right now at this node."""
    m = total_minutes % DAY_MINUTES
    w = derive_weather(node, total_minutes)
    tags = set()
    if 330 <= m <= 450:      # 05:30–07:30
        tags.add("sunrise")
        tags.add("golden_hour")
    if 360 <= m <= 480:      # 06:00–08:00
        tags.add("golden_hour")
    if 420 <= m <= 660:      # 07:00–11:00
        tags.add("morning")
        tags.add("daylight")
    if 660 < m < 1110:       # 11:00–18:30
        tags.add("daylight")
    if 1110 <= m <= 1200:    # 18:30–20:00
        tags.add("golden_hour")
        tags.add("daylight")
    if not (360 <= m < 1200):
        tags.add("night")
        if (not w['monsoon']) and (w['wind'] != 'high') and (not w['flood_watch']):
            tags.add("night_clear")
    return tags, w

def window_multiplier(window_tag, windows):
    """Production multiplier if a requested window is 'open'."""
    if window_tag not in windows: return 0.6   # workable but off-peak
    mults = {
        "sunrise": 1.6,
        "golden_hour": 1.5,
        "morning": 1.15,
        "daylight": 1.0,
        "night": 0.9,
        "night_clear": 1.4,
    }
    return mults.get(window_tag, 1.0)

def has_signal_here(node, total_minutes):
    """Crude cell-signal model by biome + a daily roll."""
    biome = (node.get('biome') or '').lower()
    base = 0.6
    if 'town' in biome: base = 0.95
    elif 'alpine' in biome: base = 0.65
    elif 'salt' in biome: base = 0.55
    elif any(k in biome for k in ['desert_canyon','canyon','mesa','high_desert','desert']):
        base = 0.5
    rng = seeded_rng(node['id'], total_minutes // DAY_MINUTES, 'signal_work')
    return rng.random() < base


# ---------------------------- Weather ---------------------------------

def derive_weather(node, total_minutes):
    day = total_minutes // DAY_MINUTES + 1
    rng = seeded_rng(node['id'], day)
    wind = rng.choices(['low','medium','high'], weights=[4,3,2])[0]
    if 'summer_heat' in node.get('season_rules', []):
        heat = rng.choices(['mild','hot','very_hot'], weights=[2,4,2])[0]
    elif 'cold_nights' in node.get('season_rules', []):
        heat = rng.choices(['cold','mild'], weights=[3,2])[0]
    elif 'alpine' in node.get('biome',''):
        heat = rng.choices(['cold','mild'], weights=[3,2])[0]
    else:
        heat = rng.choices(['mild','hot'], weights=[3,3])[0]
    monsoon = 'monsoon' in ''.join(node.get('season_rules', [])) and rng.random() < 0.2
    flood_watch = ('flash_flood' in ''.join(node.get('season_rules', [])) or 'monsoon' in ''.join(node.get('season_rules', []))) and rng.random() < 0.15
    return {'heat': heat, 'wind': wind, 'monsoon': monsoon, 'flood_watch': flood_watch}

def weather_speed_mod(w):
    mod = 1.0
    if w['heat'] in ('hot','very_hot'): mod *= 0.95
    if w['wind'] == 'high': mod *= 0.92
    if w['flood_watch']: mod *= 0.90
    return mod

def describe_weather(w):
    parts = [
        {'cold':"cold",'mild':"mild",'hot':"hot",'very_hot':"very hot"}[w['heat']],
        {'low':"light winds",'medium':"breezy",'high':"windy"}[w['wind']]
    ]
    if w['monsoon']: parts.append("monsoon cells around")
    if w['flood_watch']: parts.append("flash-flood watch")
    return ", ".join(parts)

# ---------------------------- Travel ----------------------------------

BASE_SPEED = {
    'interstate': 65.0,
    'highway': 55.0,
    'scenic': 45.0,
    'mixed': 40.0,
    'gravel': 30.0,
    'trail': 10.0,
}
GRADE_MOD = {'flat':1.00,'light':0.95,'moderate':0.85,'mixed':0.90,'steep':0.70}

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
        if cur is None or cur == dst:
            break
        visited.add(cur)
        for c in world.nodes[cur].get('connections', []):
            turns, _w = edge_drive_turns(world, cur, c, total_minutes + dist[cur]*TURN_MINUTES)
            nd = dist[cur] + turns
            if nd < dist[c['to']]:
                dist[c['to']] = nd
                prev[c['to']] = (cur, c)
    if dist[dst] == math.inf:
        return None, None
    path = []
    nid = dst
    while nid != src:
        p = prev[nid]
        if not p: break
        path.append((p[0], nid, p[1]))
        nid = p[0]
    path.reverse()
    return path, dist[dst]

# ---------------------------- Game State ------------------------------

class Pet:
    def __init__(self, name):
        self.name = name
        self.bond = 30
        self.energy = 70
        self.obedience = 60
        self.paw = 100
        self.alert = 50
        self.guard_mode = False

    def tick(self, minutes):
        self.energy = clamp(self.energy - (minutes/60)*2, 0, 100)

class Game:
    def __init__(self, world, config):
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
        self.water_cap_liters = v["base_water_cap"]
        self.food_cap_rations = v["base_food_cap"]
        self.max_water_cap    = v["max_water_cap"]
        self.max_food_cap     = v["max_food_cap"]
        self.house_cap        = v["house_cap_factor"]  # dimensionless, scales % changes
        self.solar_cap_watts  = v["solar_cap_watts"]
        self.wind_cap_watts   = v["wind_cap_watts"]

        # Upgrades (house systems)
        self.solar_watts = 0
        self.wind_watts  = 0
        self.has_tent    = False

        # House battery (0–100%)
        self.battery = 62.0

        # Stores (respect caps)
        self.water = min(8.0, self.water_cap_liters)   # liters
        self.food  = min(6,   self.food_cap_rations)   # rations

        # Cash & morale/energy
        self.cash   = float(config.get("start_cash", 120.0))
        self.morale = 60.0
        self.energy = 80.0

        # Pet
        self.pet = None

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

        # Work tracking (fatigue & per-day throttles)
        self.work_hours_day = -1
        self.work_hours_today = {}
        self.gig_cooldowns = {}  # key: gig_id@node -> day_index last done

    def _work_gig(self, hours):
        node = self.node()
        gigs = node.get('gigs') or []
        if not gigs:
            print("No listed gigs here. Try a job-type WORK instead."); return
        windows, _w = current_time_windows(self.minutes, node)

        # Pick a gig whose window fits now (fall back to any)
        viable = [g for g in gigs if g.get('window') in windows]
        if not viable:
            viable = gigs[:]
        gig = random.choice(viable)
        gid = gig.get('id', 'gig')

        # one-per-day throttle per location/gig
        today = self.minutes // DAY_MINUTES
        key = f"{self.location}:{gid}"
        if self.gig_cooldowns.get(key) == today:
            print("That gig’s dried up for today. Check back tomorrow or try another kind of work."); return

        lo, hi = gig.get('payout', [40, 120])
        rng = seeded_rng(self.location, today, gid)
        pay = rng.randint(int(lo), int(hi))

        # Job perks that plausibly help gigs
        if self.job in ('photographer','artist') and gig.get('window') in ('golden_hour','sunrise','night_clear'):
            pay = int(pay * (1.0 + self.job_perks.get('epic_bonus', 0.0)))
        if self.job == 'mechanic' and gid and 'washout' not in gid:
            pay = int(pay * 1.1)

        # Duration: ignore requested hours; gigs are compact 1.5–3h
        ghours = rng.uniform(1.5, 3.0)
        ticks = int((ghours*60)//TURN_MINUTES) or 1

        # Passive charging during gig work, same as generic work
        for _ in range(ticks):
            if self.mode == 'electric' and self.solar_watts > 0 and is_daylight(self.minutes):
                sol = (node.get('resources', {}) or {}).get('solar', 'fair')
                site = {'excellent':1.0,'good':0.75,'fair':0.5,'poor':0.25}.get(sol,0.5)
                self.ev_battery = clamp(self.ev_battery + (self.solar_watts/1000.0)*4.0*site/4.0, 0, 100)
            if self.wind_watts > 0:
                w = derive_weather(node, self.minutes)
                house_level = {'low':0.0,'medium':0.8,'high':1.5}[w['wind']]
                ev_level    = {'low':0.2,'medium':0.6,'high':1.0}[w['wind']]
                self.battery    = clamp(self.battery + (self.wind_watts/300.0)*house_level/4.0 / self.house_cap, 0, 100)
                if self.mode=='electric':
                    self.ev_battery = clamp(self.ev_battery + (self.wind_watts/300.0)*ev_level/4.0, 0, 100)
            self.advance(TURN_MINUTES)

        # costs
        self.energy = clamp(self.energy - int(2.0 * ghours), 0, 100)
        self.water  = clamp(self.water  - round(0.05 * ghours, 2), 0, self.water_cap_liters)

        self.cash += pay
        self.gig_cooldowns[key] = today
        print(f"You complete gig '{gid}' (~{ghours:.1f}h) and earn ${pay}. Cash ${self.cash:.0f}.")

    def work(self, kind='', hours=None):
        """
        WORK [photo|dev|mechanic|guide|artist|gig] [hours]
        - If kind omitted: uses your chosen job.
        - Hours default: random 1–4, clamped to 1–6.
        - Time advances in 15m ticks; solar/wind trickle (house & EV) apply.
        """
        node = self.node()
        kind = (kind or '').lower().strip()
        # Default to player's job
        if not kind or kind == 'job':
            jk = self.job
            kind = {'photographer':'photo','remote_dev':'dev','mechanic':'mechanic',
                    'trail_guide':'guide','artist':'artist'}.get(jk, 'photo')

        # Hours
        if hours is None:
            hours = random.randint(1,4)
        try:
            hours = float(hours)
        except Exception:
            hours = 2.0
        hours = max(1.0, min(6.0, hours))
        ticks = int((hours*60) // TURN_MINUTES) or 1

        # Daily fatigue ledger
        today = self.minutes // DAY_MINUTES
        if self.work_hours_day != today:
            self.work_hours_day = today
            self.work_hours_today = {}

        # Economics presets
        windows, cur_weather = current_time_windows(self.minutes, node)
        biome = (node.get('biome') or '').lower()
        photogenic = 1.0
        if any(k in biome for k in ['arches','canyon']): photogenic = 1.35
        if 'desert' in biome: photogenic = max(photogenic, 1.25)
        if 'salt' in biome: photogenic = max(photogenic, 1.30)
        if 'alpine' in biome: photogenic = max(photogenic, 1.15)
        in_moab = (self.location == 'moab')

        # Base $/h by kind + window bonus logic
        base = 18.0
        tip_mult = 1.0
        label = kind
        fail_prereq = None

        if kind == 'photo':
            base = 22.0 * photogenic
            # Best during golden_hour / sunrise / night_clear
            peak = max(window_multiplier("golden_hour", windows),
                       window_multiplier("sunrise", windows),
                       window_multiplier("night_clear", windows))
            tip_mult *= peak
        elif kind == 'dev':
            if not has_signal_here(node, self.minutes):
                fail_prereq = "No usable signal here; try Moab or move for coverage."
            base = 28.0 * (1.2 if in_moab else 1.0)
        elif kind == 'mechanic':
            base = 30.0 if in_moab else 22.0
        elif kind == 'guide':
            near_park = self.location in {'zion','bryce','arches','canyonlands','capitol_reef'}
            base = 24.0 if near_park or in_moab else 18.0
            tip_mult *= max(window_multiplier("morning", windows),
                            window_multiplier("golden_hour", windows))
        elif kind == 'artist':
            base = 18.0 * (1.1 if 'dispersed' else 1.0)
            tip_mult *= max(1.0, window_multiplier("golden_hour", windows))
        elif kind == 'gig':
            return self._work_gig(hours)  # separate handler uses node.gigs
        else:
            print("Unknown work type. Try: WORK photo|dev|mechanic|guide|artist|gig [hours]")
            return

        if fail_prereq:
            print(fail_prereq); return

        # Fatigue: diminishing returns after 4h of same kind in a day
        prev = self.work_hours_today.get(kind, 0.0)
        fatigue_mult = 1.0 if prev < 4 else 0.85 if prev < 6 else 0.7 if prev < 8 else 0.55

        # Job perks
        perk_mult = 1.0
        if kind == 'photo':
            perk_mult *= (1.0 + self.job_perks.get('epic_bonus', 0.0) * 0.5)
        if kind == 'artist':
            perk_mult *= (1.0 + self.job_perks.get('epic_bonus', 0.0) * 0.25)
        if kind == 'dev' and self.job == 'remote_dev':
            perk_mult *= 1.10
        if kind == 'mechanic' and self.job == 'mechanic':
            perk_mult *= 1.10
        if kind == 'guide' and self.job == 'trail_guide':
            perk_mult *= 1.10

        # Stochastic spice
        rng = seeded_rng(self.location, today, kind)
        variance = rng.uniform(0.9, 1.15)

        # Final hourly rate & gross
        hourly = base * tip_mult * perk_mult * fatigue_mult * variance
        gross = hourly * hours

        # Epic chance for creatives
        if kind in ('photo','artist'):
            if rng.random() < (0.15 + 0.05 * (1 if 'golden_hour' in windows else 0)):
                bonus = rng.randint(40, 140)
                bonus = int(bonus * (1.0 + self.job_perks.get('epic_bonus', 0.0)))
                gross += bonus
                print(f"A client bites on a shot/print (+${bonus}).")

        # Tick forward in 15m slices; trickle HOUSE & EV from wind/solar while you work.
        for _ in range(ticks):
            # EV solar (daylight) trickle
            if self.mode == 'electric' and self.solar_watts > 0 and is_daylight(self.minutes):
                sol = (node.get('resources', {}) or {}).get('solar', 'fair')
                site = {'excellent':1.0,'good':0.75,'fair':0.5,'poor':0.25}.get(sol,0.5)
                self.ev_battery = clamp(self.ev_battery + (self.solar_watts/1000.0)*4.0*site/4.0, 0, 100)
            # Wind trickle
            if self.wind_watts > 0:
                w = derive_weather(node, self.minutes)
                house_level = {'low':0.0,'medium':0.8,'high':1.5}[w['wind']]
                ev_level    = {'low':0.2,'medium':0.6,'high':1.0}[w['wind']]
                self.battery    = clamp(self.battery + (self.wind_watts/300.0)*house_level/4.0 / self.house_cap, 0, 100)
                if self.mode=='electric':
                    self.ev_battery = clamp(self.ev_battery + (self.wind_watts/300.0)*ev_level/4.0, 0, 100)
            # Advance world (applies house solar + normal drift)
            self.advance(TURN_MINUTES)

        # Costs of working
        extra_energy = int(2.5 * hours) if kind != 'dev' else int(1.5 * hours)
        extra_water  = round(0.06 * hours, 2)
        self.energy = clamp(self.energy - extra_energy, 0, 100)
        self.water  = clamp(self.water - extra_water, 0, self.water_cap_liters)

        # Get paid
        gross = int(round(gross))
        self.cash += gross
        self.work_hours_today[kind] = self.work_hours_today.get(kind, 0.0) + hours

        print(f"You work {kind} for ~{hours:.1f}h at ~${hourly:.0f}/h. Paid ${gross}.")
        print(f"Now: Cash ${self.cash:.0f} | House {int(self.battery)}% | "
              f"{('EV '+str(int(self.ev_battery))+'%') if self.mode=='electric' else ('Fuel '+f'{self.fuel_gal:.1f} gal')} | "
              f"Water {self.water:.1f}L | Energy {int(self.energy)}.")

    def hike(self, direction):
        """Go on a hike in a compass direction.
        Duration = random 1–5 hours scaled by per-node hike_map for that direction.
        While hiking, time advances; house battery gets passive solar (via advance()),
        and we also trickle both HOUSE and EV batteries from wind/solar each tick.
        """
        dir_clean = (direction or '').lower()
        valid = {'n','s','e','w','ne','nw','se','sw'}
        if dir_clean not in valid:
            print("HIKE which way? Use: HIKE n|s|e|w|ne|nw|se|sw"); return

        node = self.node()
        hmap = (node.get('hike_map') or {})
        seg = hmap.get(dir_clean, 3)  # relative length; 3 ~ neutral
        seg = max(1, min(5, int(seg)))
        base_hours = random.randint(1,5)
        factor = max(0.5, min(2.0, seg / 3.0))
        hours = max(1.0, round(base_hours * factor, 1))
        ticks = int((hours * 60) // TURN_MINUTES)
        if ticks <= 0: ticks = 1

        # Site quality for solar
        sol_quality = (node.get('resources', {}) or {}).get('solar', 'fair')
        site = {'excellent':1.0, 'good':0.75, 'fair':0.5, 'poor':0.25}.get(sol_quality, 0.5)

        # Narration
        print(f"You set out {dir_clean.upper()} for a ~{hours:.1f}h hike.")
        found = False

        for _ in range(ticks):
            # Passive EV charging: solar (daylight only)
            if self.mode == 'electric' and self.solar_watts > 0 and is_daylight(self.minutes):
                # ~4% per h per kW at good site; scale by site; per tick (15m) is /4
                ev_solar_per_tick = (self.solar_watts / 1000.0) * 4.0 * site / 4.0
                self.ev_battery = clamp(self.ev_battery + ev_solar_per_tick, 0, 100)

            # Passive wind to HOUSE & EV during the hike
            if self.wind_watts > 0:
                w = derive_weather(node, self.minutes)
                house_level = {'low':0.0, 'medium':0.8, 'high':1.5}[w['wind']]       # %/h baseline for house
                ev_level    = {'low':0.2, 'medium':0.6, 'high':1.0}[w['wind']]       # %/h baseline for EV
                house_wind_per_tick = (self.wind_watts / 300.0) * house_level / 4.0
                ev_wind_per_tick    = (self.wind_watts / 300.0) * ev_level    / 4.0 if self.mode=='electric' else 0.0
                self.battery   = clamp(self.battery   + house_wind_per_tick / self.house_cap, 0, 100)
                self.ev_battery = clamp(self.ev_battery + ev_wind_per_tick,   0, 100)

            # Advance time & apply passive solar to HOUSE battery, water/energy drift, pet ticks
            self.advance(TURN_MINUTES)

            # Little chance of a scenic find
            if not found and random.random() < 0.08:
                found = True
                self.morale = clamp(self.morale + 4, 0, 100)
                print("You crest a ridge to a ridiculous view. Morale soars.")

        # Extra exertion cost for hiking beyond normal drift
        extra_energy = min(12, int(hours * 3))  # ~3 energy per hour
        extra_water  = round(0.12 * hours, 2)   # +0.12 L per hour
        mult = self.job_perks.get('hike_energy_mult', 1.0)
        self.energy = clamp(self.energy - int(extra_energy * mult), 0, 100)
        self.water  = clamp(self.water  - extra_water, 0, self.water_cap_liters)

        # Pet comes along if present
        if self.pet:
            self.pet.energy = clamp(self.pet.energy - max(6, int(hours * 2)), 0, 100)
            self.pet.bond   = clamp(self.pet.bond + 2, 0, 100)

        print(f"You return after ~{hours:.1f}h. House {int(self.battery)}% | "
              f"{'EV ' + str(int(self.ev_battery)) + '%' if self.mode=='electric' else 'Fuel ' + f'{self.fuel_gal:.1f} gal'} | "
              f"Water {self.water:.1f}L | Energy {int(self.energy)}.")

    # ---------- Moab Shop ----------
    def shop(self):
        if self.location != 'moab':
            print("No outfitter here. Try Moab.")
            return
        print("Moab Outfitters — items (BUY <item> [qty])")
        print("  food     $5 each (rations)             → +1 food (cap {})".format(self.food_cap_rations))
        print("  water    $1 / L (jugs)                 → +1.0 L water (cap {:.0f} L)".format(self.water_cap_liters))
        print("  solar    $400 per 200W panel           → +200W solar (cap {}W)".format(self.solar_cap_watts))
        print("  wind     $600 per 300W turbine         → +300W wind  (cap {}W)".format(self.wind_cap_watts))
        print("  battery  $1200 per module              → +40 mi EV range (electric)")
        print("  storage  $300 per module               → +10L water cap & +5 rations (to max caps)")
        print("  tent     $150                          → improves dispersed camping")
        disc = int(self.job_perks.get('shop_discount', 0)*100)
        if disc: print(f"  * {disc}% job discount (Mechanic) applies to upgrades.")
        print(f"Cash: ${self.cash:.0f} | Installed: {self.solar_watts}W solar, {self.wind_watts}W wind, Tent: {'yes' if self.has_tent else 'no'}")
        print(f"Caps: Solar {self.solar_cap_watts}W | Wind {self.wind_cap_watts}W | Water {self.water_cap_liters:.0f}L | Food {self.food_cap_rations}")

    def buy(self, item, qty=1):
        if self.location != 'moab':
            print("You need to be in Moab to buy gear."); return
        item = item.lower()
        if qty <= 0: qty = 1

        base_prices = {'food':5, 'water':1, 'solar':400, 'wind':600, 'battery':1200, 'storage':300, 'tent':150}
        if item not in base_prices:
            print("Unknown item. Try: food, water, solar, wind, battery, storage, tent."); return

        # Job discount on upgrade-y items
        discountable = {'solar','wind','battery','storage','tent'}
        price = base_prices[item] * qty
        if item in discountable:
            price *= (1.0 - self.job_perks.get('shop_discount', 0.0))

        if self.cash < price:
            print(f"Not enough cash (${self.cash:.0f}). This costs ${price:.0f}."); return

        # Apply effects with caps
        if item == 'food':
            before = self.food
            self.food = min(self.food + qty, self.food_cap_rations)
            purchased = self.food - before
        elif item == 'water':
            before = self.water
            self.water = clamp(self.water + 1.0*qty, 0, self.water_cap_liters)
            purchased = round(self.water - before, 1)
        elif item == 'solar':
            before = self.solar_watts
            self.solar_watts = min(self.solar_watts + 200*qty, self.solar_cap_watts)
            purchased = self.solar_watts - before
        elif item == 'wind':
            before = self.wind_watts
            self.wind_watts = min(self.wind_watts + 300*qty, self.wind_cap_watts)
            purchased = self.wind_watts - before
        elif item == 'battery':
            if self.mode != 'electric':
                print("Battery modules affect EV range (MODE electric).")
            before = self.ev_range_mi
            self.ev_range_mi = min(self.ev_range_mi + 40*qty, 360)
            purchased = self.ev_range_mi - before
        elif item == 'storage':
            before_w = self.water_cap_liters
            before_f = self.food_cap_rations
            # Each module: +10L water cap and +5 rations, respecting vehicle max caps
            self.water_cap_liters = min(self.water_cap_liters + 10*qty, self.max_water_cap)
            self.food_cap_rations = min(self.food_cap_rations + 5*qty,  self.max_food_cap)
            purchased = (self.water_cap_liters - before_w, self.food_cap_rations - before_f)
        else:  # tent
            if self.has_tent:
                print("You already own a tent."); return
            self.has_tent = True
            purchased = 1

        self.cash -= price
        print(f"Purchased {qty} × {item} for ${price:.0f}. Cash left: ${self.cash:.0f}. Gained: {purchased}")
        if item in ('solar','wind','battery','storage'):
            print(f"Upgrades — solar: {self.solar_watts}W | wind: {self.wind_watts}W | EV range: {self.ev_range_mi} mi | caps: {self.water_cap_liters:.0f}L/{self.food_cap_rations} rations")

    # ---------- Charging / Refueling ----------
    def charge(self, method):
        method = (method or '').lower()
        if self.mode != 'electric':
            print("You're not in electric mode. Switch with: MODE electric")
            return
        if method not in ('station','solar','wind'):
            print("CHARGE how? Options: station | solar | wind"); return

        if method == 'station':
            if self.location != 'moab':
                print("Fast charger unavailable here. Try Moab.")
                return
            hours = 1.0
            add_pct = 40.0  # ~one-hour fast charge
            cost = add_pct * 0.5  # $0.50 per %
            if self.cash < cost:
                print(f"Charging costs ${cost:.0f}. You have ${self.cash:.0f}."); return
            self.cash -= cost
            self.ev_battery = clamp(self.ev_battery + add_pct, 0, 100)
            self.advance(int(hours*60))
            print(f"Charged {add_pct:.0f}% at station in {hours:.1f}h. EV battery: {self.ev_battery:.0f}% | Cash ${self.cash:.0f}.")
        elif method == 'solar':
            # Off-grid solar session — slower, weather/site dependent
            hours = 2.0
            sol = (self.node().get('resources', {}) or {}).get('solar', 'fair')
            site = {'excellent':1.0, 'good':0.75, 'fair':0.5, 'poor':0.25}.get(sol, 0.5)
            add_pct = (self.solar_watts / 1000.0) * 8.0 * site  # 2h @ ~4%/h per kW w/ site factor
            if add_pct <= 0.1:
                print("You need solar panels installed to gain meaningful charge.")
            self.ev_battery = clamp(self.ev_battery + add_pct, 0, 100)
            self.battery = clamp(self.battery + add_pct, 0, 100)
            self.advance(int(hours*60))
            print(f"Solar charging for {hours:.1f}h adds ~{add_pct:.1f}%. EV battery: {self.ev_battery:.0f}%.")
        else:  # wind
            hours = 2.0
            w = derive_weather(self.node(), self.minutes)
            wind_factor = {'low':0.2,'medium':0.6,'high':1.0}[w['wind']]
            add_pct = (self.wind_watts / 300.0) * 2.0 * wind_factor  # 2h session baseline
            if add_pct <= 0.1:
                print("You need a wind turbine (and some wind) to gain meaningful charge.")
            self.ev_battery = clamp(self.ev_battery + add_pct, 0, 100)
            self.battery = clamp(self.battery + add_pct, 0, 100)
            self.advance(int(hours*60))
            print(f"Wind charging for {hours:.1f}h adds ~{add_pct:.1f}%. EV battery: {self.ev_battery:.0f}%.")

    def refuel(self, gallons):
        if self.mode != 'fuel':
            print("You're not in fuel mode. Switch with: MODE fuel")
            return
        if self.location != 'moab':
            print("No reliable fuel here. Try Moab."); return
        try:
            g = float(gallons)
        except Exception:
            print("REFUEL <gallons>"); return
        if g <= 0: print("That’s not how fuel works."); return
        price = 4.00
        cost = g * price
        if self.cash < cost:
            print(f"Need ${cost:.0f}; you have ${self.cash:.0f}."); return
        self.cash -= cost
        self.fuel_gal += g
        self.advance(10)  # quick stop
        print(f"Added {g:.1f} gal for ${cost:.0f}. Fuel now {self.fuel_gal:.1f} gal. Cash ${self.cash:.0f}.")

    # ---------- Mode switch ----------
    def set_mode(self, mode):
        m = (mode or '').lower()
        if m not in ('electric','fuel'):
            print("MODE electric | MODE fuel"); return
        self.mode = m
        print(f"Drivetrain set to {self.mode.upper()}.")

    def node(self):
        return self.world.nodes[self.location]

    def advance(self, minutes):
        # Advance time in 15-min ticks so passive systems apply
        for _ in range(minutes // TURN_MINUTES):
            self.minutes += TURN_MINUTES

            # Passive drains (scale by house capacity: bigger packs drift slower)
            self.water  = clamp(self.water - 0.03, 0, self.water_cap_liters)
            self.energy = clamp(self.energy - 0.8, 0, 100)
            self.battery = clamp(self.battery - (0.2 / self.house_cap), 0, 100)
            if self.pet: self.pet.tick(TURN_MINUTES)

            # Daylight solar → HOUSE battery (site quality)
            if is_daylight(self.minutes) and self.solar_watts > 0:
                n = self.node()
                sol = (n.get('resources', {}) or {}).get('solar', 'fair')
                site = {'excellent':1.0, 'good':0.75, 'fair':0.5, 'poor':0.25}.get(sol, 0.5)
                per_hour = (self.solar_watts / 1000.0) * 6.0 * site / self.house_cap
                self.battery = clamp(self.battery + per_hour / 4.0, 0, 100)

    # ----- Actions -----
    def look(self):
        n = self.node()
        w = derive_weather(n, self.minutes)
        biome = n.get('biome','').replace('_',' ')
        elev = n.get('elevation_ft','?')
    
        print(f"You are at {n['name']}. {biome} at {elev} ft.")
    
        desc = n.get('description')
        if desc:
            print(desc)
    
        print(f"Time: {minutes_to_hhmm(self.minutes)} | Weather: {describe_weather(w)}.")
        print(f"Resources — water: {n['resources'].get('water','?')}, "
              f"food: {n['resources'].get('food','?')}, "
              f"solar: {n['resources'].get('solar','?')}, "
              f"wind: {n['resources'].get('wind','?')}.")
    
        if n.get('pet_adoption'):
            print("You spot a rescue meetup. You could ADOPT PET here.")
        if self.pet:
            print(f"Your companion {self.pet.name} watches the horizon. "
                  f"Bond {int(self.pet.bond)}%. Energy {int(self.pet.energy)}%.")

    def status(self):
        print(f"{self.player_name} — {self.vehicle_color.title()} {VEHICLES[self.vehicle_type]['label']} | Job: {JOBS[self.job]['label']}")
        print(f"Location: {self.node()['name']} | {minutes_to_hhmm(self.minutes)}")
        print(f"House Battery: {int(self.battery)}%  (cap x{self.house_cap})")
        print(f"Stores: Water {self.water:.1f}/{self.water_cap_liters:.0f} L | Food {self.food}/{self.food_cap_rations} rations | Cash ${self.cash:.0f}")
        print(f"Upgrades: Solar {self.solar_watts}/{self.solar_cap_watts} W | Wind {self.wind_watts}/{self.wind_cap_watts} W | Tent: {'yes' if self.has_tent else 'no'}")
        if self.mode == 'electric':
            print(f"Mode: ELECTRIC | EV Battery: {self.ev_battery:.0f}% | Range(full): {self.ev_range_mi} mi")
        else:
            print(f"Mode: FUEL | Fuel: {self.fuel_gal:.1f}/{self.fuel_tank_gal} gal | MPG: {self.mpg}")
        if self.pet:
            p = self.pet
            print(f"Pet {p.name}: Bond {int(p.bond)} | Energy {int(p.energy)} | Paw {int(p.paw)} | Alert {int(p.alert)} | Guard {'ON' if p.guard_mode else 'OFF'}")

    def show_map(self):
        n = self.node()
        print(f"From {n['name']} you can reach:")
        for c in n.get('connections', []):
            other = self.world.nodes[c['to']]
            print(f"  - {other['name']} ({c.get('road','?')}, {c.get('miles','?')} mi, grade {c.get('grade','mixed')})")
        print("Use: ROUTE TO <place>")

    def route_to(self, dest_key):
        nid = self.world.find_node(dest_key)
        if not nid:
            print("I don't recognize that destination."); return
        if nid == self.location:
            print("You're already here."); return
        path, total_turns = dijkstra_route(self.world, self.location, nid, self.minutes)
        if not path:
            print("No route found."); return
        self.route = path
        self.route_idx = 0
        hours = total_turns * TURN_MINUTES / 60
        names = " → ".join(self.world.nodes[a]['name'] for a,_,_ in path) + f" → {self.world.nodes[nid]['name']}"
        print(f"Route plotted ({hours:.1f}h est): {names}")
        print("Use: DRIVE to set off.")

    def drive(self):
        if not self.route:
            print("No route plotted. Use: ROUTE TO <place>"); return
        if self.route_idx >= len(self.route):
            print("Route already complete."); return

        frm, to, conn = self.route[self.route_idx]
        turns, w = edge_drive_turns(self.world, frm, conn, self.minutes)
        hours = turns * TURN_MINUTES / 60.0
        miles = float(conn.get('miles', 10))

        # Energy check
        if self.mode == 'electric':
            needed_pct = (miles / max(1.0, self.ev_range_mi)) * 100.0
            if self.ev_battery < needed_pct:
                print(f"Not enough charge for {miles:.0f} mi. Need ~{needed_pct:.1f}% EV; have {self.ev_battery:.1f}%.")
                print("Try: CHARGE station (Moab), CHARGE solar, or CHARGE wind."); return
            self.ev_battery = clamp(self.ev_battery - needed_pct, 0, 100)
        else:
            needed_gal = miles / max(1.0, self.mpg)
            if self.fuel_gal < needed_gal:
                print(f"Not enough fuel for {miles:.0f} mi. Need ~{needed_gal:.1f} gal; have {self.fuel_gal:.1f}.")
                print("Try: REFUEL in Moab or adjust your route."); return
            self.fuel_gal = max(0.0, self.fuel_gal - needed_gal)
            # Alternator tops up HOUSE battery on fuel rigs
            self.battery = clamp(self.battery + (2.0*hours)/self.house_cap, 0, 100)

        # Travel drains
        self.water  = clamp(self.water - 0.1*hours, 0, self.water_cap_liters)
        self.energy = clamp(self.energy - 6.0*hours, 0, 100)
        if self.pet:
            self.pet.energy = clamp(self.pet.energy - 4.0*hours, 0, 100)
            self.pet.alert  = clamp(self.pet.alert + 5.0, 0, 100)

        # Occasional detour
        rng = seeded_rng(frm, to, int(self.minutes/60))
        if rng.random() < 0.06:
            delay = rng.randint(1,3)
            print(f"A detour slows you down (+{delay} turns).")
            turns += delay
            hours = turns * TURN_MINUTES / 60.0

        self.advance(turns*TURN_MINUTES)
        self.location = to
        self.route_idx += 1
        print(f"You arrive at {self.node()['name']} after {hours:.1f}h and {miles:.0f} mi. Weather en route: {describe_weather(w)}.")
        if self.route_idx >= len(self.route):
            print("Route complete.")

    def check_weather(self):
        w = derive_weather(self.node(), self.minutes)
        daylight = "daylight" if is_daylight(self.minutes) else "night"
        print(f"At {self.node()['name']} ({daylight}): {describe_weather(w)}.")

    def camp(self, style):
        style = style.lower()
        if style not in ('stealth','paid','dispersed'):
            print("CAMP how? Options: stealth | paid | dispersed"); return

        # Sleep to 06:00
        now = self.minutes % DAY_MINUTES
        sleep_minutes = ((24*60) - now) + 6*60
        hours = sleep_minutes / 60.0

        # Local weather (for wind)
        w = derive_weather(self.node(), self.minutes)
        wind_level = {'low':0.0,'medium':0.8,'high':1.5}[w['wind']]

        # Scale by installed wind capacity (300W baseline)
        wind_scale = (self.wind_watts / 300.0) if self.wind_watts > 0 else 0.2  # tiny incidental if no turbine
        wind_bonus = wind_level * wind_scale  # % per hour to HOUSE battery

        # Base gains/risks
        if style == 'paid':
            energy_gain, morale_gain, pet_energy, pet_bond = 20, 10, 18, 2
            ranger_knock = 0.01
            note = "Paid site: services, permits, quiet-ish."
        elif style == 'stealth':
            energy_gain, morale_gain, pet_energy, pet_bond = 15, 6, 14, 2
            ranger_knock = 0.08
            if self.node().get('pet_rules') == 'strict': ranger_knock += 0.06
            if self.pet and self.pet.alert > 60:         ranger_knock += 0.04
            note = "Stealth spot: close to town, but keep it low-key."
        else:  # dispersed
            energy_gain, morale_gain, pet_energy, pet_bond = 23, 12, 20, 3
            if self.has_tent:
                energy_gain += 4
                morale_gain += 3
                pet_energy  += 3
                note = "Dispersed with tent: free, solitary, and cozy under the stars."
            else:
                note = "Dispersed site: free, solitary, sky for days."
            in_park = self.location in {'zion','bryce','arches','canyonlands','capitol_reef'}
            ranger_knock = 0.04 if in_park else 0.005

        # Apply overnight effects
        self.battery = clamp(self.battery + (wind_bonus*hours)/self.house_cap - (0.5*hours)/self.house_cap, 0, 100)
        self.water   = clamp(self.water - 0.1*hours, 0, self.water_cap_liters)
        self.food    = max(0, self.food - 1)
        self.energy  = clamp(self.energy + energy_gain, 0, 100)
        self.morale  = clamp(self.morale + morale_gain, 0, 100)
        if self.pet:
            self.pet.energy = clamp(self.pet.energy + pet_energy, 0, 100)
            self.pet.bond   = clamp(self.pet.bond   + pet_bond, 0, 100)

        # Gentle dispersed flavor: signal & epic photo chance
        has_signal = True
        if style == 'dispersed':
            biome = (self.node().get('biome') or '').lower()
            maybe_remote = any(k in biome for k in ['desert','swell','salt','mesa','canyon'])
            rng_sig = seeded_rng(self.location, int(self.minutes/60), 'signal')
            has_signal = not (maybe_remote and rng_sig.random() < 0.6)
            if not has_signal:
                print("No bars out here. Your phone becomes a very expensive paperweight tonight.")

            inc = self.job_perks.get('remote_camp_income', 0)
            if inc and has_signal:
                self.cash += inc
                print(f"You push a little code under the stars (+${inc}).")

            rng_shot = seeded_rng(self.location, int(self.minutes/60), 'epic_shot')
            if rng_shot.random() < 0.35:
                payout = rng_shot.randint(30, 80)
                bonus = 1.0 + self.job_perks.get('epic_bonus', 0.0)
                payout = int(payout * bonus)
                self.cash = max(0, self.cash + payout)
                self.morale = clamp(self.morale + 4, 0, 100)
                self.morale = clamp(self.morale + self.job_perks.get('morale_bonus_dispersed', 0), 0, 100)
                print(f"You capture an epic scene. Future print sales net about ${payout} and your soul hums.")

        # Ranger event?
        rng = seeded_rng(self.location, int(self.minutes/60), style)
        if rng.random() < ranger_knock:
            print("A flashlight sweeps your curtains. A ranger checks on you.")
            if style == 'paid':
                print("Your permit checks out. You roll over and go back to sleep.")
            elif style == 'dispersed':
                print("Friendly reminder about tread-lightly and stay limits. You chat stars and keep it mellow.")
            else:
                fine = 25
                self.cash = max(0, self.cash - fine)
                self.morale = clamp(self.morale - 6, 0, 100)
                print(f"You get a warning and a ${fine} fine. Morale dips.")

        self.advance(sleep_minutes)
        print(f"{note} You camp {style} for {hours:.1f}h. Morning at {minutes_to_hhmm(self.minutes)}. Battery {int(self.battery)}%.")

    def cook(self):
        if self.food <= 0:
            print("You rummage for crumbs. No food to cook."); return
        use_water = 0.5 if self.water >= 0.5 else 0.0
        self.food -= 1
        self.water = clamp(self.water - use_water, 0, self.water_cap_liters)
        self.morale = clamp(self.morale + (8 if use_water>0 else 5), 0, 100)
        self.energy = clamp(self.energy + 6, 0, 100)
        self.advance(TURN_MINUTES)
        print(f"You cook a simple meal (+morale, +energy). Water used: {use_water:.1f}L.")

    def sleep(self):
        self.advance(120)
        self.energy = clamp(self.energy + 12, 0, 100)
        if self.pet: self.pet.energy = clamp(self.pet.energy + 10, 0, 100)
        print(f"You nap for 2h. It's now {minutes_to_hhmm(self.minutes)}.")

    # ----- Pets -----
    def adopt_pet(self):
        if not self.node().get('pet_adoption'):
            print("No adoption event here. Try a larger town/rescue hub."); return
        if self.pet:
            print("You already travel with a loyal companion."); return
        name = random.choice(["Oreo","Mesa","Juniper","Pixel","Bowie","Zion","Havasu"])
        self.pet = Pet(name)
        self.morale = clamp(self.morale + 10, 0, 100)
        print(f"You meet {name}, who promptly claims the passenger seat. Bond +10.")

    def feed_pet(self):
        if not self.pet: print("You travel alone."); return
        if self.food <= 0: print("You need rations to share."); return
        self.food -= 1
        self.pet.bond = clamp(self.pet.bond + 6, 0, 100)
        self.advance(TURN_MINUTES)
        print(f"You feed {self.pet.name}. Bond warms.")

    def water_pet(self):
        if not self.pet: print("You travel alone."); return
        if self.water < 0.3: print("Water is too low."); return
        self.water = clamp(self.water - 0.3, 0, self.water_cap_liters)
        self.pet.bond = clamp(self.pet.bond + 3, 0, 100)
        self.advance(TURN_MINUTES//2)
        print(f"{self.pet.name} drinks happily.")

    def walk_pet(self):
        if not self.pet: print("You travel alone."); return
        self.energy = clamp(self.energy + 2, 0, 100)
        self.pet.energy = clamp(self.pet.energy + 5, 0, 100)
        self.pet.bond = clamp(self.pet.bond + 4, 0, 100)
        self.advance(30)
        print(f"You walk {self.pet.name}. Spirits lift.")

    def play_with_pet(self):
        if not self.pet: print("You travel alone."); return
        self.pet.bond = clamp(self.pet.bond + 5, 0, 100)
        self.morale = clamp(self.morale + 4, 0, 100)
        self.advance(20)
        print(f"You play tug and fetch with {self.pet.name}. Laughter echoes in the van.")

    def command_pet(self, verb):
        if not self.pet: print("You travel alone."); return
        v = verb.strip().upper()
        if v == 'GUARD':
            self.pet.guard_mode = True
            self.pet.alert = clamp(self.pet.alert + 10, 0, 100)
            print(f"{self.pet.name} settles by the door, ears up. Guard mode ON.")
        elif v == 'CALM':
            self.pet.guard_mode = False
            self.pet.alert = clamp(self.pet.alert - 10, 0, 100)
            print(f"{self.pet.name} relaxes. Guard mode OFF.")
        elif v == 'SEARCH':
            rng = seeded_rng(self.location, int(self.minutes/60), 'search')
            if rng.random() < 0.4:
                self.water = clamp(self.water + 1.0, 0, self.water_cap_liters)
                print(f"{self.pet.name} finds a hose bib behind a building. +1.0L water.")
            else:
                print(f"{self.pet.name} sniffs around but finds nothing today.")
            self.advance(TURN_MINUTES)
        elif v == 'HEEL':
            print(f"{self.pet.name} falls in line. It's the little things.")
        elif v == 'FETCH':
            self.morale = clamp(self.morale + 2, 0, 100)
            print(f"{self.pet.name} returns triumphantly with... a glove? Sure, that tracks.")
        else:
            print("Available: HEEL, SEARCH, GUARD, CALM, FETCH.")

# ---------------------------- IO & Loop -------------------------------

HELP_TEXT = """Commands:
  LOOK | STATUS | MAP
  ROUTE TO <place> | DRIVE
  CHECK WEATHER
  CAMP [stealth|paid|dispersed]
  COOK | SLEEP
  HIKE <n|s|e|w|ne|nw|se|sw>
  WORK [photo|dev|mechanic|guide|artist|gig] [hours]
  SHOP | BUY <food|water|solar|wind|battery|storage|tent> [qty]
  MODE <electric|fuel> | CHARGE <station|solar|wind> | REFUEL <gallons>
  ADOPT PET | FEED PET | WATER PET | WALK PET | PLAY WITH PET
  COMMAND PET <HEEL|SEARCH|GUARD|CALM|FETCH>
  HELP | QUIT
"""


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
            print(f"(YAML load failed: {e}. Falling back to JSON.)")
    if nodes is None and os.path.exists(cand_json):
        with open(cand_json, "r", encoding="utf-8") as f:
            nodes = json.load(f)["nodes"]
    if not nodes:
        print("No world data found. Place utah.yaml (or utah.json) next to this script.")
        sys.exit(1)
    return World(nodes)

def pick_from_dict(title, dct):
    print(title)
    keys = list(dct.keys())
    for i, k in enumerate(keys, 1):
        lab = dct[k].get("label", k)
        print(f"  {i}) {lab} [{k}]")
    while True:
        ans = input("> ").strip().lower()
        if ans.isdigit():
            idx = int(ans)-1
            if 0 <= idx < len(keys):
                return keys[idx]
        if ans in dct:
            return ans
        print("Pick by number or key from the list above.")

def character_creation():
    print("=== Character & Vehicle Setup ===")
    name = input("Name (enter to randomize): ").strip()
    if not name:
        name = random.choice(["River", "Juniper", "Sky", "Ash", "Indigo", "Cedar", "Rook"])
    color = input("Vehicle color (e.g., white/sand/forest/red): ").strip() or "white"

    vkey = pick_from_dict("Pick a vehicle type:", VEHICLES)
    jkey = pick_from_dict("Pick a job:", JOBS)

    # Drivetrain
    mode = ""
    while mode not in ("electric", "fuel"):
        mode = input("Drivetrain [electric|fuel]: ").strip().lower() or "electric"

    # Randomized starting cash (seeded so same choices = same roll)
    rng = seeded_rng(name, color, vkey, jkey, mode)
    start_cash = rng.randint(500, 2000)

    cfg = {
        "name": name, "color": color,
        "vehicle_key": vkey, "job_key": jkey,
        "mode": mode,
        "start_cash": float(start_cash)
    }
    print(f"Welcome, {name}. {color.title()} {VEHICLES[vkey]['label']} | {JOBS[jkey]['label']} | Start cash: ${start_cash}")
    return cfg

def prelude_shopping(game):
    """Let players spend starting cash in Moab before heading out."""
    print("\n=== Moab Outfitters — Prelude ===")
    print("You can buy initial supplies/upgrades within your starting budget.")
    print("Type SHOP to view items, BUY <item> [qty] to purchase, or DONE to begin your journey.")
    while True:
        line = input("\n> ").strip()
        up = line.upper()
        if up == "DONE" or up == "START":
            break
        elif up == "SHOP":
            game.shop()
        elif up.startswith("BUY "):
            parts = line.split()
            item = parts[1] if len(parts) > 1 else ""
            qty = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
            game.buy(item, qty)
        elif up in ("HELP","?"):
            print("Commands: SHOP | BUY <item> [qty] | DONE")
        elif up == "":
            continue
        else:
            print("Use SHOP, BUY ..., or DONE.")

def main():
    world = load_world()
    cfg = character_creation()
    game = Game(world, cfg)
    prelude_shopping(game)

    print("\nNomad IF — Utah slice")
    print("Type HELP for commands. You’re in Moab and the road is yours.\n")
    game.look()

    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGood roads and tailwinds."); break
        if not line: continue
        u = line.upper()

        if u == 'HELP':
            print(HELP_TEXT)
        elif u in ('LOOK','L'):
            game.look()
        elif u in ('STATUS','STATS'):
            game.status()
        elif u == 'MAP':
            game.show_map()
        elif u.startswith('ROUTE TO '):
            game.route_to(line.split(' ', 2)[2])
        elif u == 'DRIVE':
            game.drive()
        elif u == 'CHECK WEATHER':
            game.check_weather()
        elif u.startswith('CAMP'):
            parts = line.split()
            style = parts[1] if len(parts)>1 else ''
            game.camp(style)
        elif u == 'COOK':
            game.cook()
        elif u == 'SLEEP':
            game.sleep()
        elif u.startswith('HIKE'):
            parts = line.split()
            d = parts[1] if len(parts) > 1 else ''
            game.hike(d)
        elif u == 'SHOP':
            game.shop()
        elif u.startswith('BUY '):
            parts = line.split()
            item = parts[1] if len(parts) > 1 else ''
            qty  = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
            game.buy(item, qty)
        elif u.startswith('MODE '):
            game.set_mode(line.split(' ', 1)[1])
        elif u.startswith('CHARGE'):
            parts = line.split()
            method = parts[1] if len(parts) > 1 else ''
            game.charge(method)
        elif u.startswith('REFUEL'):
            parts = line.split()
            gallons = parts[1] if len(parts) > 1 else ''
            game.refuel(gallons)
        elif u == 'ADOPT PET':
            game.adopt_pet()
        elif u == 'FEED PET':
            game.feed_pet()
        elif u == 'WATER PET':
            game.water_pet()
        elif u == 'WALK PET':
            game.walk_pet()
        elif u == 'PLAY WITH PET':
            game.play_with_pet()
        elif u.startswith('COMMAND PET'):
            verb = line.split(' ', 2)[2] if len(line.split(' ', 2))>2 else ''
            game.command_pet(verb)
        elif u in ('QUIT','EXIT'):
            print("You turn the key, and the road beckons. Bye."); break
        elif u.startswith('WORK'):
            parts = line.split()
            kind  = parts[1] if len(parts)>1 and parts[1].lower() not in ('1','2','3','4','5','6') else ''
            hours = parts[2] if len(parts)>2 else (parts[1] if len(parts)>1 and parts[1].isdigit() else None)
            game.work(kind, hours)
        else:
            print("Unknown command. Type HELP.")

if __name__ == "__main__":
    main()
