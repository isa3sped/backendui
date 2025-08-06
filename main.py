from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from threading import Lock

app = FastAPI()

# Allow requests from GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://isa3sped.github.io", "https://your-frontend-domain.com"], # Add your frontend domain if deployed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory command queue
command_queue = []

# In-memory player info storage
player_data: Dict[str, Dict[str, Any]] = {}
player_data_lock = Lock()


# --- ENHANCED MODELS ---
# These now match the comprehensive structure the plugin sends.
class CoordsInfo(BaseModel):
    x: float
    y: float
    z: float
    world: str

class EnchantmentInfo(BaseModel):
    type: str
    level: int

class AttributeModifierInfo(BaseModel):
    attribute: str
    name: str
    amount: float
    operation: str
    slot: Optional[str] = None

class ItemInfo(BaseModel):
    material: str
    amount: int
    displayName: Optional[str] = ""
    damage: Optional[int] = 0
    maxDurability: Optional[int] = 0
    durabilityPercentage: Optional[float] = 100.0
    enchantments: Optional[List[EnchantmentInfo]] = []
    lore: Optional[List[str]] = []
    customModelData: Optional[int] = None
    attributeModifiers: Optional[List[AttributeModifierInfo]] = []
    itemFlags: Optional[List[str]] = []
    nbtTags: Optional[Dict[str, Any]] = {}

class ArmorInfo(BaseModel):
    helmet: Optional[ItemInfo] = None
    chestplate: Optional[ItemInfo] = None
    leggings: Optional[ItemInfo] = None
    boots: Optional[ItemInfo] = None

class PotionEffectInfo(BaseModel):
    type: str
    amplifier: int
    duration: int
    durationSeconds: float
    isAmbient: bool
    hasParticles: bool
    hasIcon: bool
    source: Optional[str] = "unknown"

class EntityInfo(BaseModel):
    name: str
    type: str
    distance: float
    location: CoordsInfo

class StatusInfo(BaseModel):
    health: float
    maxHealth: float
    absorption: Optional[float] = 0.0
    foodLevel: int
    saturation: float
    exhaustion: float
    level: int
    exp: float
    totalExp: int
    gameMode: str
    isOp: bool
    isFlying: bool
    allowFlight: bool
    isSneaking: bool
    isSprinting: bool
    isSwimming: bool
    isGliding: bool
    isBlocking: bool
    effects: List[PotionEffectInfo]

class WorldInfo(BaseModel):
    name: str
    weather: str
    isRaining: bool
    isThundering: bool
    temperature: float
    humidity: float
    time: int
    timeOfDay: str

class PlayerInfo(BaseModel):
    name: str
    coords: CoordsInfo
    inventory: Optional[List[ItemInfo]] = []
    armor: Optional[ArmorInfo] = None
    offhand: Optional[ItemInfo] = None
    enderChest: Optional[List[ItemInfo]] = []
    status: Optional[StatusInfo] = None
    world: Optional[WorldInfo] = None
    nearbyEntities: Optional[List[EntityInfo]] = []
    currentAction: Optional[str] = "idle"
    heldItem: Optional[ItemInfo] = None

# --- The rest of your models are fine ---
class Command(BaseModel):
    player: Optional[str] = None
    command: str
    args: List[str]

class InventoryChange(BaseModel):
    player: str
    action: str  # "add" or "remove"
    item: str


# Command system
@app.post("/api/command")
async def receive_command(cmd: Command):
    print(f"Received: /{cmd.command} {' '.join(cmd.args)} (Player: {cmd.player or 'None'})")
    command_queue.append(cmd.dict())
    return {"status": "ok", "queued": cmd.dict()}

@app.get("/api/command")
async def get_next_command():
    if command_queue:
        return {"command": command_queue.pop(0)}
    return {"command": None}

# Keep-alive check
@app.get("/")
async def keep_alive():
    return JSONResponse(content={"status": "I'm alive!"})

# Player data update from plugin
# This endpoint now correctly validates the new data structure
@app.post("/api/coords")
async def update_player_info(info: PlayerInfo):
    with player_data_lock:
        # Use .dict() to convert the Pydantic model to a dictionary for storage
        player_data[info.name] = info.dict()
    return {"status": "updated"}

# Get current data for all players
@app.get("/api/coords")
async def get_all_player_info():
    with player_data_lock:
        return {"players": player_data}

# Request item addition/removal
@app.post("/api/coords/inventory")
async def change_inventory(change: InventoryChange):
    if change.action not in ["add", "remove"]:
        return JSONResponse(status_code=400, content={"error": "Invalid action"})

    cmd = {
        "player": change.player,
        "command": "inventory_edit",
        "args": [change.action, change.item],
    }
    command_queue.append(cmd)
    return {"status": "queued", "command": cmd}

# Sabotage player (reduce attack damage)
@app.post("/api/sabotage/{player_name}")
async def sabotage_player(player_name: str):
    cmd = {
        "command": "attribute",
        "args": [player_name, "minecraft:generic.attack_damage", "base", "set", "0.5"]
    }
    command_queue.append(cmd)
    return {"status": "sabotaged", "player": player_name}

# Unsabotage player (restore normal attack damage)
@app.post("/api/unsabotage/{player_name}")
async def unsabotage_player(player_name: str):
    cmd = {
        "command": "attribute", 
        "args": [player_name, "minecraft:generic.attack_damage", "base", "set", "1.0"]
    }
    command_queue.append(cmd)
    return {"status": "unsabotaged", "player": player_name}

# Regear player with full diamond gear and enchantments
@app.post("/api/regear/{player_name}")
async def regear_player(player_name: str):
    # Diamond armor with enchantments
    armor_commands = [
        # Diamond Helmet with enchantments
        {
            "command": "give",
            "args": [player_name, "diamond_helmet{Enchantments:[{id:\"minecraft:protection\",lvl:3},{id:\"minecraft:unbreaking\",lvl:3},{id:\"minecraft:respiration\",lvl:3},{id:\"minecraft:aqua_affinity\",lvl:1}]}", "1"]
        },
        # Diamond Chestplate with enchantments
        {
            "command": "give", 
            "args": [player_name, "diamond_chestplate{Enchantments:[{id:\"minecraft:protection\",lvl:3},{id:\"minecraft:unbreaking\",lvl:3}]}", "1"]
        },
        # Diamond Leggings with enchantments
        {
            "command": "give",
            "args": [player_name, "diamond_leggings{Enchantments:[{id:\"minecraft:protection\",lvl:3},{id:\"minecraft:unbreaking\",lvl:3}]}", "1"]
        },
        # Diamond Boots with enchantments
        {
            "command": "give",
            "args": [player_name, "diamond_boots{Enchantments:[{id:\"minecraft:protection\",lvl:3},{id:\"minecraft:unbreaking\",lvl:3},{id:\"minecraft:feather_falling\",lvl:4},{id:\"minecraft:depth_strider\",lvl:3}]}", "1"]
        },
        # Bow with enchantments
        {
            "command": "give",
            "args": [player_name, "bow{Enchantments:[{id:\"minecraft:power\",lvl:5},{id:\"minecraft:punch\",lvl:2},{id:\"minecraft:flame\",lvl:1},{id:\"minecraft:infinity\",lvl:1},{id:\"minecraft:unbreaking\",lvl:3}]}", "1"]
        },
        # Crossbow with enchantments
        {
            "command": "give",
            "args": [player_name, "crossbow{Enchantments:[{id:\"minecraft:quick_charge\",lvl:3},{id:\"minecraft:multishot\",lvl:1},{id:\"minecraft:piercing\",lvl:4},{id:\"minecraft:unbreaking\",lvl:3}]}", "1"]
        },
        # Diamond Pickaxe with enchantments
        {
            "command": "give",
            "args": [player_name, "diamond_pickaxe{Enchantments:[{id:\"minecraft:efficiency\",lvl:5},{id:\"minecraft:unbreaking\",lvl:3},{id:\"minecraft:fortune\",lvl:3}]}", "1"]
        },
        # Diamond Axe with enchantments
        {
            "command": "give",
            "args": [player_name, "diamond_axe{Enchantments:[{id:\"minecraft:efficiency\",lvl:5},{id:\"minecraft:unbreaking\",lvl:3},{id:\"minecraft:fortune\",lvl:3}]}", "1"]
        },
        # Diamond Shovel with enchantments
        {
            "command": "give",
            "args": [player_name, "diamond_shovel{Enchantments:[{id:\"minecraft:efficiency\",lvl:5},{id:\"minecraft:unbreaking\",lvl:3},{id:\"minecraft:fortune\",lvl:3}]}", "1"]
        },
        # Diamond Hoe with enchantments
        {
            "command": "give",
            "args": [player_name, "diamond_hoe{Enchantments:[{id:\"minecraft:efficiency\",lvl:5},{id:\"minecraft:unbreaking\",lvl:3},{id:\"minecraft:fortune\",lvl:3}]}", "1"]
        },
        # Trident with enchantments
        {
            "command": "give",
            "args": [player_name, "trident{Enchantments:[{id:\"minecraft:riptide\",lvl:3},{id:\"minecraft:mending\",lvl:1},{id:\"minecraft:unbreaking\",lvl:3}]}", "1"]
        },
        # Golden Apples (4 max)
        {
            "command": "give",
            "args": [player_name, "enchanted_golden_apple", "4"]
        },
        # Wind Charges (2 stacks = 128)
        {
            "command": "give",
            "args": [player_name, "wind_charge", "64"]
        },
        {
            "command": "give", 
            "args": [player_name, "wind_charge", "64"]
        },
        # Arrows for the bow
        {
            "command": "give",
            "args": [player_name, "arrow", "64"]
        }
    ]
    
    # Queue all commands
    for cmd in armor_commands:
        command_queue.append(cmd)
    
    return {"status": "regeared", "player": player_name, "items_given": len(armor_commands)}

# Flame management endpoints

# Set ability damage for a player and flame type
@app.post("/api/flame/setabilitydamage/{player_name}/{flame_type}/{damage}")
async def set_player_ability_damage(player_name: str, flame_type: str, damage: int):
    cmd = {
        "command": "setabilitydamage",
        "args": [player_name, flame_type.upper(), str(damage)]
    }
    command_queue.append(cmd)
    return {"status": "ability_damage_set", "player": player_name, "flame": flame_type, "damage": damage}

# Set ability duration for a player and flame type
@app.post("/api/flame/setabilityduration/{player_name}/{flame_type}/{duration}")
async def set_player_ability_duration(player_name: str, flame_type: str, duration: int):
    cmd = {
        "command": "setabilityduration",
        "args": [player_name, flame_type.upper(), str(duration)]
    }
    command_queue.append(cmd)
    return {"status": "ability_duration_set", "player": player_name, "flame": flame_type, "duration": duration}

@app.post("/api/flame/set/{player_name}/{flame_type}")
async def set_player_flame(player_name: str, flame_type: str):
    cmd = {
        "command": "flame",
        "args": ["set", player_name, flame_type.upper()]
    }
    command_queue.append(cmd)
    return {"status": "flame_set", "player": player_name, "flame": flame_type}

@app.post("/api/flame/upgrade/{player_name}")
async def upgrade_player_flame(player_name: str):
    cmd = {
        "command": "flame", 
        "args": ["upgrade", player_name]
    }
    command_queue.append(cmd)
    return {"status": "flame_upgraded", "player": player_name}

@app.post("/api/flame/downgrade/{player_name}")
async def downgrade_player_flame(player_name: str):
    cmd = {
        "command": "flame",
        "args": ["unupgrade", player_name]
    }
    command_queue.append(cmd)
    return {"status": "flame_downgraded", "player": player_name}

# Give flame items
@app.post("/api/flame/give/{player_name}/{item_type}")
async def give_flame_item(player_name: str, item_type: str):
    cmd = {
        "command": "flame",
        "args": ["give", player_name, item_type.lower()]
    }
    command_queue.append(cmd)
    return {"status": "item_given", "player": player_name, "item": item_type}

# Run the app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
