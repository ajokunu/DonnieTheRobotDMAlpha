# combat_display.py
"""
DM Donnie Combat Display System
Auto-updates separate combat status message in Discord channel
"""

import asyncio
import discord
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class CombatDisplay:
    """Manages persistent combat status message"""
    message: Optional[discord.Message] = None
    channel_id: int = None
    last_update: float = 0.0

class CombatDisplayManager:
    """Handles automatic combat status updates in separate messages"""
    
    def __init__(self, bot):
        self.bot = bot
        self.displays: Dict[int, CombatDisplay] = {}
        self.update_queue = asyncio.Queue()
        self.running = False
        
    async def start(self):
        """Start the display updater"""
        if self.running:
            return
        
        self.running = True
        asyncio.create_task(self._update_loop())
        print("✅ Combat display manager started")
    
    async def _update_loop(self):
        """Background update loop"""
        while self.running:
            try:
                update_data = await asyncio.wait_for(self.update_queue.get(), timeout=1.0)
                await self._process_update(update_data)
                self.update_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"❌ Display update error: {e}")
                await asyncio.sleep(1)
    
    async def _process_update(self, update_data: Dict[str, Any]):
        """Process single display update"""
        try:
            channel_id = update_data["channel_id"]
            combat_manager = update_data["combat_manager"]
            
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            
            embed = self._build_embed(combat_manager)
            display = self.displays.get(channel_id)
            
            if not display or not display.message:
                # Create new display
                message = await channel.send(embed=embed)
                self.displays[channel_id] = CombatDisplay(
                    message=message,
                    channel_id=channel_id,
                    last_update=asyncio.get_event_loop().time()
                )
                print(f"✅ Created combat display for channel {channel_id}")
            else:
                # Update existing
                try:
                    await display.message.edit(embed=embed)
                    display.last_update = asyncio.get_event_loop().time()
                except discord.NotFound:
                    # Message deleted, create new
                    message = await channel.send(embed=embed)
                    display.message = message
                    display.last_update = asyncio.get_event_loop().time()
                
        except Exception as e:
            print(f"❌ Failed to update combat display: {e}")
    
    def _build_embed(self, combat_manager) -> discord.Embed:
        """Build combat status embed"""
        embed = discord.Embed(
            title="⚔️ Combat Status",
            color=0xFF4500
        )
        
        # Round info
        if combat_manager.phase.value == "active":
            embed.add_field(
                name="📊 Combat Info",
                value=f"**Round:** {combat_manager.round_number}\n**Phase:** Active",
                inline=True
            )
        else:
            embed.add_field(
                name="📊 Combat Info", 
                value=f"**Phase:** {combat_manager.phase.value.title()}",
                inline=True
            )
        
        # Initiative order
        if combat_manager.initiative_order:
            init_lines = []
            for i, combatant_id in enumerate(combat_manager.initiative_order):
                combatant = combat_manager.combatants.get(combatant_id)
                if not combatant:
                    continue
                
                # Current turn indicator
                indicator = "▶️" if i == combat_manager.turn_index else "⏸️"
                
                # Name and initiative
                name = combatant.name
                init_score = combatant.initiative or "?"
                
                # Health status (NO COLOR CODING for enemies per request)
                health_status = ""
                if combatant.is_player and combatant.current_hp is not None and combatant.max_hp is not None:
                    health_status = f" ({combatant.current_hp}/{combatant.max_hp} HP)"
                elif not combatant.is_player and combatant.current_hp is not None:
                    if combatant.current_hp <= 0:
                        health_status = " (Down)"
                    # No other health info for enemies
                
                # Conditions
                conditions = ""
                if combatant.conditions:
                    conditions = f" [{', '.join(combatant.conditions)}]"
                
                init_lines.append(f"{indicator} **{name}** (Init {init_score}){health_status}{conditions}")
            
            embed.add_field(
                name="🎲 Initiative Order",
                value="\n".join(init_lines),
                inline=False
            )
        
        # Current turn
        current = combat_manager.get_current_combatant()
        if current and combat_manager.phase.value == "active":
            embed.add_field(
                name="👤 Current Turn",
                value=f"**{current.name}** - {'Player' if current.is_player else 'NPC'}",
                inline=True
            )
        
        # Battlefield
        if combat_manager.battlefield_description:
            battlefield = combat_manager.battlefield_description
            if len(battlefield) > 100:
                battlefield = battlefield[:97] + "..."
            
            embed.add_field(
                name="🗺️ Battlefield",
                value=battlefield,
                inline=False
            )
        
        # Positions
        positions = self._get_positions(combat_manager)
        if positions:
            embed.add_field(
                name="📍 Positions",
                value=positions,
                inline=False
            )
        
        embed.set_footer(text="Auto-updated • DM controls HP and stats")
        return embed
    
    def _get_positions(self, combat_manager) -> str:
        """Get position summary"""
        position_info = []
        
        for combatant in combat_manager.combatants.values():
            if combatant.position:
                position_info.append(f"{combatant.name}: {combatant.position}")
        
        if position_info:
            return " • ".join(position_info[:4])  # Limit to 4 for space
        
        return ""
    
    async def queue_update(self, channel_id: int, combat_manager):
        """Queue display update (non-blocking)"""
        try:
            update_data = {
                "channel_id": channel_id,
                "combat_manager": combat_manager,
                "timestamp": asyncio.get_event_loop().time()
            }
            self.update_queue.put_nowait(update_data)
        except asyncio.QueueFull:
            print("⚠️ Combat display queue full")
        except Exception as e:
            print(f"❌ Failed to queue combat update: {e}")
    
    async def end_combat(self, channel_id: int):
        """End combat display"""
        display = self.displays.get(channel_id)
        if display and display.message:
            try:
                embed = discord.Embed(
                    title="✅ Combat Ended",
                    description="The battle has concluded.",
                    color=0x32CD32
                )
                await display.message.edit(embed=embed)
                
                # Clean up after delay
                await asyncio.sleep(30)
                try:
                    await display.message.delete()
                except discord.NotFound:
                    pass  # Already deleted
            except (discord.NotFound, Exception) as e:
                if not isinstance(e, discord.NotFound):
                    print(f"⚠️ Error cleaning up combat display: {e}")
            
            if channel_id in self.displays:
                del self.displays[channel_id]