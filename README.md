# README

Welcome to Nomads! The only (known) text-based Nomad simulator, created by an
actual nomad.

This game simulates life living in a vehicle and traveling around the country.

## Vehicles

| Vehicle       | Cost  | Traits                                                                 |
|---------------|-------|------------------------------------------------------------------------|
| Prius         | $20k  | 🕵️ Stealth+ · ⛽ Fuel/EV+ · 📦 Storage–– · 🏕 Dispersed–               |
| Subaru        | $25k  | 🏕 Dispersed+ (tent) · 🕵️ Stealth+ · 🐾 Cat Adoption · 📦 Storage–     |
| Truck Camper  | $30k  | 🏕 Dispersed+ (no tent) · 🐕 Dog · 📦 Storage+ · 🕵️ Stealth–           |
| Jeep          | $35k  | 🏕 Dispersed++ (rooftop tent) · 🐕 2xDog · 📦 Storage- · 🕵️ Stealth–   |
| Van           | $50k  | 🏕 Dispersed+ (no tent) · 📦 Storage++ · ☀️ Solar+ · 🕵️ Stealth–        |
| Skoolie       | $75k  | 🏕 Dispersed+ (no tent) · 📦 Storage+++ · ☀️ Solar++ · 🌀 Wind+ · ⛽ Fuel/EV–– · 🕵️ Stealth–– |

---

### Prius — *The Stealth Scout*
- **Cost:** $20k  
- **Range:** 320 mi · **MPG:** 30 · **Fuel Tank:** 14 gal  
- **Storage:** 8 / 20  
- **Traits:** 🕵️ Stealth+ · ⛽ Fuel/EV+ · 📦 Storage–– · 🏕 Dispersed–  

---

### Subaru — *The All-Terrain Companion*
- **Cost:** $25k  
- **Range:** **400 mi** · **MPG:** **32** · **Fuel Tank:** 18.5 gal  
- **Storage:** 12 / 25  
- **Traits:** 🏕 Dispersed+ (tent) · 🕵️ Stealth+ · 🐾 Cat Adoption · 📦 Storage–  

---

### Truck Camper — *The Rugged Nomad*
- **Cost:** $30k  
- **Range:** 220 mi · **MPG:** 15 · **Fuel Tank:** 26 gal  
- **Storage:** 15 / 40  
- **Traits:** 🏕 Dispersed+ (no tent) · 🐕 Pet+ · 📦 Storage+ · 🕵️ Stealth–  

---

### Van — *The Balanced Nomad Rig*
- **Cost:** $50k  
- **Range:** 240 mi · **MPG:** 22 · **Fuel Tank:** 24 gal  
- **Storage:** 20 / 50  
- **Traits:** 🏕 Dispersed+ (no tent) · 📦 Storage++ · ☀️ Solar+ · 🕵️ Stealth–  

---

### Skoolie — *The Rolling Fortress*
- **Cost:** $75k  
- **Range:** 160 mi · **MPG:** 8 · **Fuel Tank:** **50 gal**  
- **Storage:** **50 / 120**  
- **Traits:** 🏕 Dispersed+ (no tent) · 📦 Storage+++ · ☀️ Solar++ · 🌀 Wind+ · ⛽ Fuel/EV–– · 🕵️ Stealth––  

---

### Prius — *The Rogue (Stealth Scout)*
- **Cost:** $20k  
- **Range:** ⭐⭐⭐ (320 mi)  
- **Efficiency:** ⭐⭐⭐⭐ (30 MPG)  
- **Storage:** ⭐ (8 / 20)  
- **Stealth:** ⭐⭐⭐⭐⭐  
- **Traits:** 🕵️ Stealth+ · ⛽ Fuel/EV+ · 📦 Storage–– · 🏕 Dispersed–  

---

### Subaru — *The Ranger (All-Terrain Companion)*
- **Cost:** $25k  
- **Range:** ⭐⭐⭐⭐⭐ (**400 mi**)  
- **Efficiency:** ⭐⭐⭐⭐⭐ (**32 MPG**)  
- **Storage:** ⭐⭐ (12 / 25)  
- **Stealth:** ⭐⭐⭐⭐  
- **Traits:** 🏕 Dispersed+ (tent) · 🕵️ Stealth+ · 🐾 Cat Adoption · 📦 Storage–  

---

### Truck Camper — *The Fighter (Rugged Nomad)*
- **Cost:** $30k  
- **Range:** ⭐⭐ (220 mi)  
- **Efficiency:** ⭐⭐ (15 MPG)  
- **Storage:** ⭐⭐⭐ (15 / 40)  
- **Stealth:** ⭐⭐  
- **Traits:** 🏕 Dispersed+ (no tent) · 🐕 Pet+ · 📦 Storage+ · 🕵️ Stealth–  

---

### Van — *The Paladin (Balanced Nomad Rig)*
- **Cost:** $50k  
- **Range:** ⭐⭐⭐ (240 mi)  
- **Efficiency:** ⭐⭐⭐ (22 MPG)  
- **Storage:** ⭐⭐⭐⭐ (20 / 50)  
- **Stealth:** ⭐⭐  
- **Traits:** 🏕 Dispersed+ (no tent) · 📦 Storage++ · ☀️ Solar+ · 🕵️ Stealth–  

---

### Skoolie — *The Tank (Rolling Fortress)*
- **Cost:** $75k  
- **Range:** ⭐ (160 mi)  
- **Efficiency:** ⭐ (8 MPG)  
- **Storage:** ⭐⭐⭐⭐⭐ (**50 / 120**)  
- **Stealth:** ⭐  
- **Traits:** 🏕 Dispersed+ (no tent) · 📦 Storage+++ · ☀️ Solar++ · 🌀 Wind+ · ⛽ Fuel/EV–– · 🕵️ Stealth––  


## CHARACTERS

| Job          | Label                        | Epic Bonus | Morale Bonus (Dispersed) | Shop Discount | Remote Camp Income | Hike Energy Mult | Hike Find Bonus |
|--------------|------------------------------|------------|--------------------------|---------------|--------------------|------------------|-----------------|
| Artist       | Artist (muse on wheels)      | 0.1        | 3                        | –             | –                  | –                | –               |
| Mechanic     | Mechanic (handy with tools)  | –          | –                        | 0.15          | –                  | –                | –               |
| Photographer | Photographer (eye for light) | 0.25       | –                        | –             | –                  | –                | –               |
| Remote Dev   | Remote Dev (wifi wizard)     | –          | –                        | –             | 30                 | –                | –               |
| Trail Guide  | Trail Guide (path whisperer) | –          | –                        | –             | –                  | 0.8              | 0.1             |

---

### Artist — *The Muse on Wheels*
- **Epic Bonus:** ⭐⭐ (0.1)  
- **Morale (Dispersed):** ⭐⭐⭐⭐ (+3)  
- **Shop/Income/Survival:** ⭐  
- **Traits:** 🎨 Camp Creativity+ · 😊 Morale Aura+ · 🔧 Repairs–  
- **Flavor:** Keeps spirits high at dispersed camps, but not great when the van breaks down.  

---

### Mechanic — *The Engineer*
- **Epic Bonus:** ⭐  
- **Shop Discount:** ⭐⭐⭐⭐ (15%)  
- **Breakdown Recovery:** ⭐⭐⭐⭐  
- **Morale/Charisma:** ⭐  
- **Traits:** 🔧 Repairs++ · 🛠 Breakdown Recovery+ · 😐 Morale–  
- **Flavor:** Keeps the rigs rolling and saves money, but isn’t much of a party at camp.  

---

### Photographer — *The Eye for Light*
- **Epic Bonus:** ⭐⭐⭐⭐⭐ (0.25)  
- **Morale (Events):** ⭐⭐⭐  
- **Storage/Practical Skills:** ⭐  
- **Traits:** 📸 Epic Moments++ · 🎉 Festival Income+ · 😓 Harsh Weather Morale–  
- **Flavor:** Can turn moments into legends and festivals into paydays, but struggles in rough conditions.  

---

### Remote Dev — *The Wifi Wizard*
- **Epic Bonus:** ⭐  
- **Remote Income:** ⭐⭐⭐⭐ (+30)  
- **Energy Usage:** ⭐ (drain heavy)  
- **Traits:** 💻 Camp Income++ · 📡 Signal Required · 🔋 Power Drain–  
- **Flavor:** Brings in steady cash from anywhere with WiFi, but eats solar and net like a hungry dragon.  

---

### Trail Guide — *The Path Whisperer*
- **Epic Bonus:** ⭐⭐ (find bonus 0.1)  
- **Hike Energy Use:** ⭐⭐⭐⭐ (0.8 mult)  
- **Survival/Wild Terrain:** ⭐⭐⭐⭐  
- **Income/Shop:** ⭐  
- **Traits:** 🥾 Survival++ · 🌲 Wild Terrain+ · 💰 Poor Income–  
- **Flavor:** Best in the wild, lowering hiking costs and finding hidden paths, but doesn’t earn much coin.  

---

| Job               | Role / Flavor   | Epic Bonus | Morale     | Shop/Discount | Income     | Survival/Trail | Energy Use | Key Traits                                        |
|-------------------|-----------------|------------|------------|---------------|------------|----------------|------------|---------------------------------------------------|
| **Artist**        | Muse on Wheels  | ⭐⭐⭐⭐   | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐      | ⭐         | ⭐⭐           | ⭐⭐       | 🎨 Creativity+    · 😊 Morale+      · 🔧 Repairs– |
| **Mechanic**      | Engineer        | ⭐         | ⭐⭐       | ⭐⭐⭐⭐⭐    | ⭐⭐⭐⭐   | ⭐⭐⭐⭐       | ⭐⭐⭐⭐   | 🔧 Repairs++      · 🛠 Recovery+    · 😐 Morale–  |
| **Photographer**  | Eye for Light   | ⭐⭐⭐⭐⭐ | ⭐⭐⭐     | ⭐⭐          | ⭐⭐       | ⭐             | ⭐⭐⭐     | 📸 Epic Moments++ · 🎉 Festival+    · 😓 Weather– |
| **Remote Dev**    | Wifi Wizard     | ⭐⭐       | ⭐         | ⭐            | ⭐⭐⭐⭐⭐ | ⭐⭐⭐         | ⭐⭐⭐⭐⭐ | 💻 Income++       · 📡 Signal Req   · 🪫 Drain+   |
| **Guide**         | Trail Whisperer | ⭐⭐⭐     | ⭐⭐⭐⭐   | ⭐⭐⭐        | ⭐⭐⭐     | ⭐⭐⭐⭐⭐     | ⭐         | 🥾 Survival++     · 🌲 Terrain+     · 🔋 Drain–   |

## CHALLENGES

What are the challenges, tasks and quests in the game? What puzzles are there
to solve?

Perhaps you're required to travel to a distant destination but must level up
before you earn the solar/wind capacity to support the distance?

Perhaps you're required to visit the mighty five and 'TAKE PHOTO' at each
location?

Perhaps you're required to attend the speedway event at the salt flats
(photographer bonus)?

Perhaps you're required to guide hikers at each of the mighty five 'GUIDE HIKE'
in each of the parks?

Perhaps the mechanic needs to gather parts from 3-4 different locations in
order to upgrade their vehicle?

Perhaps the artist is invited to showcase art/music at 3-4 of the locations.
'PERFORM' in each location to unlock the upgrade.

Perhaps the remove dev needs to show up on-site in SLC and that becomes an
adventure. (introduce SLC for resources, shopping, etc. Level restricted.)

By completing the tasks, the character unlocks and is gifted their "quest"
item:

Photographer  - camera
Remove worker - laptop
Mechanic      - repair manual
Artist        - guitar
Trail Guide   - deluxe tent

These items increase income earned by 10%.

## ENVIRONMENT

ELEVATION  
This reports the elevation for your location.

WEATHER  
This reports the current weather.

## MAPS [ PENDING ]
Curret map covers the state of Utah for ten locations:

 - Moab (starting point)
 - Arches National Park
 - Canyonlands National Park (should this become three?)
 - Mirror Lake Highway
 - Valley of the Gods
 - Bonneville Salt Flats
 - Bryce Canyon
 - Zion National Park
 - San Rafael Swell
 - Capitol Reef 

At this point, travel is done between these points, with only certain nodes
directly connected. Gas is limited. Water is limited. Be sure to stock up
before venturing into the wild.

I would like to extend this such that each location has it's own mini-map.
Beginning with Arches National Park I'd like to create a n/s/e/w/ne/nw/se/sw
style replica of each park. This lets you virtually visit the park and get to
know the parks themselves through the game. The more accurate the better (down
to which parks have facilities, water, cell service, etc)!

"quick travel" can also be achieved using the ROUTE TO command, but once inside
each location you can manually navigate around using n/s/e/w keys.

Priority:
 - Moab: 
    (N-S strip with Lyon's Park, grocery store, car dealership, mechanic, gas
    station, EV station, RV park and nearby dispersed camping along the river.
 - Arches:
    Replica of the park and connecting (manual) drive from Moab. Include
    the visitor center, restrooms, garbage, water, etc.
 - Canyonlands:
    Replica of the park beginning at Dead Horse Point (unlocks at level N)
    Include nearby dispersed camping plus (limited) park campsites.
 - San Rafael Swell
    Replica of the campground east-to-west plus Buckhorn Draw to the bridge
 - Bonneville Salt Flats
    Replica of the speedway access to the gas station plus nearby dispersed.

## ELECTRICAL SYSTEM

BATTERY  
This gives you a battery status including Load, Percentage and Capacity.

POWER | ELECTRICAL  
This gives you an overview of the entire power/electrical system including Battery, Solar and Wind.

SOLAR  
This gives you a solar panel status including Solar Input Watts, Current and Capacity.
(FIXME: fix solar capacity bug. allows you to buy after capacity reached)

WIND
This gives you a wind turbine status including Wind Input Watts, Current and Capacity.
(FIXME: fix wind capacity bug. allows you to buy after capacity reached)

EV
This gives you an EV status including EV Battery Percentage and Range.

## ACTIONS

READ

### WATCH <something>

WATCH Netflix (easter-egg: randomized Netflix series)
WATCH sunrise
WATCH sunset
WATCH YouTube (easter-egg: randomized vanlife YouTubers series)

HIKE  
This sets you off on a random-length hike, gaining experience but using energy.
(FIXME: add hike descriptions relevant to each region)

(FEED,WATER,WALK,PLAY WITH) PET

WORK

NAP

COOK

EAT

### (INVENTORY | INV | I)
INVENTORY reports current consumables inventory:

meals
water (gallons)
propane
butane
diesel
extra fuel (if mode fuel)

### GARBAGE [ PENDING ]
this needs to be tracked

### STATS
morale     - represents mood & enjoyment in life; increased by (pet, hike, etc); decreased by work.
energy     - represents ability to do things; increased by food, play, exercise; decreased by work.
health     - represents hit points; players can be injured or even die. increased with rest,  food.
confidence - represents confidence in abilities; this stat grows each level. decrease if morale low.
creativity - represents the muse; important for artist/photog. affects epic chances and income.
comfort    - represents livability of the vehicle; fancy vs feral living. increase w/ devices.

Part of the game mechanics include keeping watch over these and fostering them accordingly.

### EXERCISE [ PENDING ]
this needs to be added
- increases all stats on sliding scale (this may have its own exp chart)

### DEVICES
fridge   - provides +5 food and water storage; bonus to morale, comfort
stove    - gives bonus energy, morale and comfort when used to cook
jetboil  - gives bonus energy & morale when used to cook (this should have alternate function)
heater   - diesel heater provides cabin heat during cold weather or winter season (increase comfort, morale)
starlink - guarantees connectivity even when dispersed (increase comfort, morale)

laptop        - increases income for all job types; unlocks for dev at level 10 quest
camera        - increases creativity for all job types; unlocks for photographer at level 10 quest
guitar        - increases morale for all job types; unlocks for artist at level 10 quest
repair manual - increases confidence for all job types; unlocks for mechanic at level 10 quest
deluxe tent   - increases comfort for all job types; unlocks for trail guide at level 10 quest

### REPAIRS [ PENDING ]
this needs to be added
vehicles can have breakdowns and items can wear out

the mechanic role can self-repair a lot of these issues, the others roles cannot.
a visit to the repair shop and some cash are required otherwise.

after level 10 you can purchase the repair manual and learn to repair items.
this can make the mechanic role appealing in this regard.

### REFUEL
refuel vehicle with gasoline

### STARLINK
This outputs realistic metrics from a functioning Starlink device

### WEBOOST
This outputs realistic metrics for a functioning weboost (despite a weboost not
having an interface)

### FRIDGE
This (will) interact with the fridge inventory. better food requires the
fridge.

Installing a fridge avoids food from spoiling overnight. Chance increases in heat.
Installing a fridge reduces the attraction from rodents.

### HEATER
This (will) interact with the diesel heater to increase/decrease the heat based
on the outside temps and comfort value.
