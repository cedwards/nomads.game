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

Photographer - camera
Remove devel - laptop
Mechanic     - toolbox
Artist       - guitar
Trail Guide  - maps

These items increase income earned by 10%.

## ENVIRONMENT

ELEVATION
WEATHER

## ELECTRICAL SYSTEM

BATTERY
POWER | ELECTRICAL
SOLAR
WIND
EV

## ACTIONS

READ

### WATCH <something>

WATCH Netflix (easter-egg: generates random Netflix series output)
WATCH sunrise
WATCH sunset

HIKE

(FEED,WATER,WALK,PLAY WITH) PET

WORK

NAP

COOK

EAT

