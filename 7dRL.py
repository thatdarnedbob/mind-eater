import libtcodpy as libtcod
from math import sqrt
import textwrap
import shelve
import random
import os

# So we have some constants that will useful for code legibility.

SCREEN_WIDTH = 60
SCREEN_HEIGHT = 50

CAMERA_WIDTH = 60
CAMERA_HEIGHT = 43

# format of bottom half of screen:
#-----------------------#----------------------------------#
#PLAYER PARRIES         #                                  #
#PLAYER WOUNDS          #                                  #
#TARGET NAME            #                                  #
#TARGET PARRIES         #                                  #
#TARGET WOUNDS          #                                  #
#abcdefghijklmnopqrstubw#abcdefghijklmnopqrstuvwxyzABCDEFGH#
#
# note: # and - is empty space, but is a real border.
# column 1 (0), column 25 (24), column 60 (59)
# Height = 7
# player info height = 2, width = 23
# enemy info height = 3, width = 23
# log height = 6, width = 34
# all positional variables, except for the entire panel, are relative to the panel's top left corner!

PANEL_X = 0
PANEL_Y = 43
PANEL_HEIGHT = 7
PANEL_WIDTH = 60
PLAYER_INFO_WIDTH = 23
PLAYER_INFO_X = 1
PLAYER_INFO_Y = 1
PLAYER_INFO_HEIGHT = 2
ENEMY_INFO_WIDTH = 23
ENEMY_INFO_HEIGHT = 2
ENEMY_INFO_X = 1
ENEMY_INFO_Y = PLAYER_INFO_Y + PLAYER_INFO_HEIGHT
LOG_WIDTH = 34
LOG_HEIGHT = 5
LOG_LENGTH = 1000
LOG_X = PLAYER_INFO_X + PLAYER_INFO_WIDTH + 1
LOG_Y = 1

MENU_WIDTH = 40
MENU_MAX_HEIGHT = 40

VILLAGE_TILES_HIGH = 5
VILLAGE_TILES_WIDE = 5
VILLAGE_TILE_SIZE = 20

LIMIT_FPS = 25
FOV_ALGO = 0


TORCH_RADIUS = 16

curr_map_width = 102
curr_map_height = 102
# Game loop functions

def main_menu():

	# We set the default values for the main menu here.

	libtcod.console_set_default_background(0, libtcod.darkest_blue)
	libtcod.console_set_default_foreground(0, libtcod.yellow)
	libtcod.console_set_background_flag(0, libtcod.BKGND_DEFAULT)
	libtcod.console_set_alignment(0, libtcod.LEFT)

	while not libtcod.console_is_window_closed():

		# This is necessary to get everything into the new default state, instead of the old black on black.
		libtcod.console_clear(0)

		# Aw cute little hearts. This is pretty much just getting comfortable with mapping ascii

		heart_colors = [libtcod.red, libtcod.green, libtcod.blue, libtcod.yellow, libtcod.orange, libtcod.purple]
		libtcod.console_map_ascii_code_to_font(255, 3, 0)

		#for x in range(0,40):
		#	heart_x = roll(0, SCREEN_WIDTH)
		#	heart_y = roll(0, SCREEN_HEIGHT)
		#	libtcod.console_put_char(0, heart_x, heart_y, 255, libtcod.BKGND_DEFAULT)
		#	libtcod.console_set_char_foreground(0, heart_x, heart_y, random.choice(heart_colors))

		# We present the main menu

		libtcod.console_print(0, SCREEN_WIDTH / 3, SCREEN_HEIGHT / 2 - 3, "a) New Game")
		libtcod.console_print(0, SCREEN_WIDTH / 3, SCREEN_HEIGHT / 2 - 1, "b) Continue")
		libtcod.console_print(0, SCREEN_WIDTH / 3, SCREEN_HEIGHT / 2 + 1, "c) Exit")


		# this sends everything from the console to the screen.

		libtcod.console_flush()

		# some super basic input handling here. The key.c - ord('a') kinda just shanks a 0 - max int out of a lowercase letter

		#key = libtcod.console_wait_for_keypress(True)
		mouse = libtcod.Mouse()
		key = libtcod.Key()

		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)

		index = key.c - ord('a')

		if index == 0:
			new_game()
			play_game()
		elif index == 1:
			load_game()
			play_game()
		elif index == 2:
			exit(0)

	exit(0)


def new_game():
	global player, game_state, game_log, target

	if os.path.isfile('savegame'):
		os.remove('savegame')

	# create player
	player = Object(0, 0, '@', 'the Mind Eater', libtcod.white, walkable=True, always_visible=True, fighter=player_fighter(), mind=player_mind())
	target = None

	make_village_map()
	initialize_fov()

	game_log = []

	log("YOU ARE THE MIND EATER", libtcod.red)
 
	game_state = 'playing'

	player.inventory.append(sword(0, 0))
	player.inventory.append(shield(0, 0))
	player.inventory.append(leather_armor(0, 0))



# With shelve, saving and loading couldn't be easier!

def save_game():
	if os.path.isfile('savegame'):
		os.remove('savegame')
	file = shelve.open('savegame')

	file['cur_map'] = cur_map
	file['objects'] = objects
	file['player_index'] = objects.index(player)
	#file['stairs_index'] = objects.index(stairs)
	file['game_state'] = game_state
	file['game_log'] = game_log

	file.close()

def load_game():
	global cur_map, objects, player, game_state, game_log
	# stairs
	# set state

	if not os.path.isfile('savegame'):
		return False

	file = shelve.open('savegame')

	cur_map = file['cur_map']
	objects = file['objects']
	player = objects[file['player_index']]
	#stairs = objects[file['stairs_index']]
	game_state = file['game_state']
	game_log = file['game_log']

	file.close()

	os.remove('savegame')

	initialize_fov()

def play_game():
	global camera_x, camera_y, key, mouse

	player_action = None

	mouse = libtcod.Mouse()
	key = libtcod.Key()
	(camera_x, camera_y) = (0, 0)

	while not libtcod.console_is_window_closed():
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)

		render_all_night()

		libtcod.console_flush()

		for obj in objects:
			obj.clear()

		# player gets to go

		player_action = handle_keys()
		if player_action == 'exit':
			if game_state is not 'dead':
				save_game()
			exit(0)

		# monsters can go?

		if game_state == 'playing' and player_action == 'took-turn':
			
			for obj in objects:
				if obj.ai:
					obj.ai.take_turn()

# the Object class

class Object:

	def __init__(self, x, y, char, name, color, walkable=True, always_visible=False,
		fighter=None, ai=None, mind=None, item=None):

		self.x = x
		self.y = y
		self.char = char
		self.name = name
		self.color = color
		self.walkable = walkable
		self.always_visible = always_visible

		self.fighter = fighter
		if self.fighter:
			self.fighter.owner = self

		self.ai = ai
		if self.ai:
			self.ai.owner = self

		self.mind = mind
		if self.mind:
			self.mind.owner = self
			self.mind.name = "The mind of a %s."%self.name
			self.mind.desc = "This is a %s's mind. It has stuff."%self.name

		self.inventory = []

		self.item = item
		if self.item:
			self.item.owner = self

		if self.mind and self.fighter:
			# otherwise, a fighter with the parry skill starts off not full.
			self.fighter.parries_left = self.fighter.max_parries

	def move(self, dx, dy):
		new_x = self.x + dx
		new_y = self.y + dy

		if in_range(new_x, new_y) and is_walkable(new_x, new_y):
			self.x = new_x
			self.y = new_y
			return True
		else:
			return False

	def move_towards(self, target_x, target_y):
		dx = target_x - self.x
		dy = target_y - self.y

		if dx is not 0:
			dir_x = dx/abs(dx)
		else:
			dir_x = 0
		
		if dy is not 0:
			dir_y = dy/abs(dy)
		else:
			dir_y = 0

		success = self.move(dir_x, dir_y)
		if not success:
			if roll(0,1) == 0:
				self.move(dir_x, 0)
			else:
				self.move(0, dir_y)

	def distance_to(self, other):
		#return the distance to another obj
		dx = other.x - self.x
		dy = other.y - self.y
		return sqrt(dx ** 2 + dy ** 2)
	 
	def distance(self, x, y):			
		#return the distance to some coordinates			
		return sqrt((x - self.x) ** 2 + (y - self.y) ** 2)	 		

	def send_to_back(self):
		#make this obj be drawn first, so all others appear above it if they're in the same tile.
		global objects
		objects.remove(self)
		objects.insert(0, self)

	def draw(self):
		# only show if it's visible to the player
		if (libtcod.map_is_in_fov(fov_map, self.x, self.y)):
			(x, y) = to_camera_coordinates(self.x, self.y)

			if x is not None:
				#set the color and then draw the character that represents this obj at its position
				libtcod.console_set_char_foreground(board, self.x, self.y, self.color)
				libtcod.console_set_char(board, self.x, self.y, self.char)

		# show if it's set to "always visible" and on an explored tile
		elif self.always_visible and cur_map[self.x][self.y].explored:
			(x, y) = to_camera_coordinates(self.x, self.y)

			if x is not None:
				#set the color and then draw the character that represents this obj at its position
				libtcod.console_set_char_foreground(board, self.x, self.y, self.color*0.5)
				libtcod.console_set_char(board, self.x, self.y, self.char)

	def clear(self):
		#erase the character that represents this obj
		
		(x, y) = to_camera_coordinates(self.x, self.y)
		if x is not None:
			libtcod.console_set_char(board, self.x, self.y, ' ')

	def get_equipped_in_slot(self, slot):
		equipped = None
		for thing in self.inventory:
			if thing.item.slot == slot:
				return thing.item

	def start_with(self, an_item):
		self.inventory.append(an_item)
		if an_item.item.equippable:
			an_item.item.equip(self)

class Fighter:
	# all combat related properties.
	# if an object can deal damage by itself, it has Fighter
	# if an object can take damage, it has Fighter
	# if an object can be interacted with by moving into it, it has Fighter (thanks to cludges!)

	def __init__(self, wounds, defense, power, armor, xp, death_function=None):
		self.base_max_wounds = wounds
		self.wounds = wounds
		self.base_max_parries = defense
		self.parries_left = defense
		self.rested = False
		self.base_power = power
		self.base_armor = armor
		self.xp = xp
		self.death_function = death_function

	@property
	def power(self): # return the actual power by summing up the power bonus from all buffs
		bonus = sum(buff.power_bonus for buff in get_all_buffs(self.owner))
		return self.base_power + bonus

	@property
	def armor(self): # return the actual armor by summing up the armor bonus from all buffs
		bonus = sum(buff.armor_bonus for buff in get_all_buffs(self.owner))
		return self.base_armor + bonus

	@property
	def max_parries(self): # return the actual defense by summing up the defense bonus from all buffs
		bonus = sum(buff.max_parries_bonus for buff in get_all_buffs(self.owner))
		return self.base_max_parries + bonus

	@property
	def max_wounds(self): # return the actual max_wounds by summing up the max_wounds bonus from all buffs
		bonus = sum(buff.max_wounds_bonus for buff in get_all_buffs(self.owner))
		return self.base_max_wounds + bonus

	def attack(self, target):
		target.fighter.take_damage(self.power)

	def take_damage(self, damage):
		if self.parries_left >= 1:
			self.parries_left -= 1
			log(self.owner.name.capitalize() + ' parries the blow!')
		else:
			net_damage = max(0, damage - self.armor)
			self.wounds -= net_damage
			if net_damage == 0:
				log('The blow was absorbed by ' + self.owner.name + '\'s armor!')
			else:
				log('The blow lands solidly on ' + self.owner.name + '!')
			if self.wounds <= 0:
				function = self.death_function
				if function is not None:
					function(self.owner)

				# if the owner is not the player, could give XP to the killer here. Leave that for later though.

	def rest(self):
		if self.rested:
			self.parries_left = min(self.max_parries, self.parries_left + 1)
			self.rested = False
		elif self.parries_left < self.max_parries:
			self.rested = True

def player_fighter():
	return Fighter(wounds=3, defense=0, power=1, armor=0, xp=0, death_function=player_death)

def player_mind():
	# could buffed for testing purposes. should start out all zeros
	return Mind(make_faculty_list(mapping=0, parry=0))

def farmer(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = BasicAI()
	mind_comp = Mind(make_faculty_list(mapping=1, parry=1, first_aid=1, doors=1, dig=1))
	return Object(x, y, 'F', 'farmer', libtcod.yellow, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)

def lumber_worker(x, y):
	fighter_comp = Fighter(wounds = 2, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = BasicAI()
	mind_comp = Mind(make_faculty_list(mapping=1, parry=1, weapon=1, doors=1))
	monster = Object(x, y, 'L', 'lumberjack', libtcod.sepia, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.start_with(axe(x, y))
	return monster

def hunter(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = BasicAI()
	mind_comp = Mind(make_faculty_list(mapping=1, parry=1, weapon=1, stealth=1, search=1, doors=1, run=1))
	return Object(x, y, 'H', 'hunter', libtcod.red, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)

def fisherman(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = BasicAI()
	mind_comp = Mind(make_faculty_list(mapping=1, doors=1, swim=1))
	return Object(x, y, 'A', 'angler', libtcod.light_blue, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)

def guard(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = BasicAI()
	mind_comp = Mind(make_faculty_list(mapping=1, parry=2, weapon=1, armor=1, doors=1, run=1))
	return Object(x, y, 'G', 'guard', libtcod.white, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)

def cow(x, y):
	fighter_comp = Fighter(wounds = 6, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = BasicAI()
	mind_comp = Mind(make_faculty_list(run=1, vault=1))
	return Object(x, y, 'C', 'cow', libtcod.white, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)

def chicken(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 0, armor=0, xp = 0, death_function=monster_death)
	ai_comp = BasicAI()
	mind_comp = Mind(make_faculty_list(search=2, dig=1))
	return Object(x, y, 'c', 'chicken', libtcod.dark_orange, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)

def dog(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = BasicAI()
	mind_comp = Mind(make_faculty_list(mapping=1, stealth=1, search=2, run=1, dig=1, swim=1, vault=1))
	return Object(x, y, 'd', 'dog', libtcod.light_sepia, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)

def door(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 0, armor=0, xp = 0, death_function=door_open_death)
	return Object(x, y, 150, 'door', libtcod.sepia, walkable=True, always_visible=True, fighter=fighter_comp)

def gate(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 0, armor=0, xp = 0, death_function=gate_open_death)
	return Object(x, y, 150, 'gate', libtcod.dark_sepia, walkable=False, always_visible=True, fighter=fighter_comp)

def player_death(player):
	# the game is over
	global game_state
	log('You are slain! The world is safe!', libtcod.green)
	game_state = 'dead'

	player.char = '%'
	player.color = libtcod.dark_red

def monster_death(monster):
	log('The ' + monster.name + ' is dead!  Maybe a mind remains...', libtcod.red)
	monster.char = '%'
	monster.color = libtcod.dark_red
	monster.walkable = True
	monster.fighter = None
	monster.ai = None
	monster.name = 'remains of a ' + monster.name
	monster.send_to_back()

def door_open_death(monster):
	global objects
	log('You shatter the door with a mighty crash!', libtcod.yellow)
	monster.fighter = None
	objects.remove(monster)
	cur_map[monster.x][monster.y].change_type('wood floor')
	initialize_fov()

def gate_open_death(monster):
	global objects
	log('You smash through the gate with a mighty crash!', libtcod.yellow)
	monster.fighter = None
	objects.remove(monster)
	cur_map[monster.x][monster.y].change_type('grass')

def get_all_buffs(buffed):
	# implement buffs later
	buff_list = []

	if buffed.mind is not None:
		buff_list.append(Buff(max_parries_bonus=buffed.mind.skills[1]))

	for thing in buffed.inventory:
		if thing.item is not None and thing.item.equipped:
			buff_list.append(thing.item)

	return buff_list

class Buff:
	def __init__(self, power_bonus=0, armor_bonus=0, max_wounds_bonus=0, max_parries_bonus=0):
		self.power_bonus = power_bonus
		self.armor_bonus = armor_bonus
		self.max_wounds_bonus = max_wounds_bonus
		self.max_parries_bonus = max_parries_bonus

class Mind:
	def __init__(self, skills):
		self.skills = skills
		self.name = ""
		self.desc = ""

class BasicAI:
	# This is AI for a creature that just moves toward the player if it sees them, and tries to attack
	def take_turn(self):
		monster = self.owner

		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			# move towards the player if far away
			if monster.distance_to(player) >= 2:
				monster.move_towards(player.x, player.y)

			elif player.fighter.wounds > 0:
				monster.fighter.attack(player)

			newAI = AlertAI(player.x, player.y)
			monster.ai = newAI
			newAI.owner = monster

class AlertAI():
	# This is an AI that is aware of the pleyer, and moves to kill them.
	def __init__(self, x, y):
		self.target_x = x
		self.target_y = y

	def take_turn(self):
		monster = self.owner

		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			if monster.distance_to(player) >= 2:
				monster.move_towards(player.x, player.y)

			elif player.fighter.wounds > 0:
				monster.fighter.attack(player)
			self.target_x = player.x
			self.target_y = player.y
		else:
			monster.move_towards(self.target_x, self.target_y)

class Item():
	# object can have an item component. this makes them an item. 
	# so items can display themselves, move, have various other componenets
	# but the item com be placed in another object's inventory.
	# while in the inventory, that object can use the item,
	# or equip the item. So each item has something that happens when it is used,
	# and a slot to be equipped in, and various bonuses, and descriptions.
	
	def __init__(self, use_function=None, equippable=False, slot=None, power_bonus=0, armor_bonus=0, max_parries_bonus=0, max_wounds_bonus=0):
		self.use_function = use_function
		self.equippable = equippable
		self.slot = slot
		self.power_bonus = power_bonus
		self.armor_bonus = armor_bonus
		self.max_parries_bonus = max_parries_bonus
		self.max_wounds_bonus = max_wounds_bonus
		self.equipped = False

	def pick_up(self, picker):

		if len(picker.inventory) > 25:
			if picker is player:
				log("Your inventory is full, can't pick this" + self.owner.name + "up", libtcod.red)
		else:
			picker.inventory.append(self.owner)
			objects.remove(self.owner)
			if picker is player:
				log("You picked up a " + self.owner.name + '!', libtcod.green)
			if self.equippable and picker.get_equipped_in_slot(self.slot) is None:
				self.equip(picker)

	def drop(self, dropper):
		if self.equipped:
			self.unequip(dropper)

		objects.append(self.owner)
		dropper.inventory.remove(self.owner)
		self.owner.x = dropper.x
		self.owner.y = dropper.y
		if dropper is player:
			log('You dropped a ' + self.owner.name + '.', libtcod.yellow)

	def use(self, user):
		if self.use_function is None:
			if user is player:
				log('This item can not be used.', libtcod.red)
			else:
				return None
		else:
			result = self.use_function()
			if result == 'used-up':
				user.inventory.remove(self.owner)

	def toggle_equip(self, user):
		if not self.equippable:
			if user is player:
				log('This item can not be equipped.', libtcod.red)
			return None
		if self.equipped:
			self.unequip(user)
		else:
			self.equip(user)

	def equip(self, user):
		old_shiz = user.get_equipped_in_slot(self.slot)
		if old_shiz is not None:
			old_shiz.unequip(user)
		self.equipped = True

		if user is player:
			log("Equipped a " + self.owner.name + " as " + self.slot + ".", libtcod.light_green)

	def unequip(self, user):
		if not self.equipped:
			return None
		self.equipped = False
		if user is player:
			log("Stopped equipping a " + self.owner.name + " as " + self.slot + ".", libtcod.light_red)

def no_use():
	log("This thing isn't actually usable.")

def sword(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='weapon', power_bonus=1)
	return Object(xpos, ypos, '/', 'sword', libtcod.light_gray, walkable=True, always_visible=True, item=item_comp)

def axe(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='weaopn', power_bonus=2)
	return Object(xpos, ypos, 'P', 'axe', libtcod.light_green, walkable=True, always_visible=True, item=item_comp)

def leather_armor(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='armor', armor_bonus=1)
	return Object(xpos, ypos, '&', 'leather armor', libtcod.light_sepia, walkable=True, always_visible=True, item=item_comp)

def shield(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='offhand', max_parries_bonus=2)
	return Object(xpos, ypos, ']', 'shield', libtcod.blue, walkable=True, always_visible=True, item=item_comp)

class Tile:
	# will build grass by default

	def __init__(self, terrain='grass'):
		self.type = terrain
		(self.walkable, self.transparent, self.stealth, self.back, self.fore, self.char) = terrain_tile(terrain)
		self.explored = False

	def change_type(self, terrain):
		self.type = terrain
		(self.walkable, self.transparent, self.stealth, self.back, self.fore, self.char) = terrain_tile(terrain)

def terrain_tile(terrain):
	if terrain == 'grass':
		return (True, True, False, libtcod.green, libtcod.green, '.')
	if terrain == 'stone':
		return (True, True, False, libtcod.gray, libtcod.gray, '.')
	if terrain == 'stone wall':
		return (False, False, True, libtcod.darker_gray, libtcod.darker_gray, '#')
	if terrain == 'village wall':
		return (False, False, True, libtcod.green, libtcod.sepia, '#')
	if terrain == 'mud':
		return (True, True, False, libtcod.sepia, libtcod.sepia, '.')
	if terrain == 'tree':
		return (False, False, True, libtcod.green, libtcod.dark_green, 'T')
	if terrain == 'sand':
		return (True, True, False, libtcod.light_amber, libtcod.light_amber, '.')
	if terrain == 'shallow water':
		return (True, True, True, libtcod.light_blue, libtcod.lighter_blue, '~')
	if terrain == 'water':
		return (False, True, True, libtcod.darker_blue, libtcod.dark_blue, '~')
	if terrain == 'crops':
		return (True, True, True, libtcod.sepia, libtcod.amber, 'C')
	if terrain == 'fence':
		return (False, True, False, libtcod.green, libtcod.dark_sepia, '#')
	if terrain == 'low stone wall':
		return (False, True, True, libtcod.green, libtcod.light_gray, '#')
	if terrain == 'wood wall':
		return (False, False, True, libtcod.dark_sepia, libtcod.dark_sepia, '#')
	if terrain == 'weak hinges':
		# the name here is a cludge to make things look nice. This is the tile for a door to sit on.
		return (True, False, True, libtcod.dark_sepia, libtcod.dark_sepia, ' ')
	if terrain == 'wood floor':
		return (True, True, False, libtcod.light_sepia, libtcod.light_sepia, '.')
	if terrain == 'window':
		return (False, True, True, libtcod.light_blue, libtcod.light_blue, '#')
	if terrain == 'dirt road':
		return (True, True, False, libtcod.dark_sepia, libtcod.dark_sepia, '.')
	if terrain == 'gravestone':
		return (False, True, True, libtcod.green, libtcod.gray, 149)

def initialize_ascii_maps():
	# we set the integers from 128 on up to be special graphics in our font file

	#these three: thick left to right diagonals, diamond pattern, thin right to left diagonals
	libtcod.console_map_ascii_code_to_font(128, 0, 11)
	libtcod.console_map_ascii_code_to_font(129, 1, 11)
	libtcod.console_map_ascii_code_to_font(130, 2, 11)

	# hole in the ground
	libtcod.console_map_ascii_code_to_font(131, 7, 0)

	# double wall horiz
	libtcod.console_map_ascii_code_to_font(132, 13, 12)
	# double wall vert
	libtcod.console_map_ascii_code_to_font(133, 10, 11)
	# double wall top left
	libtcod.console_map_ascii_code_to_font(134, 9, 12)
	# double wall top right
	libtcod.console_map_ascii_code_to_font(135, 11, 11)
	# double wall bottom left
	libtcod.console_map_ascii_code_to_font(136, 8, 12)
	# double wall bottom right
	libtcod.console_map_ascii_code_to_font(137, 12, 11)

	# single wall horiz
	libtcod.console_map_ascii_code_to_font(138, 4, 12)
	# single wall vert
	libtcod.console_map_ascii_code_to_font(139, 3, 11)
	# single wall top left
	libtcod.console_map_ascii_code_to_font(140, 10, 13)
	# single wall top right
	libtcod.console_map_ascii_code_to_font(141, 15, 11)
	# single wall bottom left
	libtcod.console_map_ascii_code_to_font(142, 0, 12)
	# single wall bottom right
	libtcod.console_map_ascii_code_to_font(143, 9, 13)

	# thick top border
	libtcod.console_map_ascii_code_to_font(144, 4, 14)
	# thick bottom border
	libtcod.console_map_ascii_code_to_font(145, 12, 13)
	# thick left border
	libtcod.console_map_ascii_code_to_font(146, 13, 13)
	# thick right border
	libtcod.console_map_ascii_code_to_font(147, 14, 13)
	# thick entire square
	libtcod.console_map_ascii_code_to_font(148, 11, 13)

	# upwards triangle
	libtcod.console_map_ascii_code_to_font(149, 14, 1)

	# door-looking thing
	libtcod.console_map_ascii_code_to_font(150, 14, 15)

	# solid block
	libtcod.console_map_ascii_code_to_font(151, 11, 13)

def make_map():
	global cur_map, objects#, stairs

	objects = [player]

	# a  is an array of tiles. Tile know what color they are.

	cur_map = [[Tile('grass')
		for y in range(curr_map_height) ]
			for x in range(curr_map_width) ]

	# Could modify tiles here.
	# Currently, we just put stones circles every which way.

	for x in range(roll(17,37)):
		new_x = roll(0, curr_map_width)
		new_y = roll(0, curr_map_height)
		place_stone_patch(new_x, new_y)
	
	# we should put the player somewhere specific.

	player.x = 10
	player.y = 10

	# we can generate objects here.

	#stairs = Object(new_x, new_y, '<', 'stairs', libtcod.white)
	#objects.append(stairs)
	#stairs.send_to_back()

def make_village_map():
	global cur_map, objects, curr_map_height, curr_map_width, board

	# stairs
	# a village map - a set of tiles, all enclosed by a wall.

	curr_map_height = VILLAGE_TILES_HIGH * VILLAGE_TILE_SIZE + 2
	curr_map_width = VILLAGE_TILES_WIDE * VILLAGE_TILE_SIZE + 2

	board = libtcod.console_new(curr_map_width, curr_map_height)

	libtcod.console_set_default_background(board, libtcod.darkest_blue)
	libtcod.console_set_default_foreground(board, libtcod.yellow)

	objects = [player]

	# split the area into an X x Y grid of NxN village tile areas

	cur_map = [[Tile('grass')
		for y in range(curr_map_height) ]
			for x in range(curr_map_width) ]

	build_double_wall(0, 0, curr_map_width, curr_map_height, 'village wall')

	# staggered_path(1, 1, 100, 100, 'dirt road')

	top_left_corners = []

	# before shuffling, top left corners reads from left to right, and then from up to down.

	for y in range(VILLAGE_TILES_HIGH):
		for x in range(VILLAGE_TILES_WIDE):
			top_left_corners.append((1+x*VILLAGE_TILE_SIZE, 1+y*VILLAGE_TILE_SIZE))

	# let's get trees down first. no trees in the middle of the road!

	for corner in top_left_corners:
		place_trees(corner[0], corner[1], VILLAGE_TILE_SIZE)

	# let's get a road network

	# decide on the connect point for each tile.
	connections = []

	for ind in range(VILLAGE_TILES_HIGH*VILLAGE_TILES_WIDE):
		road_x = roll(0, VILLAGE_TILE_SIZE - 1)
		road_y = roll(0, VILLAGE_TILE_SIZE - 1)
		connections.append((road_x, road_y))

	# implementing the sidewinder maze generation algorithm to create our road network.
	# Want to run left to right, and connect down when our run is cleared.
	# So on the rightmost edge, clear run.
	# on the bottom, just connect everything to the right, until the rightmost edge

	for y in range(VILLAGE_TILES_HIGH):
		run = []

		for x in range(VILLAGE_TILES_WIDE):
			run.append(x + y * VILLAGE_TILES_HIGH)

			at_eastern_boundary = x == VILLAGE_TILES_WIDE - 1
			at_southern_boundary = y == VILLAGE_TILES_HIGH - 1
			should_close_out = (at_eastern_boundary and not at_southern_boundary) or (not at_southern_boundary and chance(1,2))

			if should_close_out:
				which = run[roll(0, len(run) - 1)]
				from_road_x = top_left_corners[which][0] + connections[which][0]
				from_road_y = top_left_corners[which][1] + connections[which][1]
				to_road_x = top_left_corners[which + VILLAGE_TILES_HIGH][0] + connections[which + VILLAGE_TILES_HIGH][0]
				to_road_y = top_left_corners[which + VILLAGE_TILES_HIGH][1] + connections[which + VILLAGE_TILES_HIGH][1]

				staggered_path(from_road_x, from_road_y, to_road_x, to_road_y, 'dirt road')
				run = []

			elif not at_eastern_boundary:
				from_road_x = top_left_corners[x + y * VILLAGE_TILES_HIGH][0] + connections[x + y * VILLAGE_TILES_HIGH][0]
				from_road_y = top_left_corners[x + y * VILLAGE_TILES_HIGH][1] + connections[x + y * VILLAGE_TILES_HIGH][1]
				to_road_x = top_left_corners[x + y * VILLAGE_TILES_HIGH + 1][0] + connections[x + y * VILLAGE_TILES_HIGH + 1][0]
				to_road_y = top_left_corners[x + y * VILLAGE_TILES_HIGH + 1][1] + connections[x + y * VILLAGE_TILES_HIGH + 1][1]

				staggered_path(from_road_x, from_road_y, to_road_x, to_road_y, 'dirt road')

	random.shuffle(top_left_corners)

	# populate each tile with random content

	# set the starting position
	starting_tile = top_left_corners.pop()

	x_off = roll(VILLAGE_TILE_SIZE / 4, 3 * VILLAGE_TILE_SIZE / 4) + starting_tile[0]
	y_off = roll(VILLAGE_TILE_SIZE / 4, 3 * VILLAGE_TILE_SIZE / 4) + starting_tile[1]

	objects.append(Object(x_off, y_off, 131, 'hole down', libtcod.black, walkable=True, always_visible=True))

	radial_tile_paint(4, x_off, y_off, 'mud')

	player.x = x_off+1
	player.y = y_off+1

	# refactor: tile_types = village_tiles(VILLAGE_TILES_HIGH*VILLAGE_TILES_WIDE)
	tile_types = []

	tot_tiles = VILLAGE_TILES_WIDE * VILLAGE_TILES_HIGH

	for x in range(tot_tiles / 6):
		tile_types.append(0)
	for x in range(tot_tiles / 25):
		tile_types.append(1)
	for x in range(tot_tiles / 5):
		tile_types.append(2)
	for x in range(tot_tiles / 6):
		tile_types.append(3)
	for x in range(tot_tiles / 25):
		tile_types.append(4)
	for x in range(tot_tiles / 20):
		tile_types.append(5)

	random.shuffle(tile_types)

	for x in range(tot_tiles - len(tile_types)):
		tile_types.append(roll(0,5))

	tile_types.reverse()

	while len(top_left_corners) > 0:
		tile = top_left_corners.pop()
		choice = tile_types.pop()

		if choice == 0:
			place_copse(tile[0], tile[1], VILLAGE_TILE_SIZE)
		elif choice == 1:
			place_pond(tile[0], tile[1], VILLAGE_TILE_SIZE)
		elif choice == 2:
			place_field(tile[0], tile[1], VILLAGE_TILE_SIZE)
		elif choice == 3:
			place_cottage(tile[0], tile[1], VILLAGE_TILE_SIZE)
		elif choice == 4:
			place_graves(tile[0], tile[1], VILLAGE_TILE_SIZE)
		elif choice == 5:
			place_pens(tile[0], tile[1], VILLAGE_TILE_SIZE)


	#stairs = Object(roll(20,30), roll(20,30), ' ', 'stairs', libtcod.white)
	#objects.append(stairs)
	#stairs.send_to_back()

def place_stone_patch(xpos, ypos):
	global cur_map

	radius = roll(2,6)

	# we don't want to place shit outside the bounds

	radial_tile_paint(radius, xpos, ypos, 'stone')

def place_trees(xpos, ypos, tile_size):
	global cur_map
	tile_area = tile_size * tile_size
	for x in range(tile_area / 50, roll(tile_area / 50, tile_area / 10)):
		xoff = xpos + roll(0,tile_size - 1)
		yoff = ypos + roll(0,tile_size - 1)
		cur_map[xoff][yoff].change_type('tree')

def place_copse(xpos, ypos, tile_size):
	global cur_map, objects

	num_copses = roll(3, tile_size / 3)
	for i in range(num_copses):
		place_trees(xpos, ypos, tile_size)

	jacks = chance(2,3)
	hunters = chance(1,3)
	if jacks:
		num_jacks = roll(1,3)

		while num_jacks > 0:
			jack_x = roll(xpos, xpos + tile_size - 1)
			jack_y = roll(ypos, ypos + tile_size - 1)

			if is_walkable(jack_x, jack_y):
				objects.append(lumber_worker(jack_x, jack_y))
				num_jacks -= 1

	if hunters:
		num_hunters = roll(1,3)

		while num_hunters > 0:
			hunt_x = roll(xpos, xpos + tile_size - 1)
			hunt_y = roll(ypos, ypos + tile_size - 1)

			if is_walkable(hunt_x, hunt_y):
				objects.append(hunter(hunt_x, hunt_y))
				num_hunters -= 1

def place_pond(xpos, ypos, tile_size):
	global cur_map

	radius = roll(tile_size / 10,2 * tile_size / 5)
	centerx = roll(xpos+1+radius, xpos + tile_size - 2 - radius)
	centery = roll(ypos+1+radius, ypos + tile_size - 2 - radius)

	radial_tile_paint(radius + 1, centerx, centery, 'sand')
	radial_tile_paint(radius, centerx, centery, 'shallow water')
	radial_tile_paint(radius - 1, centerx, centery, 'water')

	num_fishers = roll(1,3)

	while num_fishers > 0:
		fish_x = roll(xpos, xpos + tile_size - 1)
		fish_y = roll(ypos, ypos + tile_size - 1)

		if is_walkable(fish_x, fish_y):
			objects.append(fisherman(fish_x, fish_y))
			num_fishers -= 1

def place_field(xpos, ypos, tile_size):
	global cur_map

	width = roll(tile_size / 5,3 * tile_size / 4)
	height = roll(tile_size / 5,3 * tile_size / 4)

	xoff = xpos + roll(1, tile_size - 2 - width)
	yoff = ypos + roll(1, tile_size - 2 - height)

	rectangle_tile_fill(xoff, yoff, width, height, 'crops')

	rectangle_tile_trim(xoff - 1, yoff - 1, width + 2, height + 2, 'fence')

	rectangle_place_gaps(xoff - 1, yoff - 1, width + 2, height + 2, 'grass',
		[chance(1,4), chance(1,4), chance(1,4), chance(1,4)])

	num_farmers = roll(2,4)

	while num_farmers > 0:
		farm_x = roll(xoff, xoff + width - 1)
		farm_y = roll(yoff, yoff + height - 1)

		if is_walkable(farm_x, farm_y):
			objects.append(farmer(farm_x, farm_y))
			num_farmers -= 1

def place_cottage(xpos, ypos, tile_size):
	global cur_map, objects

	cottage_w = roll(tile_size / 4, 2 * tile_size / 5)
	cottage_h = roll(tile_size / 4, 2 * tile_size / 5)

	wall_extra_w = roll(tile_size / 5, tile_size / 2)
	wall_extra_h = roll(tile_size / 5, tile_size / 2)

	wall_total_w = cottage_w + wall_extra_w
	wall_total_h = cottage_h + wall_extra_h

	wall_start_x = roll(xpos, xpos + tile_size - wall_total_w)
	wall_start_y = roll(ypos, ypos + tile_size - wall_total_h)

	cottage_start_x = roll(wall_start_x + 2, wall_start_x + wall_extra_w - 2)
	cottage_start_y = roll(wall_start_y + 2, wall_start_y + wall_extra_h - 2)

	rectangle_tile_fill(cottage_start_x, cottage_start_y, cottage_w, cottage_h, 'wood floor')
	rectangle_tile_trim(cottage_start_x, cottage_start_y, cottage_w, cottage_h, 'wood wall')
	rectangle_place_gaps(cottage_start_x, cottage_start_y, cottage_w, cottage_h, 'window',
		[chance(1,3), chance(1,3), chance(1,3), chance(1,3)])
	

	surrounding_wall = chance(1,3)

	if surrounding_wall:
		build_single_wall(wall_start_x, wall_start_y, wall_total_w, wall_total_h, 'low stone wall')
		# rectangle_tile_trim(wall_start_x, wall_start_y, wall_total_w, wall_total_h, 'low stone wall')

		rectangle_place_gaps(wall_start_x, wall_start_y, wall_total_w, wall_total_h, 'grass',
			[chance(1,2),chance(1,2),chance(1,2),chance(1,2)], at_least_one=False)

	occupants = roll(1,3)
	while occupants > 0:
		xpos = roll(cottage_start_x + 1, cottage_start_x + cottage_w - 2)
		ypos = roll(cottage_start_y + 1, cottage_start_y + cottage_h - 2)
		if is_walkable(xpos, ypos):
			which = roll(0,4)
			if which == 0:
				objects.append(farmer(xpos, ypos))
			elif which == 1:
				objects.append(hunter(xpos, ypos))
			elif which == 2:
				objects.append(lumber_worker(xpos, ypos))
			elif which == 3:
				objects.append(fisherman(xpos, ypos))
			elif which == 4:
				objects.append(guard(xpos, ypos))
			occupants -= 1

	num_dogs = roll(1,3)

	while num_dogs > 0:
		xpos = roll(cottage_start_x + 1, cottage_start_x + cottage_w - 2)
		ypos = roll(cottage_start_y + 1, cottage_start_y + cottage_h - 2)
		if is_walkable(xpos, ypos):
			objects.append(dog(xpos, ypos))
		num_dogs -= 1

	door_wall = roll(0,3)

	if door_wall == 0:
		door_x = roll(cottage_start_x + 1, cottage_start_x + cottage_w - 2)
		door_y = cottage_start_y
	elif door_wall == 1:
		door_y = roll(cottage_start_y + 1, cottage_start_y + cottage_h - 2)
		door_x = cottage_start_x
	elif door_wall == 2:
		door_x = roll(cottage_start_x + 1, cottage_start_x + cottage_w - 2)
		door_y = cottage_start_y + cottage_h - 1
	elif door_wall == 3:
		door_y = roll(cottage_start_y + 1, cottage_start_y + cottage_h - 2)
		door_x = cottage_start_x + cottage_w - 1

	new_door = door(door_x, door_y)
	objects.append(new_door)
	new_door.send_to_back()
	cur_map[door_x][door_y].change_type('weak hinges')

def place_graves(xpos, ypos, tile_size):
	# build a low stone wall, with gaps. Place in it some graves, which are headstones with patches of dirt or grass below them

	global cur_map


	wall_w = roll(tile_size / 2, tile_size - 1)
	wall_h = roll(tile_size / 2, tile_size - 1)

	wall_start_x = roll(xpos, xpos + tile_size - wall_w)
	wall_start_y = roll(ypos, ypos + tile_size - wall_h)

	#gets rid of roads, adds in trees
	rectangle_tile_fill(wall_start_x, wall_start_y, wall_w, wall_h, 'grass')
	place_trees(xpos, ypos, tile_size)
	
	build_single_wall(wall_start_x, wall_start_y, wall_w, wall_h, 'low stone wall')
	rectangle_place_gaps(wall_start_x, wall_start_y, wall_w, wall_h, 'grass',
		[chance(2,3), chance(2,3), chance(2,3), chance(2,3)])
	
	for y in range(wall_start_y + 1, wall_start_y + wall_h - 3):
		if (y - wall_start_y) % 2 == 1:
			for x in range(wall_start_x+1, wall_start_x + wall_w - 1):
				if chance(2,7):
					cur_map[x][y].change_type('gravestone')
					cur_map[x][y+1].change_type('mud')

def place_pens(xpos, ypos, tile_size):
	global cur_map, objects

	x1 = roll(0, tile_size / 2)
	x2 = roll(x1 + 6, tile_size - 4)
	x3 = roll(0, tile_size - 4)

	y1 = roll(0, tile_size / 2)
	y2 = roll(0, tile_size / 2)
	y3 = roll(max(y1, y2) + 6, tile_size - 4)

	w1 = x2 - x1 - 2
	w2 = roll(4, tile_size - x2)
	w3 = roll(4, tile_size - x3)

	h1 = y3 - y1 - 2
	h2 = y3 - y2 - 2
	h3 = roll(4, tile_size - y3)

	x = [x1, x2, x3]
	y = [y1, y2, y3]
	w = [w1, w2, w3]
	h = [h1, h2, h3]

	for i in range(3):
		build_single_wall(xpos + x[i], ypos + y[i], w[i], h[i], 'fence')

		cows = chance(1,3)

		animals = roll(2,4)

		while animals >0:
			ani_x = roll(x[i] + 1, x[i] + w[i] - 2) + xpos
			ani_y = roll(y[i] + 1, y[i] + h[i] - 2) + ypos

			if is_walkable(ani_x, ani_y):
				if cows:
					objects.append(cow(ani_x, ani_y))
				else:
					objects.append(chicken(ani_x, ani_y))
				animals -= 1
			elif cur_map[ani_x][ani_y].type == 'tree':
				cur_map[ani_x][ani_y].change_type('grass')

		gate_wall = roll(0,3)

		if gate_wall == 0:
			gate_x = roll(1, w[i] - 2) + x[i] + xpos
			gate_y = ypos + y[i]
		elif gate_wall == 1:
			gate_x = x[i] + xpos
			gate_y = roll(1, h[i] - 2) + y[i] + ypos
		elif gate_wall == 2:
			gate_x = roll(1, w[i] - 2) + x[i] + xpos
			gate_y = ypos + y[i] + h[i] - 1
		elif gate_wall == 3:
			gate_x = x[i] + w[i] + xpos - 1
			gate_y = roll(1, h[i] - 2) + y[i] + ypos

		new_gate = gate(gate_x, gate_y)
		objects.append(new_gate)
		new_gate.send_to_back()

def radial_tile_paint(radius, xpos, ypos, terrain):
	# This only respects the boundaries of the current map, not your current terrain.

	global cur_map

	xmin = max(0, xpos - radius)
	xmax = min(xpos + radius, curr_map_width)

	ymin = max(0, ypos - radius)
	ymax = min(ypos + radius, curr_map_height)

	for x in range(xmin, xmax):
		for y in range(ymin, ymax):
			if sqrt((x - xpos) ** 2 + (y - ypos) ** 2) < radius:
				cur_map[x][y].change_type(terrain)

def rectangle_tile_fill(xpos, ypos, w, h, terrain):
	global cur_map

	for x in range(xpos, xpos+w):
		for y in range(ypos, ypos+h):
			cur_map[x][y].change_type(terrain)

def rectangle_tile_trim(xpos, ypos, w, h, terrain):
	global cur_map

	for x in range(xpos, xpos+w):
		cur_map[x][ypos].change_type(terrain)
		cur_map[x][ypos+h-1].change_type(terrain)

	for y in range(ypos, ypos+h):
		cur_map[xpos][y].change_type(terrain)
		cur_map[xpos+w-1][y].change_type(terrain)

def rectangle_place_gaps(xpos, ypos, w, h, terrain, which_walls=[True, True, True, True], at_least_one=True):
	global cur_map

	# goes along this rectangle, and, ignoring the corners, places gaps of random length at a random point along it.
	# Uses the given terrain to make up the gaps. This can be used for windows, etc.
	# which_walls is in format(NORTH, SOUTH, WEST, EAST)

	if at_least_one and (not which_walls[0] and not which_walls[1] and not which_walls[2] and not which_walls[3]):
		which_walls[roll(0,3)] = True

	if which_walls[0]:
		gap_length = roll(1, w - 2)
		gap_x = xpos + roll(1, w - 1 - gap_length)
		for x in range(gap_length):
			cur_map[x + gap_x][ypos].change_type(terrain)

	if which_walls[1]:
		gap_length = roll(1, w - 2)
		gap_x = xpos + roll(1, w - 1 - gap_length)
		for x in range(gap_length):
			cur_map[x + gap_x][ypos+h-1].change_type(terrain)

	if which_walls[2]:
		gap_length = roll(1, h - 2)
		gap_y = ypos + roll(1, h - 1 - gap_length)
		for y in range(gap_length):
			cur_map[xpos][y + gap_y].change_type(terrain)

	if which_walls[3]:
		gap_length = roll(1, h - 2)
		gap_y = ypos + roll(1, h - 1 - gap_length)
		for y in range(gap_length):
			cur_map[xpos+w-1][y + gap_y].change_type(terrain)

def build_single_wall(xpos, ypos, w, h, terrain):
	global cur_map

	for x in range(xpos, xpos+w):
		cur_map[x][ypos].change_type(terrain)
		cur_map[x][ypos+h-1].change_type(terrain)
		cur_map[x][ypos].char = 138
		cur_map[x][ypos+h-1].char = 138

	for y in range(ypos, ypos+h):
		cur_map[xpos][y].change_type(terrain)
		cur_map[xpos+w-1][y].change_type(terrain)
		cur_map[xpos][y].char = 139
		cur_map[xpos+w-1][y].char = 139

	cur_map[xpos][ypos].char = 140
	cur_map[xpos+w-1][ypos].char = 141
	cur_map[xpos][ypos+h-1].char = 142
	cur_map[xpos+w-1][ypos+h-1].char = 143 

def build_double_wall(xpos, ypos, w, h, terrain):
	global cur_map
	#rectangle_tile_trim(xpos, ypos, w, h, terrain)
	for x in range(xpos, xpos+w):
		cur_map[x][ypos].change_type(terrain)
		cur_map[x][ypos+h-1].change_type(terrain)
		cur_map[x][ypos].char = 132
		cur_map[x][ypos+h-1].char = 132

	for y in range(ypos, ypos+h):
		cur_map[xpos][y].change_type(terrain)
		cur_map[xpos+w-1][y].change_type(terrain)
		cur_map[xpos][y].char = 133
		cur_map[xpos+w-1][y].char = 133

	cur_map[xpos][ypos].char = 134
	cur_map[xpos+w-1][ypos].char = 135
	cur_map[xpos][ypos+h-1].char = 136
	cur_map[xpos+w-1][ypos+h-1].char = 137	

def staggered_path(start_x, start_y, end_x, end_y, terrain):
	global cur_map

	curr_x = start_x
	curr_y = start_y

	cur_map[curr_x][curr_y].change_type(terrain)

	xmag = abs(end_x - start_x)
	ymag = abs(end_y - start_y)

	if ymag == 0:
		for x in range(curr_x, end_x):
			cur_map[x][end_y].change_type(terrain)
		return None

	if xmag == 0:
		for y in range(curr_y, end_y):
			cur_map[end_x][y].change_type(terrain)
		return None

	xsign = (end_x - start_x)/abs(end_x - start_x)
	ysign = (end_y - start_y)/abs(end_y - start_y)

	while curr_x is not end_x and curr_y is not end_y:
		if chance(xmag, xmag+ymag):
			xmag = xmag - 1
			curr_x = curr_x + xsign
			cur_map[curr_x][curr_y].change_type(terrain)
		else:
			ymag = ymag - 1
			curr_y = curr_y  + ysign
			cur_map[curr_x][curr_y].change_type(terrain)

	if curr_x is not end_x:
		for x in range(curr_x, end_x):
			cur_map[x][end_y].change_type(terrain)
	elif curr_y is not end_y:
		for y in range(curr_y, end_y):
			cur_map[end_x][y].change_type(terrain)

def initialize_fov():
	global fov_recompute, fov_map
	fov_recompute = True



	fov_map = libtcod.map_new(curr_map_width, curr_map_height)

	for y in range(curr_map_height):
		for x in range(curr_map_width):
			libtcod.map_set_properties(fov_map, x, y, cur_map[x][y].transparent, cur_map[x][y].walkable)

	libtcod.console_clear(0)

def move_camera(target_x, target_y):
	global camera_x, camera_y, fov_recompute

	x = target_x - CAMERA_WIDTH / 2
	y = target_y - CAMERA_HEIGHT / 2

	if x < 0: x = 0
	if y < 0: y = 0
	if x > curr_map_width - CAMERA_WIDTH: x = curr_map_width - CAMERA_WIDTH
	if y > curr_map_height - CAMERA_HEIGHT: y = curr_map_height - CAMERA_HEIGHT

	if x != camera_x or y != camera_y:
		fov_recompute = True

	(camera_x, camera_y) = (x, y)

def to_camera_coordinates(x, y):

	(x, y) = (x - camera_x, y - camera_y)

	if (x < 0 or y < 0 or x >= CAMERA_WIDTH or y >= CAMERA_HEIGHT):
		return (None, None)

	return (x, y)

def get_names_under_mouse():
	global mouse, target

	(x, y) = (mouse.cx, mouse.cy)
	(x, y) = (camera_x + x, camera_y + y)

	names = []

	if libtcod.map_is_in_fov(fov_map, x, y):
		for obj in objects: 
			if obj.x == x and obj.y == y:
				names.append(obj.name)

				if mouse.lbutton_pressed and obj is not player:
					target = obj
		
		if len(names) > 0:
			names.append('on')

	names = ', '.join(names)
	if libtcod.map_is_in_fov(fov_map, x, y):
		if len(names) > 0: 
			names += " "
		names += cur_map[x][y].type

	return names.capitalize()

def log(new_log, color = libtcod.white):
	# split the log enter, if necessary, across multiple lines
	new_log_lines = textwrap.wrap(new_log, LOG_WIDTH)

	for line in new_log_lines:
		# if the log has the max number of entries already, delete the first one.
		if len(game_log) == LOG_LENGTH:
			del game_log[0]

		# add the new line as a tuple of text and color.
		game_log.append( (line, color) )

def render_all():
	global fov_map
	global fov_recompute
	global camera_x, camera_y

	move_camera(player.x, player.y)

	if fov_recompute:

		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, True, FOV_ALGO)
		libtcod.console_clear(board)

		for y in range(CAMERA_HEIGHT):
			for x in range(CAMERA_WIDTH):
				(map_x, map_y) = (camera_x + x, camera_y + y)
				visible = libtcod.map_is_in_fov(fov_map, map_x, map_y)

				wall = not cur_map[map_x][map_y].transparent

				if visible:
					tile = cur_map[map_x][map_y]
					libtcod.console_put_char_ex(board, map_x, map_y, tile.char, tile.fore, tile.back)
					if player.mind.skills[0]:
						cur_map[map_x][map_y].explored = True
				elif cur_map[map_x][map_y].explored:
					# explored tile logic
					tile = cur_map[map_x][map_y]
					libtcod.console_put_char_ex(board, map_x, map_y, tile.char, tile.fore * 0.5, tile.back *0.5)


	for obj in objects:
		if obj is not player:
			obj.draw()

	player.draw()

	libtcod.console_blit(board, camera_x, camera_y, curr_map_width, curr_map_height, 0, 0, 0)

	libtcod.console_clear(panel)

	# create the player info panel
	pmp = player.fighter.max_parries
	ppl = player.fighter.parries_left
	player_parries = "PARRIES:" + " X" * ppl
	if player.fighter.rested:
		player_parries += " /" + " -" * (pmp - ppl - 1)
	else:
		player_parries += " -" * (pmp - ppl)

	if player.fighter.max_parries == 0:
		player_parries += " UNSKILLED"

	libtcod.console_set_default_foreground(panel, libtcod.light_gray)
	libtcod.console_print(panel, PLAYER_INFO_X, PLAYER_INFO_Y, player_parries)

	pmw = player.fighter.max_wounds
	pwl = player.fighter.wounds 
	player_wounds = "WOUNDS:" + " *" * pwl + " -" * (pmw - pwl)
	libtcod.console_set_default_foreground(panel, libtcod.light_red)
	libtcod.console_print(panel, PLAYER_INFO_X, PLAYER_INFO_Y + 1, player_wounds)

	# create the enemy info panel
	if target is not None and target.fighter is not None:

		tmp = target.fighter.max_parries
		tpl = target.fighter.parries_left
		target_parries = "PARRIES:" + " X" * tpl
		if target.fighter.rested:
			target_parries += " /" + " -" * (tmp - tpl - 1)
		else:
			target_parries += " -" * (tmp - tpl)
		if target.fighter.max_parries == 0:
			target_parries += " UNSKILLED"

		libtcod.console_set_default_foreground(panel, libtcod.light_gray)
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y + 1, target_parries)

		tmw = target.fighter.max_wounds
		twl = target.fighter.wounds
		target_wounds = "WOUNDS:" + " *" * twl + " -" * (tmw - twl)

		libtcod.console_set_default_foreground(panel, libtcod.light_red)
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y + 2, target_wounds)

		libtcod.console_set_default_foreground(panel, libtcod.yellow)
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y, "TARGET: " + target.name.capitalize())
	else:
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y, "No current target.")

	libtcod.console_set_default_foreground(panel, libtcod.yellow)
	libtcod.console_print_ex(panel, PANEL_WIDTH / 2, 0, libtcod.BKGND_DEFAULT, libtcod.CENTER, get_names_under_mouse())

	# create the log panel
	y = 0
	for (line, color) in game_log[-1*LOG_HEIGHT:]:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print(panel, LOG_X, LOG_Y + y, line)
		y += 1

	libtcod.console_blit(panel, 0, 0, PANEL_WIDTH, PANEL_HEIGHT, 0, PANEL_X, PANEL_Y)

def render_all_night():
	global fov_map
	global fov_recompute
	global camera_x, camera_y

	move_camera(player.x, player.y)

	if fov_recompute:

		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, True, FOV_ALGO)
		libtcod.console_clear(board)

		for y in range(CAMERA_HEIGHT):
			for x in range(CAMERA_WIDTH):
				(map_x, map_y) = (camera_x + x, camera_y + y)
				visible = libtcod.map_is_in_fov(fov_map, map_x, map_y)

				wall = not cur_map[map_x][map_y].transparent

				if visible:
					tile = cur_map[map_x][map_y]
					libtcod.console_put_char_ex(board, map_x, map_y, tile.char, tile.fore, libtcod.black)
					if player.mind.skills[0]:
						cur_map[map_x][map_y].explored = True
				elif cur_map[map_x][map_y].explored:
					# explored tile logic
					tile = cur_map[map_x][map_y]
					libtcod.console_put_char_ex(board, map_x, map_y, tile.char, tile.fore * 0.5, libtcod.black)


	for obj in objects:
		if obj is not player:
			obj.draw()

	player.draw()

	libtcod.console_blit(board, camera_x, camera_y, curr_map_width, curr_map_height, 0, 0, 0)

	libtcod.console_clear(panel)

	# create the player info panel
	pmp = player.fighter.max_parries
	ppl = player.fighter.parries_left
	player_parries = "PARRIES:" + " X" * ppl
	if player.fighter.rested:
		player_parries += " /" + " -" * (pmp - ppl - 1)
	else:
		player_parries += " -" * (pmp - ppl)

	if player.fighter.max_parries == 0:
		player_parries += " UNSKILLED"

	libtcod.console_set_default_foreground(panel, libtcod.light_gray)
	libtcod.console_print(panel, PLAYER_INFO_X, PLAYER_INFO_Y, player_parries)

	pmw = player.fighter.max_wounds
	pwl = player.fighter.wounds 
	player_wounds = "WOUNDS:" + " *" * pwl + " -" * (pmw - pwl)
	libtcod.console_set_default_foreground(panel, libtcod.light_red)
	libtcod.console_print(panel, PLAYER_INFO_X, PLAYER_INFO_Y + 1, player_wounds)

	# create the enemy info panel
	if target is not None and target.fighter is not None:

		tmp = target.fighter.max_parries
		tpl = target.fighter.parries_left
		target_parries = "PARRIES:" + " X" * tpl
		if target.fighter.rested:
			target_parries += " /" + " -" * (tmp - tpl - 1)
		else:
			target_parries += " -" * (tmp - tpl)
		if target.fighter.max_parries == 0:
			target_parries += " UNSKILLED"

		libtcod.console_set_default_foreground(panel, libtcod.light_gray)
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y + 1, target_parries)

		tmw = target.fighter.max_wounds
		twl = target.fighter.wounds
		target_wounds = "WOUNDS:" + " *" * twl + " -" * (tmw - twl)

		libtcod.console_set_default_foreground(panel, libtcod.light_red)
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y + 2, target_wounds)

		libtcod.console_set_default_foreground(panel, libtcod.yellow)
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y, "TARGET: " + target.name.capitalize())
	else:
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y, "No current target.")

	libtcod.console_set_default_foreground(panel, libtcod.yellow)
	libtcod.console_print_ex(panel, PANEL_WIDTH / 2, 0, libtcod.BKGND_DEFAULT, libtcod.CENTER, get_names_under_mouse())
	
	# create the log panel
	y = 0
	for (line, color) in game_log[-1*LOG_HEIGHT:]:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print(panel, LOG_X, LOG_Y + y, line)
		y += 1

	libtcod.console_blit(panel, 0, 0, PANEL_WIDTH, PANEL_HEIGHT, 0, PANEL_X, PANEL_Y)

def triple_menu(title, options):
	# so triple_menu will take a title and a list of triples - (option, explanation, return for that option).
	# it will display that list with an alphabetical label on each entry,
	# starting with the first entry highlighted and explained.
	# arrow keys and the numpad navigate to each entry, changing the explanation
	# Enter and space select the highlighted option.
	# Escape cancels out the menu.

	# this is hacky and cludgy, and selection isn't yet implemented. Still, it will do for now.

	# initialize the menu window

	if len(options) > 26: raise ValueError('For now, no menus w/ more than 26 options.')

	title_height = libtcod.console_get_height_rect(0, 0, 0, MENU_WIDTH, MENU_MAX_HEIGHT, title)

	if title == '':
		title_height = 0

	footer_height = 0

	for option in options:
		pos_footer = option[1]
		pos_height = libtcod.console_get_height_rect(0,0, 0, MENU_WIDTH, MENU_MAX_HEIGHT, pos_footer)
		footer_height = max(footer_height, pos_height)

	height = len(options) + title_height + footer_height

	menu = libtcod.console_new(MENU_WIDTH, height)

	libtcod.console_set_default_foreground(menu, libtcod.white)
	libtcod.console_set_default_background(menu, libtcod.darkest_blue)

	# initialization finish, begin loop.

	choice_made = False
	selected = 0

	while not choice_made:

		libtcod.console_clear(menu)

		# print the menu title
		libtcod.console_print_rect_ex(menu, 0, 0, MENU_WIDTH, title_height, libtcod.BKGND_DEFAULT, libtcod.LEFT, title)
		libtcod.console_set_default_background(menu, libtcod.red)

		# print each option

		y = title_height
		letter_index = ord('a')

		for option_tuple in options:
			text = '(' + chr(letter_index) + ') ' + option_tuple[0]
			if selected == y - title_height:
				libtcod.console_set_default_background(menu, libtcod.light_blue)
				libtcod.console_print_ex(menu, 0, y, libtcod.BKGND_SET, libtcod.LEFT, text)
				libtcod.console_set_default_background(menu, libtcod.darkest_blue)
			else:
				libtcod.console_print_ex(menu, 0, y, libtcod.BKGND_DEFAULT, libtcod.LEFT, text)

			y += 1
			letter_index += 1

		footer = options[selected][1]

		libtcod.console_print_rect_ex(menu, 0, len(options)+title_height, MENU_WIDTH, footer_height, libtcod.BKGND_DEFAULT, libtcod.LEFT, footer)
		# then we blit this sucker onto the main screen.

		x = SCREEN_WIDTH / 2 - MENU_WIDTH / 2
		y = SCREEN_HEIGHT / 2 - height / 2
		libtcod.console_blit(menu, 0, 0, MENU_WIDTH, height, 0, x, y, 1.0, 1.0)

		libtcod.console_flush()

		# ok, now we handle INPUT

		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)

		if key.vk == libtcod.KEY_ESCAPE:
			libtcod.console_clear(menu)
			libtcod.console_blit(menu, 0, 0, MENU_WIDTH, height, 0, x, y, 1.0, 1.0)
			libtcod.console_delete(menu)
			return 'no-choice'

		index = key.c - ord('a')
		if index >= 0 and index < len(options):
			libtcod.console_clear(menu)
			libtcod.console_blit(menu, 0, 0, MENU_WIDTH, height, 0, x, y, 1.0, 1.0)
			libtcod.console_delete(menu)
			return options[index][2]
		elif (key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2) and selected < len(options) - 1:
			selected += 1
		elif (key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8) and selected > 0:
			selected -= 1
		elif key.vk == libtcod.KEY_ENTER:

			libtcod.console_clear(menu)
			libtcod.console_blit(menu, 0, 0, MENU_WIDTH, height, 0, x, y, 1.0, 1.0)
			libtcod.console_delete(menu)
			return options[selected][2]

	libtcod.console_delete(menu)
	return None

def single_screen(title, options):

	title_height = libtcod.console_get_height_rect(0, 0, 0, MENU_WIDTH, MENU_MAX_HEIGHT, title)
	
	height = len(options) + title_height

	menu = libtcod.console_new(MENU_WIDTH, height)

	libtcod.console_set_default_foreground(menu, libtcod.white)
	libtcod.console_set_default_background(menu, libtcod.darkest_blue)

	# initialization finish, begin loop.

	choice_made = False

	while not choice_made:

		libtcod.console_clear(menu)

		# print the menu title
		libtcod.console_print_rect_ex(menu, 0, 0, MENU_WIDTH, title_height, libtcod.BKGND_DEFAULT, libtcod.LEFT, title)

		# print each option

		y = title_height

		for option in options:
			libtcod.console_print_ex(menu, 0, y, libtcod.BKGND_DEFAULT, libtcod.LEFT, option)
			y += 1
		
		# then we blit this sucker onto the main screen.

		x = SCREEN_WIDTH / 2 - MENU_WIDTH / 2
		y = SCREEN_HEIGHT / 2 - height / 2
		libtcod.console_blit(menu, 0, 0, MENU_WIDTH, height, 0, x, y, 1.0, 1.0)

		libtcod.console_flush()

		# ok, now we handle INPUT

		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)

		if key.vk == libtcod.KEY_ESCAPE or key.vk == libtcod.KEY_SPACE or key.vk == libtcod.KEY_ENTER:
			libtcod.console_clear(menu)
			libtcod.console_blit(menu, 0, 0, MENU_WIDTH, height, 0, x, y, 1.0, 1.0)
			libtcod.console_delete(menu)
			return None

	libtcod.console_clear(menu)
	libtcod.console_blit(menu, 0, 0, MENU_WIDTH, height, 0, x, y, 1.0, 1.0)
	libtcod.console_delete(menu)
	return None

def escape_menu():
	options = []
	options.append(["Skills", "", 0],)
	options.append(["Controls", "", 1])
	if game_state == 'playing':
		options.append(["Save and Quit", "", 2])
	elif game_state == 'dead':
		options.append(["Quit", "", 3])

	choice = triple_menu("***PAUSED***", options)

	if choice == 0:
		skills_menu()
	elif choice == 1:
		controls_screen()
	elif choice == 2 or choice == 3:
		return 'exit'

def skills_menu():
	options = []

	for inx, skill in enumerate(player.mind.skills):
		if skill > 0:
			options.append( [num_to_faculty_name(inx, skill), num_to_faculty_description(inx, skill), inx] )
	if len(options) == 0:
		options.append( ["You have no skills currently.", "Eat minds to gain skills! Kill creatures to eat their minds.", 0])
	triple_menu("SKILLS", options)

	return None

def controls_screen():
	options = []

	options.append("Move - Arrow Keys")
	options.append("Other Move - Num Pad")
	options.append("Rest (Recover Parries) - Space")
	options.append("Eat Minds - E")
	options.append("Menu - Escape")
	single_screen("CONTROLS", options)
	return None

def handle_keys():
	global key

	if key.vk == libtcod.KEY_ESCAPE:
		return escape_menu()

	if game_state == 'playing':
		if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
			return player_move_or_attack(0,-1)
		elif key.vk == libtcod.KEY_KP9:
			return player_move_or_attack(1,-1)
		elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
			return player_move_or_attack(1,0)
		elif key.vk == libtcod.KEY_KP3:
			return player_move_or_attack(1,1)
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
			return player_move_or_attack(0,1)
		elif key.vk == libtcod.KEY_KP1:
			return player_move_or_attack(-1,1)
		elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
			return player_move_or_attack(-1,0)
		elif key.vk == libtcod.KEY_KP7:
			return player_move_or_attack(-1,-1)
		elif key.vk == libtcod.KEY_KP5 or key.vk == libtcod.KEY_SPACE:
			return player_pause()

		key_char = chr(key.c).lower()

		if key_char == 'e':
			return player_eat_mind()
		elif key_char == 'g':
			for obj in objects:
				if obj.x == player.x and obj.y == player.y and obj.item:
					obj.item.pick_up(player)
					return 'took-turn'
		elif key_char == 'i':
			for thing in player.inventory:
				print(thing.name)
				print(thing.item.equipped)
			for obj in objects:
				inv = obj.inventory
				print(obj.name)
				for thing in inv:
					print(thing.name)
					print(thing.item.equipped)
				return 'no-turn'
		elif key_char == 'd':
			for thing in player.inventory:
				thing.item.drop(player)
		elif key_char == 'w':
			for thing in player.inventory:
				thing.item.toggle_equip(player)

	return 'no-turn'

def player_move_or_attack(dx, dy):
	global fov_recompute, target

	x = player.x + dx
	y = player.y + dy

	# try to find a target to attack
	targeted = None
	for obj in objects:
		if obj.fighter and x is obj.x and y is obj.y:
			targeted = obj
			break

	if targeted is not None:
		player.fighter.attack(targeted)
		target = targeted
		return 'took-turn'
	elif player.move(dx, dy):
		fov_recompute = True
		return 'took-turn'
	else:
		return 'no-turn'

def player_pause():
	player.fighter.rest()
	return 'took-turn'

def player_eat_mind():
	available_minds = []

	for obj in objects:
		if obj.mind and obj.x == player.x and obj.y == player.y and obj is not player:
			available_minds.append( [obj.mind.name, obj.mind.desc, obj.mind] )
	# Now, choose mind from available_minds with a menu

	if len(available_minds) == 0:
		log("No minds here to be eaten!", libtcod.red)
		return 'no-turn'

	eaten_mind = triple_menu("Which mind to consume?", available_minds)

	# choose option to eat in that mind with a menu
	
	if eaten_mind == 'no-choice':
		return 'no-turn'

	choice = mindeating_menu(eaten_mind)

	if choice == -1:
		return 'took-turn'

	# update the player skills based on that

	player.mind.skills[choice] += 1
	if choice == 1:
		player_pause()
		player_pause()

	log("You devour the mind...", libtcod.red)
	log("You know %s!" %num_to_faculty_name(choice, player.mind.skills[choice]), libtcod.blue)

	return 'took-turn'

def num_to_faculty_name(ind, magnitude=1):
	if ind == 0:
		return "Mapping"
	if ind == 1:
		return "Parry %i" % magnitude
	if ind == 2:
		return "Weapon Use"
	if ind == 3:
		return "Armor Use"
	if ind == 4:
		return "First Aid %i" % magnitude
	if ind == 5:
		return "Stealth %i" % magnitude
	if ind == 6:
		return "Searching %i" % magnitude
	if ind == 7:
		return "Open Doors"
	if ind == 8:
		return "Running"
	if ind == 9:
		return "Digging"
	if ind == 10:
		return "Swimming"
	if ind == 11:
		return "Vaulting"

def num_to_faculty_description(ind, magnitude=1):
	if ind == 0:
		return "With this, you can remember what terrain you've seen."
	if ind == 1:
		return "Each parry lets you block one more attack. Stand still to regain parries slowly."
	if ind == 2:
		return "You can use weapons. Weapons are essential to proper parrying, and some do more damage than your limbs."
	if ind == 3:
		return "You can now wear armor, just like the filth you hunt. It reduces the damage from each landed blow."
	if ind == 4:
		return "This much knowledge of first aid lets you regain a wound if you have %i or fewer left. Not for combat use!"
	if ind == 5:
		return "You can duck down to hide behind or in low obstructions."
	if ind == 6:
		return "You can see things that are hiding behind or in low obstructions."
	if ind == 7:
		return "You can open doors without making a racket."
	if ind == 8:
		return "You can run at the cost of your defenses. Press r to convert parries into extra spaces of movement."
	if ind == 9:
		return "You can go to where the bodies are buried..."
	if ind == 10:
		return "You can cross over deep water."
	if ind == 11:
		return "With a bound, you can now vault over low obstacles."

def make_faculty_list(mapping=0, parry=0, weapon=0, armor=0, first_aid=0, stealth=0, 
	search=0, doors=0, run=0, dig=0, swim=0, vault=0):

	return [mapping, parry, weapon, armor, first_aid, stealth, search, doors, run, dig, swim, vault]

def mindeating_menu(eaten_mind):
	options = []

	for i in range(len(player.mind.skills)):
		if eaten_mind.skills[i] > player.mind.skills[i]:

			options.append( [num_to_faculty_name(i, player.mind.skills[i] + 1), num_to_faculty_description(i, player.mind.skills[i] + 1), i] )

	if len(options) == 0:
		eaten_mind.owner.name += ", mindless"
		eaten_mind.owner.mind = None
		log('This mind had nothing new in it! Disgusting!', libtcod.red)
		return -1

	choice = triple_menu("MMM! What to gain from this mind?", options)

	if choice == 'no-choice':
		log('You resist the urge to eat this mind...', libtcod.blue)
		return -1

	eaten_mind.owner.name += ", mindless"
	eaten_mind.owner.mind = None

	return choice

def is_walkable(x, y):
	if not cur_map[x][y].walkable:
		return False

	for obj in objects:
		if not obj.walkable and obj.x == x and obj.y == y:
			return False
	return True

def in_range(x, y):
	if 0 <= x < curr_map_width and 0 <= y < curr_map_height:
		return True
	else:
		return False

def roll(low, high):
	return random.randint(low, high)

def chance(some, outof):
	# There is a 3 out 7 chance that this happens:
	# it happens if chance(3,7)
	return roll(1,outof) <= some

def random_choice(options):
	# chooses uniformly from a list
	return options[roll(0, len(options) - 1)]

# libtcod.console_set_custom_font('arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_set_custom_font('terminal12x12.png', libtcod.FONT_LAYOUT_ASCII_INROW)

libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'BLANK GAME')

libtcod.sys_set_fps(LIMIT_FPS)
libtcod.console_set_keyboard_repeat(200, 1000/LIMIT_FPS)

initialize_ascii_maps()

panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

libtcod.console_set_default_background(panel, libtcod.darkest_blue)

menu = libtcod.console_new(MENU_WIDTH, MENU_MAX_HEIGHT)

libtcod.console_set_default_background(menu, libtcod.darkest_blue)
libtcod.console_set_default_foreground(menu, libtcod.white)

main_menu()