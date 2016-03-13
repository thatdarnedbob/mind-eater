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

VILLAGE_TILES_HIGH = 6
VILLAGE_TILES_WIDE = 6
VILLAGE_TILE_SIZE = 20

LIMIT_FPS = 25
FOV_ALGO = 0


TORCH_RADIUS = 10
ENEMY_SIGHT = 6

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

		libtcod.console_print(0, SCREEN_WIDTH / 5, SCREEN_HEIGHT / 2 - 3, 'a) New Game')
		libtcod.console_print(0, SCREEN_WIDTH / 5, SCREEN_HEIGHT / 2 - 1, 'b) What makes MIND EATER different?')
		libtcod.console_print(0, SCREEN_WIDTH / 5, SCREEN_HEIGHT / 2 + 1, 'c) Exit')


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
			# when saving and loading are reliable again, add them back in here
			# load_game()
			# play_game()
			instruction_menu()
		elif index == 2:
			exit(0)

	exit(0)

def instruction_menu():
	libtcod.console_set_default_background(0, libtcod.darkest_blue)
	libtcod.console_set_default_foreground(0, libtcod.yellow)
	libtcod.console_set_background_flag(0, libtcod.BKGND_DEFAULT)
	libtcod.console_set_alignment(0, libtcod.LEFT)

	while not libtcod.console_is_window_closed():

		libtcod.console_clear(0)

		# We present the main menu

		libtcod.console_print(0, 15, SCREEN_HEIGHT / 2 - 9, 'You start off really sucky')
		libtcod.console_print(0, 15, SCREEN_HEIGHT / 2 - 5, 'But eventually you\'ll rule.')
		libtcod.console_print(0, 15, SCREEN_HEIGHT / 2 - 1, 'Stand over a body,')
		libtcod.console_print(0, 15, SCREEN_HEIGHT / 2 + 3, 'and hit e to eat its mind!')
		libtcod.console_print(0, 15, SCREEN_HEIGHT / 2 + 7, 'Press ENTER to return.')


		# this sends everything from the console to the screen.

		libtcod.console_flush()

		# some super basic input handling here. The key.c - ord('a') kinda just shanks a 0 - max int out of a lowercase letter

		#key = libtcod.console_wait_for_keypress(True)
		mouse = libtcod.Mouse()
		key = libtcod.Key()

		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)

		if key.vk == libtcod.KEY_ENTER or key.vk == libtcod.KEY_KPENTER:
			main_menu()

	exit(0)

def new_game():
	global player, game_state, game_log, target, lookback, objects, player_wait, cooldown

	if os.path.isfile('savegame'):
		os.remove('savegame')

	# create player
	player = Object(0, 0, '@', 'the Mind Eater', libtcod.white, walkable=False, always_visible=True, fighter=player_fighter(), mind=player_mind())
	target = None

	make_village_map()
	initialize_fov()

	game_log = []

	log('Dusk is settling...', libtcod.white)
	log('AND YOU ARE THE MIND EATER', libtcod.red)
	log('PRESS e TO EAT A CORPSE\'S MIND', libtcod.red)
 
	game_state = 'playing'
	lookback = 0
	player_wait = 0
	cooldown = 7

	#player.start_with(axe(0, 0))

	for obj in objects:
		if obj.fighter is not None:
			obj.fighter.parries_left = obj.fighter.max_parries

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
	file['cur_map_width'] = cur_map_width
	file['cur_map_height'] = cur_map_height
	file['target'] = target

	file.close()

def load_game():
	global cur_map, objects, player, game_state, game_log, board, cur_map_width, cur_map_height, target, lookback
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

	cur_map_width = file['cur_map_width']
	cur_map_height = file['cur_map_height']
	board = libtcod.console_new(cur_map_width, cur_map_height)

	target = file['target']

	file.close()

	os.remove('savegame')

	initialize_fov()

	lookback = 0

def play_game():
	global camera_x, camera_y, key, mouse, fov_recompute, player_wait

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
			#if game_state is not 'dead':
			#	save_game()
			exit(0)

		# monsters can go?

		if player_wait > 0:
			player_action = 'waiting'
			player_wait -= 1

		if game_state == 'playing' and player_action != 'no-turn':
			fov_recompute = True
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
			self.mind.name = 'A %s`s mind.'%self.name
			self.mind.desc = 'A %s`s mind.'%self.name

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
		if not in_range(new_x, new_y):
			return False
		if is_walkable(new_x, new_y):
			self.x = new_x
			self.y = new_y
			return True
		elif cur_map[new_x][new_y].type == 'water' and self.mind is not None and self.mind.skills[10] > 0:
			self.x = new_x
			self.y = new_y
			return True
		elif cur_map[new_x][new_y].transparent and in_range(new_x+dx, new_y+dy) and is_walkable(new_x+dx, new_y+dy) and self.mind is not None and self.mind.skills[11] > 0:
			self.x = new_x + dx
			self.y = new_y + dy
			if cur_map[new_x][new_y].type == 'window':
				cur_map[new_x][new_y].change_type('broken window')
				say('The window shatters!', libtcod.light_blue, new_x, new_y, 15)
				for obj in objects:
					if obj.ai is not None and self.distance_to(obj) < 15:
						obj.ai.get_message('alert', new_x, new_y)

			return True
		else:
			return False

	def wander(self):
		new_x = roll(-1,1) + self.x
		new_y = roll(-1,1) + self.y

		if in_range(new_x, new_y) and is_walkable(new_x, new_y):
			self.x = new_x
			self.y = new_y
			return True
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
		if not success and dir_x != 0 and dir_y != 0:
			if roll(0,1) == 0:
				self.move(dir_x, 0)
			else:
				self.move(0, dir_y)
		elif not success and dir_x == 0:
			if roll(0,1) == 0:
				self.move(-1, dir_y)
			else:
				self.move(1, dir_y)
		elif not success and dir_y == 0:
			if roll(0,1) == 0:
				self.move(dir_x, -1)
			else:
				self.move(dir_x, 1)

	def move_away(self, target_x, target_y):
		dx = self.x - target_x
		dy = self.y - target_y

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
				return self.move(dir_x, 0)
			else:
				return self.move(0, dir_y)

		return success

	def move_astar(self, target_x, target_y):
		# Create an FOV map tht has the dimensions of the map
		fov = libtcod.map_new(cur_map_width, cur_map_height)

		# Scan the current map each turn and set all the walks as unwalkable
		for y1 in range(cur_map_height):
			for x1 in range(cur_map_width):
				libtcod.map_set_properties(fov, x1, y1, cur_map[x1][y1].transparent, cur_map[x1][y1].walkable)

		# Allocate an A* path
		# 1.41 is the normal cost of moving diagonally; set to 0.0 to prohibit diagonal moes.

		my_path = libtcod.path_new_using_map(fov, 1.41)

		# Compute the path between self's coordinates and the target's coordinates
		libtcod.path_compute(my_path, self.x, self.y, target_x, target_y)

		# Check if the path exists, and also if it is less than 25 tiles
		# Path size matter because the damn monsters might go on a marathon to clear a blocked hallway.

		if not libtcod.path_is_empty(my_path) and libtcod.path_size(my_path) < 25:
			# Find the next coordinates in the computed full path
			x, y = libtcod.path_walk(my_path, True)
			if x and y:
				self.x = x
				self.y = y

		else:
			# Keep the old move function as a backup so that if there are no paths
			# The monster will still try to move towards the player (closer to the corridor opening)
			self.move_towards(target_x, target_y)

		libtcod.path_delete(my_path)

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

		# show if it's set to 'always visible' and on an explored tile
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
		for thing in self.inventory:
			if thing.item.slot == slot and thing.item.equipped:
				return thing.item

	def start_with(self, an_item):
		#self.inventory.append(an_item)
		objects.append(an_item)
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

		self.runs = 0

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
	def max_runs(self):
		bonus = sum(buff.max_runs_bonus for buff in get_all_buffs(self.owner))
		return self.max_parries + bonus

	@property
	def max_wounds(self): # return the actual max_wounds by summing up the max_wounds bonus from all buffs
		bonus = sum(buff.max_wounds_bonus for buff in get_all_buffs(self.owner))
		return self.base_max_wounds + bonus

	def attack(self, target):
		target.fighter.take_damage(self.power)

	def take_damage(self, damage, unblockable=False):
		if self.parries_left >= 1 and self.owner.get_equipped_in_slot('weapon') is not None and not unblockable:
			self.parries_left -= 1
			log(self.owner.name.capitalize() + ' parries the blow!')
		else:
			net_damage = max(0, damage - self.armor)
			self.wounds -= net_damage
			if net_damage == 0:
				log('The blow was absorbed by ' + self.owner.name + '\'s armor!')
			elif self.owner.name == 'door' and player.mind.skills[7] == 1:
				log('You creep through the door, turning the handle slowly...', libtcod.yellow)
			elif self.owner.name == 'gate' and player.mind.skills[7] == 1:
				log('You creep through the gate, unlatching it carefully...', libtcod.yellow)
			else:
				log('The blow lands solidly on ' + self.owner.name + '!')
			if self.wounds <= 0:
				self.wounds = 0
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

	def first_aid(self):
		global player_wait

		skill_level = self.owner.mind.skills[4]
		if skill_level >= self.wounds and self.max_wounds > self.wounds:
			self.wounds += 1
		if self.owner is player:
			player_wait = 6

	def run_prep(self):
		if self.runs < self.max_runs and self.parries_left > 0:
			self.parries_left -= 1
			self.runs += 1
			return 'run-prep'

def player_fighter():
	return Fighter(wounds=3, defense=0, power=1, armor=0, xp=0, death_function=player_death)

def player_mind():
	# could buffed for testing purposes. should start out all zeros
	return Mind(make_faculty_list())
	# for cheats, come here! just remove the # from the next line, and put on in front of the previous line.
	# return Mind(make_faculty_list(armor=1, weapon=1, mapping=1, parry=3, stealth=1, throw=1))

def farmer(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = FarmerAI()
	mind_comp = Mind(make_faculty_list(mapping=1, parry=1, weapon=1, first_aid=1, doors=1, dig=1))
	monster =  Object(x, y, 'F', 'farmer', libtcod.yellow, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.start_with(peasant_tool(x, y))
	monster.mind.desc = 'A farmer is concerned with scratching out a meager living, and his mind reflects that.'
	return monster

def lumber_worker(x, y):
	fighter_comp = Fighter(wounds = 2, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = LumberAI()
	mind_comp = Mind(make_faculty_list(mapping=1, parry=1, weapon=1, doors=1))
	monster = Object(x, y, 'L', 'lumberjack', libtcod.sepia, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.start_with(axe(x, y))
	monster.mind.desc = 'A lumberjack sure knows how to swing an axe. Not much else.'
	return monster

def hunter(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = HunterAI()
	mind_comp = Mind(make_faculty_list(mapping=1, parry=1, weapon=1, stealth=1, search=1, doors=1, run=1, throw=1))
	monster = Object(x, y, 'H', 'hunter', libtcod.red, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.start_with(spear(x, y))
	monster.start_with(javelin(x, y))
	monster.mind.desc = 'A hunter\'s skills let him become one with the night.'
	return monster

def fisherman(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = FisherAI()
	mind_comp = Mind(make_faculty_list(mapping=1, doors=1, swim=1))
	monster = Object(x, y, 'A', 'angler', libtcod.light_blue, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.mind.desc = 'To fish in a pond this size requires a special sort of mind.'
	return monster

def guard(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = BasicAI()
	mind_comp = Mind(make_faculty_list(mapping=1, parry=2, weapon=1, armor=1, doors=1, run=1))
	monster = Object(x, y, 'G', 'guard', libtcod.white, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.start_with(sword(x, y))
	monster.start_with(shield(x, y))
	monster.start_with(leather_armor(x, y))
	monster.mind.desc = 'A guard\'s mind is a killing machine, but you would have had to be better already to get at this, right?'
	return monster

def village_guard(x, y, tlx, tly, state=0):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = VillageGuardAI(tlx, tly, state)
	mind_comp = Mind(make_faculty_list(mapping=1, parry=2, weapon=1, armor=1, doors=1, run=1))
	monster = Object(x, y, 'G', 'guard', libtcod.white, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.start_with(sword(x, y))
	monster.start_with(shield(x, y))
	monster.start_with(leather_armor(x, y))
	monster.mind.desc = 'A guard\'s mind is a killing machine, but you would have had to be better already to get at this, right?'
	return monster

def mad_mage(x, y):
	fighter_comp = Fighter(wounds=2, defense=0, power=6, armor=1, xp=0, death_function=monster_death)
	ai_comp = MadMageAI(x, y)
	mind_comp = Mind(make_faculty_list(magic=1))
	monster = Object(x, y, 'W', 'Mad Wizard', libtcod.cyan, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.start_with(magic_amulet(x,y))
	monster.mind.desc = 'Hopefully you can make sense of the swirling craze within...'
	return monster

def cow(x, y):
	fighter_comp = Fighter(wounds = 6, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = CowAI()
	mind_comp = Mind(make_faculty_list(run=1, vault=1))
	monster = Object(x, y, 'C', 'cow', libtcod.white, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.mind.desc = 'You never know what you may find.'
	return monster

def chicken(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 0, armor=0, xp = 0, death_function=monster_death)
	ai_comp = ChickenAI()
	mind_comp = Mind(make_faculty_list(search=2, dig=1))
	monster =  Object(x, y, 'c', 'chicken', libtcod.dark_orange, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.mind.desc = 'You may be surprised by how observant these birds are.'
	return monster

def dog(x, y):
	fighter_comp = Fighter(wounds = 1, defense = 0, power = 1, armor=0, xp = 0, death_function=monster_death)
	ai_comp = AlertDogAI()
	mind_comp = Mind(make_faculty_list(mapping=1, stealth=1, search=2, run=1, dig=1, swim=1, vault=1))
	monster = Object(x, y, 'd', 'dog', libtcod.light_sepia, walkable=False, fighter=fighter_comp, ai=ai_comp, mind=mind_comp)
	monster.mind.desc = 'Man\'s best friend. But you\'re the furthest thing from a man.'
	return monster

def great_corpse(x, y):
	corpse_type = ''
	mind_comp = None
	if chance(1,2):
		corpse_type = 'great warrior'
		mind_comp = Mind(make_faculty_list(mapping=1, parry=4, weapon=1, armor=1, first_aid=3))
		monster = Object(x, y, '%', 'remains of a %s' % corpse_type, libtcod.gray, walkable=True, mind=mind_comp)
		monster.mind.name = 'A great warrior\'s mind.'
		monster.mind.desc = 'With this, your skills could be legendary...'
		return monster
	else:
		corpse_type = 'great thief'
		mind_comp = Mind(make_faculty_list(mapping=1, parry=2, weapon=1, stealth=4, search=4, vault=1))
		monster = Object(x, y, '%', 'remains of a %s' % corpse_type, libtcod.gray, walkable=True, mind=mind_comp)
		monster.mind.name = 'A great thief\'s mind.'
		monster.mind.desc = 'With this, your skills could be legendary...'
		return monster

def fine_corpse(x, y):
	corpse_type = ''
	mind_comp = None
	if chance(1,4):
		corpse_type = 'warrior'
		mind_comp = Mind(make_faculty_list(mapping=1, parry=2, weapon=1, armor=1, first_aid=1))
		monster = Object(x, y, '%', 'remains of a %s' % corpse_type, libtcod.gray, walkable=True, mind=mind_comp)
		monster.mind.name = 'A warrior\'s mind.'
		monster.mind.desc = 'This was a lot easier than killing a guard.'
		return monster

	elif chance(1,3):
		corpse_type = 'thief'
		mind_comp = Mind(make_faculty_list(mapping=1, stealth=2, search=2, vault=1))
		monster = Object(x, y, '%', 'remains of a %s' % corpse_type, libtcod.gray, walkable=True, mind=mind_comp)
		monster.mind.name = 'A thief\'s mind.'
		monster.mind.desc = 'You could learn a thing or two...'
		return monster

	elif chance(1,2):
		corpse_type = 'healer'
		mind_comp = Mind(make_faculty_list(mapping=1, first_aid=2, run=1))
		monster = Object(x, y, '%', 'remains of a %s' % corpse_type, libtcod.gray, walkable=True, mind=mind_comp)
		monster.mind.name = 'A healer\'s mind.'
		monster.mind.desc = 'If he only knew what his education would enable.'
		return monster

	else:
		corpse_type = 'athlete'
		mind_comp = Mind(make_faculty_list(run=3, swim=1, vault=1))
		monster = Object(x, y, '%', 'remains of a %s' % corpse_type, libtcod.gray, walkable=True, mind=mind_comp)
		monster.mind.name = 'An athlete\'s mind.'
		monster.mind.desc = 'If only you could use your body half as well!'
		return monster

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

	# loot splosion!

	while len(monster.inventory) > 0:
		xs = roll(-1, 1)
		ys = roll(-1, 1)
		if is_walkable(xs + monster.x, ys + monster.y):
			thing = monster.inventory[0]
			thing.item.drop(monster)
			thing.x = xs + monster.x
			thing.y = ys + monster.y
					
def door_open_death(monster):
	global objects

	if player.mind.skills[7] == 0:

		log('You shatter the door with a mighty crash!', libtcod.yellow)

		for obj in objects:
				if obj.ai is not None and monster.distance_to(obj) < 25 and obj is not monster:
					obj.ai.get_message('alert', player.x, player.y)

		monster.fighter = None
		objects.remove(monster)
		cur_map[monster.x][monster.y].change_type('wood floor')
		initialize_fov()

	else:

		player.x = monster.x
		player.y = monster.y

		monster.fighter.wounds = 1
		initialize_fov()

def gate_open_death(monster):
	global objects

	if player.mind.skills[7] == 0:
		log('You smash through the gate with a mighty crash!', libtcod.yellow)

		for obj in objects:
				if obj.ai is not None and monster.distance_to(obj) < 25 and obj is not monster:
					obj.ai.get_message('alert', player.x, player.y)

		monster.fighter = None
		objects.remove(monster)
		cur_map[monster.x][monster.y].change_type('grass')
	else:

		player.x = monster.x
		player.y = monster.y

		monster.fighter.wounds = 1
		initialize_fov()

def get_all_buffs(buffed):
	# implement buffs later
	buff_list = []

	if buffed.mind is not None:
		buff_list.append(Buff(max_parries_bonus=buffed.mind.skills[1]))

	if buffed.mind is not None:
		buff_list.append(Buff(max_runs_bonus=buffed.mind.skills[8]))

	for thing in buffed.inventory:
		if thing.item is not None and thing.item.equipped:
			buff_list.append(thing.item)

	return buff_list

def enemy_can_see_player(monster):
	if player.mind.skills[5] < monster.mind.skills[6] or player.mind.skills[5] == 0:
		return libtcod.map_is_in_fov(enemy_fov_map, monster.x, monster.y)
	elif cur_map[player.x][player.y].hiding_spot and player.distance_to(monster) > 1.5:
		return False
	else:
		return libtcod.map_is_in_fov(enemy_fov_map, monster.x, monster.y) and libtcod.map_is_in_fov(stealth_fov_map, monster.x, monster.y)

def player_can_see_enemy(monster):
	# unused
	if monster.mind is None:
		return libtcod.map_is_in_fov(fov_map, monster.x, monster.y)
	if player.mind.skills[6] < monster.mind.skills[5] or monster.mind.skills[5] == 0:
		return libtcod.map_is_in_fov(fov_map, monster.x, monster.y)
	elif cur_map[monster.x][monster.y].hiding_spot and player.distance_to(monster) > 1.5:
		return False
	else:
		return (libtcod.map_is_in_fov(fov_map, monster.x, monster.y) and libtcod.map_is_in_fov(stealth_fov_map, monster.x, monster.y))

class Buff:
	def __init__(self, power_bonus=0, armor_bonus=0, max_wounds_bonus=0, max_parries_bonus=0, max_runs_bonus=0):
		self.power_bonus = power_bonus
		self.armor_bonus = armor_bonus
		self.max_wounds_bonus = max_wounds_bonus
		self.max_parries_bonus = max_parries_bonus
		self.max_runs_bonus = max_runs_bonus

class Mind:
	def __init__(self, skills):
		self.skills = skills
		self.name = ''
		self.desc = ''

class BasicAI:
	# This is AI for a creature that just moves toward the player if it sees them, and tries to attack
	def take_turn(self):
		monster = self.owner

		if enemy_can_see_player(monster):
			# move towards the player if far away
			if monster.distance_to(player) >= 2:
				monster.move_towards(player.x, player.y)

			elif player.fighter.wounds > 0:
				monster.fighter.attack(player)

			newAI = AlertAI(player.x, player.y)
			monster.ai = newAI
			newAI.owner = monster

	def get_message(self, message, x, y):
		return None

class AlertAI():
	# This is an AI that is aware of the pleyer, and moves to kill them.
	def __init__(self, x, y):
		self.target_x = x
		self.target_y = y

	def take_turn(self):
		monster = self.owner

		if enemy_can_see_player(monster):
			if monster.distance_to(player) >= 2:
				monster.move_towards(player.x, player.y)

			elif player.fighter.wounds > 0:
				monster.fighter.attack(player)
			self.target_x = player.x
			self.target_y = player.y
		else:
			monster.move_towards(self.target_x, self.target_y)

	def get_message(self, message, x, y):
		return None

class PsychoAI():
	# this AI goes all, out, without regard to sightlines or what ever.
	def take_turn(self):
		monster = self.owner

		dist = monster.distance_to(player)
		if dist < 40:
			monster.move_astar(player.x, player.y)

		if player.fighter.wounds > 0 and dist < 2:
			monster.fighter.attack(player)

	def get_message(self, message, x, y):
		return None

class SurprisedPackAI():
	def __init__(self, surprise_turns, x, y):
		self.shock = max(0, surprise_turns)
		self.x_sighted = x
		self.y_sighted = y

	def take_turn(self):
		monster = self.owner

		if self.shock > 0:
			self.shock -= 1
			return
		else:
			newAI = AlertPackAI(self.x_sighted, self.y_sighted)
			monster = self.owner
			say('Someone shouts: "I have seen the creature!"', libtcod.white, self.x_sighted, self.y_sighted, 25)

			for obj in objects:
				if obj.ai is not None and monster.distance_to(obj) < 25 and obj is not monster:
					obj.ai.get_message('alert', player.x, player.y)

			monster.ai = newAI
			newAI.owner = monster
			monster.ai.take_turn()
			return

	def get_message(self, message, x, y):
		return None

class AlertPackAI():

	def __init__(self, x, y):
		self.target_x = x
		self.target_y = y
		self.wait = 20

	def take_turn(self):
		monster = self.owner

		self.wait = max(self.wait -1, 0)
		if enemy_can_see_player(monster):

			self.target_x = player.x
			self.target_y = player.y

			friendly_count = 0
			for obj in objects:
				if obj.fighter is not None and obj is not player and obj.distance_to(player) < 6:
					friendly_count += 1

			if friendly_count > 2:
				if monster.distance_to(player) >= 2:
					monster.move_towards(player.x, player.y)

				elif player.fighter.wounds > 0:
					monster.fighter.attack(player)
			elif monster.distance_to(player) < 5:
				monster.move_away(player.x, player.y)
			else:
				monster.move_towards(player.x, player.y)

			if self.wait == 0:

				say('Someone shouts: "The creature is here!"', libtcod.white, self.target_x, self.target_y, 25)

				for obj in objects:
					if obj.ai is not None and monster.distance_to(obj) < 25 and obj is not monster:
						obj.ai.get_message('alert', player.x, player.y)
				self.wait += 25

		elif monster.fighter.parries_left < monster.fighter.max_parries:
			monster.fighter.rest
		else:
			monster.move_towards(self.target_x, self.target_y)

	def get_message(self, message, x, y):
		if message == 'alert':
			self.target_x = x
			self.target_y = y

class SurprisedLonerAI():
	def __init__(self, surprise_turns, x, y):
		self.shock = max(0, surprise_turns)
		self.x_sighted = x
		self.y_sighted = y

	def take_turn(self):
		monster = self.owner

		if self.shock > 0:
			self.shock -= 1
			return
		else:
			newAI = AlertLonerAI(self.x_sighted, self.y_sighted)
			monster = self.owner
			say('Someone shouts: "I have seen the creature!"', libtcod.white, self.x_sighted, self.y_sighted, 25)

			for obj in objects:
				if obj.ai is not None and monster.distance_to(obj) < 25 and obj is not monster:
					obj.ai.get_message('alert', player.x, player.y)

			monster.ai = newAI
			newAI.owner = monster
			monster.ai.take_turn()
			return

	def get_message(self, message, x, y):
		return None

class AlertLonerAI():

	def __init__(self, x, y):
		self.target_x = x
		self.target_y = y
		self.wait = 20

	def take_turn(self):
		monster = self.owner

		self.wait = max(self.wait - 1, 0)
		if enemy_can_see_player(monster):

			self.target_x = player.x
			self.target_y = player.y

			if monster.distance_to(player) < 2 and player.fighter.wounds > 0:
				monster.fighter.attack(player)
			elif monster.distance_to(player) < 6 and player.fighter.wounds > 0 and monster.get_equipped_in_slot('missile') is not None:
				missile = monster.get_equipped_in_slot('missile')
				if missile is not None:
					log('The %s threw a javelin! BRUTAL!'%monster.name, libtcod.red)
					player.fighter.take_damage(1, unblockable=True)
					monster.inventory.remove(missile.owner)
					new_jav = javelin(player.x, player.y)
					objects.append(new_jav)
					new_jav.send_to_back()
			elif monster.distance_to(player) >= 6:
				monster.move_towards(player.x, player.y)

			if self.wait == 0:

				say('Someone shouts: "The creature is here!"', libtcod.white, self.target_x, self.target_y, 25)

				for obj in objects:
					if obj.ai is not None and monster.distance_to(obj) < 25 and obj is not monster:
						obj.ai.get_message('alert', player.x, player.y)
				self.wait += 25

		elif monster.fighter.parries_left < monster.fighter.max_parries:
			monster.fighter.rest
		else:
			monster.move_towards(self.target_x, self.target_y)

	def get_message(self, message, x, y):
		if message == 'alert':
			self.target_x = x
			self.target_y = y

class FarmerAI():

	def __init__(self):
		self.wait = 0

	def take_turn(self):
		monster = self.owner

		if enemy_can_see_player(monster):
			newAI = SurprisedPackAI(player.mind.skills[5]+1, player.x, player.y)
			monster.ai = newAI
			newAI.owner = monster
			monster.ai.take_turn()
			log('The %s gasps in surprise!'%monster.name, libtcod.white)
			return
		elif self.wait > 0:
			self.wait -= 1
		elif cur_map[monster.x][monster.y].type == 'crops':
			chores = ['pruning', 'watering', 'weeding', 'killing a rat']
			monster.wander()
			say('The farmer begins %s.'%random.choice(chores), libtcod.white, monster.x, monster.y, 10)
			self.wait += roll(25,40)
		else:
			monster.wander()

	def get_message(self, message, x, y):
		if message == 'alert':
			newAI = AlertPackAI(x, y)
			monster = self.owner
			monster.ai = newAI
			newAI.owner = monster
			monster.ai.take_turn()
			return

class LumberAI():

	def __init__(self):
		self.wait = 0
		self.state = 'looking'
		self.progress = 0
		self.tree_x = 0
		self.tree_y = 0

	def take_turn(self):
		global cur_map
		monster = self.owner

		if enemy_can_see_player(monster):
			newAI = SurprisedPackAI(player.mind.skills[5]+1, player.x, player.y)
			monster.ai = newAI
			newAI.owner = monster
			monster.ai.take_turn()
			log('The %s gasps in surprise!'%monster.name, libtcod.white)
			return
		elif self.state == 'looking':
			monster.wander()
			for x in range(monster.x - 1, monster.x + 2):
				for y in range(monster.y - 1, monster.y + 2):
					if in_range(x, y) and cur_map[x][y].type=='tree':
						self.state = 'chopping'
						self.progress = 75
						self.tree_x = x
						self.tree_y = y
		elif self.progress > 0:
			self.progress -= 1
			if self.progress % 25 == 0:
				say('The lumberjack chops at a tree.', libtcod.white, monster.x, monster.y, 15)
		else:
			self.state = 'looking'
			cur_map[self.tree_x][self.tree_y].change_type('grass')
			say('Someone shouts:"TIMBER!!!"', libtcod.white, monster.x, monster.y, 25)
			initialize_fov()

	def get_message(self, message, x, y):
		if message == 'alert':
			newAI = AlertPackAI(x, y)
			monster = self.owner
			monster.ai = newAI
			newAI.owner = monster
			monster.ai.take_turn()
			return

class FisherAI():

	def __init__(self):
		self.wait = 0

	def take_turn(self):
		monster = self.owner

		if enemy_can_see_player(monster):
			newAI = SurprisedPackAI(player.mind.skills[5]+1, player.x, player.y)
			monster.ai = newAI
			newAI.owner = monster
			monster.ai.take_turn()
			log('The %s gasps in surprise!'%monster.name, libtcod.white)
			return
		elif self.wait > 0:
			self.wait -= 1
		elif cur_map[monster.x][monster.y].type == 'shallow water':
			actions = ['setting a lure', 'casting', 'twiddling his thumbs', 'pulling in the line', 'checking the line']
			say('The angler begins %s.'%random.choice(actions), libtcod.white, monster.x, monster.y, 13)
			self.wait += roll(20,30)
		else:
			for x in range(monster.x - 5, monster.x + 6):
				for y in range(monster.y - 5, monster.y + 6):
					if in_range(x, y) and cur_map[x][y].type=='shallow water':
						monster.move_towards(x, y)
						return

	def get_message(self, message, x, y):
		if message == 'alert':
			newAI = AlertPackAI(x, y)
			monster = self.owner
			monster.ai = newAI
			newAI.owner = monster
			monster.ai.take_turn()
			return

class HunterAI():

	def __init__(self):
		self.wait = 0
		self.wander_count = 0

	def take_turn(self):
		monster = self.owner

		if enemy_can_see_player(monster):
			newAI = SurprisedLonerAI(player.mind.skills[5]+1, player.x, player.y)
			monster.ai = newAI
			newAI.owner = monster
			monster.ai.take_turn()
			log('The %s gasps in surprise!'%monster.name, libtcod.white)
			return
		elif self.wander_count > 0:
			monster.wander()
			self.wander_count -= 1
		elif self.wait > 0:
			self.wait -= 1
			if self.wait == 0:
				self.wander_count += roll(15,25)
		elif cur_map[monster.x][monster.y].type == 'shallow water':
			actions = ['lying in wait', 'setting a snare', 'skinning some game', 'preparing some bait', 'sharpening a javelin']
			say('The hunter begins %s.'%random.choice(actions), libtcod.white, monster.x, monster.y, 13)
			self.wait += roll(20,30)
		else:
			monster.wander()
						
	def get_message(self, message, x, y):
		if message == 'alert':
			newAI = AlertLonerAI(x, y)
			monster = self.owner
			monster.ai = newAI
			newAI.owner = monster
			monster.ai.take_turn()
			return

class CowAI():
	def __init__(self):
		self.state = 'calm'
		self.target_x = 0
		self.target_y =0

	def take_turn(self):
		the_cow = self.owner

		if self.state == 'calm':
			if the_cow.fighter.wounds < the_cow.fighter.max_wounds:
				log('The cow BELLOWS!!!', libtcod.violet)
				for obj in objects:
					if obj.ai is not None and the_cow.distance_to(obj) < 50 and obj is not the_cow:
						obj.ai.get_message('cow-rage', the_cow.x, the_cow.y)
				self.state = 'rage'
			else:
				the_cow.wander()
		elif self.state == 'rage':
			if the_cow.fighter.wounds < 3:
				self.state = 'flight'

			if enemy_can_see_player(the_cow):
				self.target_x = player.x
				self.target_y = player.y

				if the_cow.distance_to(player) >= 2:
					the_cow.move_towards(player.x, player.y)
				elif player.fighter.wounds > 0:
					the_cow.fighter.attack(player)
			else:
				the_cow.move_towards(self.target_x, self.target_y)
		else:
			if enemy_can_see_player(the_cow):
				the_cow.move_away(player.x, player.y)

	def get_message(self, message, x, y):

		if message == 'cow-rage':
			self.state = 'rage'
			log('A cow bellows in answer!')

class AlertDogAI():

	def __init__(self):
		self.seen_player = False
		self.target_x = 0
		self.target_y = 0
		self.friend = None
		self.wait = 1

	def take_turn(self):
		the_dog = self.owner

		if not self.seen_player:
			if enemy_can_see_player(the_dog):
				self.seen_player = True
				self.target_x = player.x
				self.target_y = player.y
				self.take_turn()
				return
			elif self.friend is None:
				min_dist = 25
				friendly = None
				for obj in objects:
					if obj.mind is not None and obj.mind.skills[7] > 0 and obj is not player:
						if obj.distance_to(the_dog) < min_dist:
							min_dist = obj.distance_to(the_dog)
							friendly = obj
				if friendly is not None:
					self.friend = friendly
			if self.friend is not None:
				the_dog.move_towards(self.friend.x, self.friend.y)
			else:
				the_dog.wander()
		
		if self.seen_player:
			if enemy_can_see_player(the_dog):
				self.target_x = player.x
				self.target_y = player.y

				if the_dog.distance_to(player) >= 2:
					the_dog.move_towards(player.x, player.y)
				elif player.fighter.wounds > 0:
					the_dog.fighter.attack(player)

				self.wait -= 1

				if self.wait == 0:

					say('BARK BARK BARK BARK BARK', libtcod.white, self.target_x, self.target_y, 45)

					for obj in objects:
						if obj.ai is not None and the_dog.distance_to(obj) < 45 and obj is not the_dog:
							obj.ai.get_message('alert', player.x, player.y)
					self.wait += 10

	def get_message(self, message, x, y):
		if message == 'alert':
			self.target_x = x
			self.target_y = y

class ChickenAI():

	def __init__(self):
		self.wait = roll(12,23)

	def take_turn(self):
		chick = self.owner

		if enemy_can_see_player(chick):
			if not chick.move_away(player.x, player.y):
				chick.wander()
		else:
			chick.wander()

		self.wait -= 1
		if self.wait == 0:
			say('cluck cluck cluck', libtcod.red, chick.x, chick.y, 12)
			self.wait += roll(12,23)

	def get_message(self, message, x, y):
		return

class SleepingPackAI():

	def __init__(self):
		self.wake_up_time = roll(7,12)
		self.waking = False
		self.snore_timer = roll(14,23)

	def take_turn(self):
		sleepy = self.owner

		if sleepy.fighter.max_parries > sleepy.fighter.parries_left or sleepy.fighter.max_wounds > sleepy.fighter.wounds:
			self.waking = True
			say('It\'s here! TO ARMS!', libtcod.white, sleepy.x, sleepy.y, 15)

		if not self.waking:
			self.snore_timer -= 1
			if self.snore_timer == 0:
				say('ZZZZZZZZZZZ', libtcod.blue, sleepy.x, sleepy.y, 10)
				self.snore_timer += roll(14, 23)
		else:
			self.wake_up_time -= 1
			if self.wake_up_time == 0:
				if enemy_can_see_player(sleepy):
					for obj in objects:
						if obj.ai is not None and sleepy.distance_to(obj) < 15 and obj is not sleepy:
							obj.ai.get_message('alert', player.x, player.y)
				newAI = AlertPackAI(sleepy.x, sleepy.y)
				sleepy.ai = newAI
				newAI.owner = sleepy
				sleepy.ai.take_turn()
				return

	def get_message(self, message, x, y):
		if message == 'alert':
			self.waking = True

class SleepingLonerAI():
	
	def __init__(self):
		self.wake_up_time = roll(6,11)
		self.waking = False
		self.snore_timer = roll(14,23)

	def take_turn(self):
		sleepy = self.owner

		if sleepy.fighter.max_parries > sleepy.fighter.parries_left or sleepy.fighter.max_wounds > sleepy.fighter.wounds:
			self.waking = True
			say('It\'s here! TO ARMS!', libtcod.white, sleepy.x, sleepy.y, 15)

		if not self.waking:
			self.snore_timer -= 1
			if self.snore_timer == 0:
				say('ZZZZZZZZZZZ', libtcod.blue, sleepy.x, sleepy.y, 10)
				self.snore_timer += roll(14, 23)
		else:
			self.wake_up_time -= 1
			if self.wake_up_time == 0:
				if enemy_can_see_player(sleepy):
					for obj in objects:
						if obj.ai is not None and sleepy.distance_to(obj) < 15 and obj is not sleepy:
							obj.ai.get_message('alert', player.x, player.y)
				newAI = AlertLonerAI(sleepy.x, sleepy.y)
				sleepy.ai = newAI
				newAI.owner = sleepy
				sleepy.ai.take_turn()
				return

	def get_message(self, message, x, y):
		if message == 'alert':
			self.waking = True

class SleepingDogAI():

	def __init__(self):
		self.wake_up_time = roll(4,9)
		self.waking = False
		self.snore_timer = roll(14,23)

	def take_turn(self):
		sleepy = self.owner

		if sleepy.fighter.max_parries > sleepy.fighter.parries_left or sleepy.fighter.max_wounds > sleepy.fighter.wounds:
			self.waking = True
			say('BARK BARK BARK', libtcod.white, sleepy.x, sleepy.y, 25)

		if not self.waking:
			self.snore_timer -= 1
			if self.snore_timer == 0:
				say('ZZZZZZZZZZZ', libtcod.blue, sleepy.x, sleepy.y, 10)
				self.snore_timer += roll(14, 23)
		else:
			self.wake_up_time -= 1
			if self.wake_up_time == 0:
				if enemy_can_see_player(sleepy):
					for obj in objects:
						if obj.ai is not None and sleepy.distance_to(obj) < 25 and obj is not sleepy:
							obj.ai.get_message('alert', player.x, player.y)
				newAI = AlertDogAI()
				sleepy.ai = newAI
				newAI.owner = sleepy
				sleepy.ai.take_turn()
				return

	def get_message(self, message, x, y):
		if message == 'alert':
			self.waking = True

class VillageGuardAI():

	def __init__(self, tlx, tly, state=0):
		self.tlx = tlx
		self.tly = tly
		self.state = state
		self.wait = 0

	def take_turn(self):
		monster = self.owner

		if enemy_can_see_player(monster):
			new_ai = AlertAI(player.x, player.y)
			monster.ai = new_ai
			new_ai.owner = monster

			new_ai.take_turn()
			return
		if self.wait > 0:
			self.wait -= 1
			return

		if self.state == 0:
			monster.move_towards(self.tlx + 20, self.tly + 18)
			if monster.x == self.tlx + 20 and monster.y == self.tly + 18:
				self.state = 1
				self.wait = 5
		elif self.state == 1:
			monster.move_towards(self.tlx + 39, self.tly + 19)
			if monster.x == self.tlx + 39 and monster.y == self.tly + 19:
				self.state = 2
				self.wait = 5
		elif self.state == 2:
			monster.move_towards(self.tlx + 21, self.tly + 20)
			if monster.x == self.tlx + 21 and monster.y == self.tly + 20:
				self.state = 3
				self.wait = 5
		elif self.state == 3:
			monster.move_towards(self.tlx + 20, self.tly + 39)
			if monster.x == self.tlx + 20 and monster.y == self.tly + 39:
				self.state = 4
				self.wait = 5
		elif self.state == 4:
			monster.move_towards(self.tlx + 19, self.tly + 21)
			if monster.x == self.tlx + 19 and monster.y == self.tly + 21:
				self.state = 5
				self.wait = 5
		elif self.state == 5:
			monster.move_towards(self.tlx, self.tly + 20)
			if monster.x == self.tlx and monster.y == self.tly + 20:
				self.state = 6
				self.wait = 5
		elif self.state == 6:
			monster.move_towards(self.tlx + 18, self.tly + 19)
			if monster.x == self.tlx + 18 and monster.y == self.tly + 19:
				self.state = 7
				self.wait = 5
		elif self.state == 7:
			monster.move_towards(self.tlx + 19, self.tly)
			if monster.x == self.tlx +19 and monster.y == self.tly:
				self.state = 0
				self.wait = 5

	def get_message(self, message, x, y):
		return None

class MadMageAI():
	def __init__(self, center_x, center_y):
		self.center_x = center_x
		self.center_y = center_y
		self.state = 0
		self.babble = roll(3,6)

	def take_turn(self):
		wiz = self.owner

		if enemy_can_see_player(wiz):
			self.state = 4

		if self.state == 0:
			wiz.move_towards(self.center_x, self.center_y - 7)
			if wiz.x == self.center_x and wiz.y == self.center_y -7:
				self.state = 1
		if self.state == 1:
			wiz.move_towards(self.center_x+7, self.center_y)
			if wiz.x == self.center_x + 7 and wiz.y == self.center_y:
				self.state = 2
		if self.state == 2:
			wiz.move_towards(self.center_x, self.center_y +7)
			if wiz.x == self.center_x and wiz.y == self.center_y+7:
				self.state = 3
		if self.state == 3:
			wiz.move_towards(self.center_x -7, self.center_y)
			if wiz.x == self.center_x - 7 and wiz.y == self.center_y:
				self.state = 0
		if self.state == 4:
			if enemy_can_see_player(wiz):
				if wiz.distance_to(player) >= 2:
					wiz.move_towards(player.x, player.y)

				elif player.fighter.wounds > 0:
					wiz.fighter.attack(player)
			else:
				wiz.wander()

		say('The mad wizard babbles...%i'%self.state, libtcod.fuchsia, wiz.x, wiz.y, 10)

	def get_message(self, message, x, y):
		return

def say(msg, col, x, y, vol):
	if player.distance(x,y) < vol:
		log(msg, col)

class Item():
	# object can have an item component. this makes them an item. 
	# so items can display themselves, move, have various other componenets
	# but the item com be placed in another object's inventory.
	# while in the inventory, that object can use the item,
	# or equip the item. So each item has something that happens when it is used,
	# and a slot to be equipped in, and various bonuses, and descriptions.
	
	def __init__(self, use_function=None, equippable=False, slot=None, power_bonus=0, armor_bonus=0,
		max_parries_bonus=0, max_runs_bonus=0, max_wounds_bonus=0):
		self.use_function = use_function
		self.equippable = equippable
		self.slot = slot
		self.power_bonus = power_bonus
		self.armor_bonus = armor_bonus
		self.max_parries_bonus = max_parries_bonus
		self.max_runs_bonus = max_runs_bonus
		self.max_wounds_bonus = max_wounds_bonus
		self.equipped = False

	def pick_up(self, picker):

		
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
		self.owner.send_to_back()

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
		if user is player:
			log('You picked up a ' + self.owner.name + '!', libtcod.green)
		old_shiz = user.get_equipped_in_slot(self.slot)
		if old_shiz is not None:
			old_shiz.drop(user)

		if user.mind.skills[2] == 0 and self.slot == 'weapon':
			if user is player:
				log('But you need to learn how to use weapons first!')
			return
		elif user.mind.skills[3] == 0 and self.slot == 'armor':
			if user is player:
				log('But you need to learn how to use armor first!')
			return
		elif user.mind.skills[12] == 0 and self.slot == 'missile':
			if user is player:
				log('But you need to learn how to use javelins first!')
			return
		else:
			self.equipped = True
			user.inventory.append(self.owner)
			objects.remove(self.owner)

		if self.slot == 'necklace' and user is player:
			player.fighter.wounds = player.fighter.max_wounds

		if user.fighter is not None:
			user.fighter.parries_left = min(user.fighter.parries_left, user.fighter.max_parries)

		if user is player:
			log('Equipped a ' + self.owner.name + ' as ' + self.slot + '.', libtcod.light_green)

	def unequip(self, user):
		if not self.equipped:
			return None
		self.equipped = False
		if user.fighter is not None:
			user.fighter.parries_left = min(user.fighter.parries_left, user.fighter.max_parries)

def no_use():
	log('This thing isn\'t actually usable.')

def sword(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='weapon', power_bonus=1)
	return Object(xpos, ypos, '/', 'sword', libtcod.light_gray, walkable=True, always_visible=True, item=item_comp)

def axe(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='weapon', power_bonus=2, max_parries_bonus=-1)
	return Object(xpos, ypos, 'P', 'axe', libtcod.light_green, walkable=True, always_visible=True, item=item_comp)

def spear(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='weapon', max_parries_bonus=1)
	return Object(xpos, ypos, '|', 'spear', libtcod.purple, walkable=True, always_visible=True, item=item_comp)

def peasant_tool(xpos, ypos):
	tool_names = ['scythe', 'shovel', 'sickle', 'hatchet', 'hammer', 'rake']
	item_comp = Item(use_function=no_use, equippable=True, slot='weapon')
	return Object(xpos, ypos, 'x', random.choice(tool_names), libtcod.fuchsia, walkable=True, always_visible=True, item=item_comp)

def javelin(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='missile')
	return Object(xpos, ypos, '!', 'javelin', libtcod.light_red, walkable=True, always_visible=True, item=item_comp)

def magic_amulet(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='necklace', max_wounds_bonus=1)
	return Object(xpos, ypos, 'q', 'amulet', libtcod.light_violet, walkable=True, always_visible=True, item=item_comp)

def leather_armor(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='armor', armor_bonus=1)
	return Object(xpos, ypos, '&', 'leather armor', libtcod.light_sepia, walkable=True, always_visible=True, item=item_comp)

def shield(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='offhand', max_parries_bonus=2)
	return Object(xpos, ypos, ']', 'shield', libtcod.blue, walkable=True, always_visible=True, item=item_comp)

def running_shoes(xpos, ypos):
	item_comp = Item(use_function=no_use, equippable=True, slot='feet', max_runs_bonus=1)
	return Object(xpos, ypos, '"', 'running shoes', libtcod.yellow, walkable=True, always_visible=True, item=item_comp)

def random_item(xpos, ypos):
	which = roll(0,6)

	if which == 0:
		return sword(xpos, ypos)
	if which == 1:
		return axe(xpos, ypos)
	if which == 2:
		return spear(xpos, ypos)
	if which == 3:
		return javelin(xpos, ypos)
	if which == 4:
		return leather_armor(xpos, ypos)
	if which == 5:
		return shield(xpos, ypos)
	if which == 6:
		return running_shoes(xpos, ypos)

class Tile:
	# will build grass by default

	def __init__(self, terrain='grass'):
		self.type = terrain
		(self.walkable, self.transparent, self.stealth, self.hiding_spot, self.back, self.fore, self.char) = terrain_tile(terrain)
		self.explored = False

	def change_type(self, terrain):
		self.type = terrain
		(self.walkable, self.transparent, self.stealth, self.hiding_spot, self.back, self.fore, self.char) = terrain_tile(terrain)

def terrain_tile(terrain):
	if terrain == 'grass':
		return (True, True, False, False, libtcod.green, libtcod.green, '.')
	if terrain == 'stone':
		return (True, True, False, False, libtcod.gray, libtcod.gray, '.')
	if terrain == 'stone wall':
		return (False, False, True, False, libtcod.darker_gray, libtcod.darker_gray, '#')
	if terrain == 'village wall':
		return (False, False, True, False, libtcod.green, libtcod.sepia, '#')
	if terrain == 'mud':
		return (True, True, False, False, libtcod.sepia, libtcod.sepia, '.')
	if terrain == 'tree':
		return (False, False, True, False, libtcod.green, libtcod.dark_green, 'T')
	if terrain == 'sand':
		return (True, True, False, False, libtcod.light_amber, libtcod.light_amber, '.')
	if terrain == 'shallow water':
		return (True, True, False, True, libtcod.light_blue, libtcod.lighter_blue, '~')
	if terrain == 'water':
		return (False, True, False, True, libtcod.darker_blue, libtcod.dark_blue, '~')
	if terrain == 'crops':
		return (True, True, False, True, libtcod.sepia, libtcod.amber, 'w')
	if terrain == 'fence':
		return (False, True, True, False, libtcod.green, libtcod.dark_sepia, '#')
	if terrain == 'low stone wall':
		return (False, True, True, False, libtcod.green, libtcod.light_gray, '#')
	if terrain == 'wood wall':
		return (False, False, True, False, libtcod.dark_sepia, libtcod.dark_sepia, '#')
	if terrain == 'weak hinges':
		# the name here is a cludge to make things look nice. This is the tile for a door to sit on.
		return (True, False, True, False, libtcod.dark_sepia, libtcod.dark_sepia, ' ')
	if terrain == 'wood floor':
		return (True, True, False, False, libtcod.light_sepia, libtcod.light_sepia, '.')
	if terrain == 'window':
		return (False, True, True, False, libtcod.light_blue, libtcod.light_blue, '#')
	if terrain == 'broken window':
		return (False, True, True, False, libtcod.light_blue, libtcod.light_blue, ',')
	if terrain == 'dirt road':
		return (True, True, False, False, libtcod.dark_sepia, libtcod.dark_sepia, '.')
	if terrain == 'cobble road':
		return (True, True, False, False, libtcod.gray, libtcod.gray, '.')
	if terrain == 'gravestone':
		return (False, True, True, False, libtcod.green, libtcod.gray, 149)
	if terrain == 'fresh grave':
		return (True, True, False, False, libtcod.dark_green, libtcod.sepia, 'o')
	if terrain == 'old grave':
		return (True, True, False, False, libtcod.dark_green, libtcod.dark_green, 'o')
	if terrain == 'open grave':
		return (True, True, False, True, libtcod.dark_green, libtcod.dark_violet, 'o')

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

def make_village_map():
	global cur_map, objects, cur_map_height, cur_map_width, board

	# stairs
	# a village map - a set of tiles, all enclosed by a wall.

	cur_map_height = VILLAGE_TILES_HIGH * VILLAGE_TILE_SIZE
	cur_map_width = VILLAGE_TILES_WIDE * VILLAGE_TILE_SIZE

	board = libtcod.console_new(cur_map_width, cur_map_height)

	libtcod.console_set_default_background(board, libtcod.darkest_blue)
	libtcod.console_set_default_foreground(board, libtcod.yellow)

	objects = [player]

	# split the area into an X x Y grid of NxN village tile areas

	cur_map = [[Tile('grass')
		for y in range(cur_map_height) ]
			for x in range(cur_map_width) ]

	#build_double_wall(0, 0, cur_map_width, cur_map_height, 'village wall')

	# staggered_path(1, 1, 100, 100, 'dirt road')

	top_left_corners = []

	# before shuffling, top left corners reads from left to right, and then from up to down.

	for y in range(VILLAGE_TILES_HIGH):
		for x in range(VILLAGE_TILES_WIDE):
			top_left_corners.append((x*VILLAGE_TILE_SIZE, y*VILLAGE_TILE_SIZE))

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

	#walled_x = roll(1, VILLAGE_TILES_WIDE - 3)
	#walled_y = roll(1, VILLAGE_TILES_HIGH - 3)

	#top_left_corners = []

	#walled_tiles = [(walled_x, walled_y), (walled_x+1, walled_y+1), (walled_x+1, walled_y), (walled_x, walled_y+1)]

	#for y in range(VILLAGE_TILES_HIGH):
	#	for x in range(VILLAGE_TILES_WIDE):
	#		if walled_tiles.count((x, y)) == 0:
	#			top_left_corners.append((x*VILLAGE_TILE_SIZE, y*VILLAGE_TILE_SIZE))

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

	
		# go here for CHEATS. remove # signs.
	#objects.append(sword(x_off+2, y_off+1))
	#objects.append(shield(x_off+1, y_off+2))
	#objects.append(leather_armor(x_off+2, y_off+2))
	#objects.append(javelin(x_off+3, y_off+3))

	# refactor: tile_types = village_tiles(VILLAGE_TILES_HIGH*VILLAGE_TILES_WIDE)
	tile_types = []

	tot_tiles = VILLAGE_TILES_WIDE * VILLAGE_TILES_HIGH - 1

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

	tile_types.append(6)

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
		elif choice == 6:
			place_wizard_tower(tile[0], tile[1], VILLAGE_TILE_SIZE)

	#place_walled_village(walled_x*VILLAGE_TILE_SIZE, walled_y*VILLAGE_TILE_SIZE)

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
		num_hunters = roll(1,2)

		while num_hunters > 0:
			hunt_x = roll(xpos, xpos + tile_size - 1)
			hunt_y = roll(ypos, ypos + tile_size - 1)

			if is_walkable(hunt_x, hunt_y):
				objects.append(hunter(hunt_x, hunt_y))
				num_hunters -= 1
				dog_spots = []
				for x in range(hunt_x-1, hunt_x+2):
					for y in range(hunt_y-1, hunt_y+2):
						if (in_range(x, y) and is_walkable(x, y)):
							dog_spots.append((x, y)) 
				if len(dog_spots) > 0:
					(dog_x, dog_y) = random.choice(dog_spots)
					objects.append(dog(dog_x, dog_y))

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

	x_item = roll(cottage_start_x + 1, cottage_start_x + cottage_w - 2)
	y_item = roll(cottage_start_y + 1, cottage_start_y + cottage_h - 2)

	objects.append(random_item(x_item, y_item))

	occupants = roll(1,3)
	while occupants > 0:
		xpos = roll(cottage_start_x + 1, cottage_start_x + cottage_w - 2)
		ypos = roll(cottage_start_y + 1, cottage_start_y + cottage_h - 2)
		if is_walkable(xpos, ypos):
			which = roll(0,4)
			if which == 0:
				mons = farmer(xpos, ypos)
				mons.ai = SleepingPackAI()
				mons.ai.owner = mons
				objects.append(mons)
			elif which == 1:
				mons = hunter(xpos, ypos)
				mons.ai = SleepingLonerAI()
				mons.ai.owner = mons
				objects.append(mons)
			elif which == 2:
				mons = lumber_worker(xpos, ypos)
				mons.ai = SleepingPackAI()
				mons.ai.owner = mons
				objects.append(mons)
			elif which == 3:
				mons = fisherman(xpos, ypos)
				mons.ai = SleepingPackAI()
				mons.ai.owner = mons
				objects.append(mons)
			elif which == 4:
				mons = guard(xpos, ypos)
				mons.ai = SleepingLonerAI()
				mons.ai.owner = mons
				objects.append(mons)
			occupants -= 1

	num_dogs = roll(1,3)

	while num_dogs > 0:
		xpos = roll(cottage_start_x + 1, cottage_start_x + cottage_w - 2)
		ypos = roll(cottage_start_y + 1, cottage_start_y + cottage_h - 2)
		if is_walkable(xpos, ypos):
			a_dog = dog(xpos, ypos)
			a_dog.ai = SleepingDogAI()
			a_dog.ai.owner = a_dog
			objects.append(a_dog)
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
					if chance(1,15):
						cur_map[x][y+1].change_type('fresh grave')
					else:
						cur_map[x][y+1].change_type('old grave')

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

def place_wizard_tower(xpos, ypos, tile_size):
	center_x = xpos + tile_size / 2 - 1
	center_y = ypos + tile_size / 2 - 1

	radial_tile_paint(8, center_x, center_y, 'stone wall')
	radial_tile_paint(6, center_x, center_y, 'stone')
	radial_tile_paint(4, center_x, center_y, 'stone wall')
	radial_tile_paint(2, center_x, center_y, 'stone')

	rectangle_tile_fill(center_x-8, center_y, 17, 1, 'stone')
	rectangle_tile_fill(center_x, center_y-8, 1, 17, 'stone')

	objects.append(mad_mage(center_x, center_y))

def place_walled_village(xpos, ypos):
	global cur_map, objects

	rectangle_tile_fill(xpos, ypos, 40, 40, 'grass')
	build_double_wall(xpos-1, ypos-1, 42, 42, 'village wall')

	rectangle_tile_fill(xpos+19, ypos-1, 2, 42, 'cobble road')
	rectangle_tile_fill(xpos-1, ypos+19, 42, 2, 'cobble road')
	rectangle_tile_fill(xpos+18, ypos+18, 4, 4, 'cobble road')
	rectangle_tile_fill(xpos+19, ypos+19, 2, 2, 'shallow water')

	objects.append(village_guard(xpos+19, ypos, xpos, ypos, 0))
	objects.append(village_guard(xpos+21, ypos+20, xpos, ypos, 3))
	objects.append(village_guard(xpos, ypos+20, xpos, ypos, 6))

	# north

def radial_tile_paint(radius, xpos, ypos, terrain):
	# This only respects the boundaries of the current map, not your current terrain.

	global cur_map

	xmin = max(0, xpos - radius)
	xmax = min(xpos + radius, cur_map_width)

	ymin = max(0, ypos - radius)
	ymax = min(ypos + radius, cur_map_height)

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

	cur_x = start_x
	cur_y = start_y

	cur_map[cur_x][cur_y].change_type(terrain)

	xmag = abs(end_x - start_x)
	ymag = abs(end_y - start_y)

	if ymag == 0:
		for x in range(cur_x, end_x):
			cur_map[x][end_y].change_type(terrain)
		return None

	if xmag == 0:
		for y in range(cur_y, end_y):
			cur_map[end_x][y].change_type(terrain)
		return None

	xsign = (end_x - start_x)/abs(end_x - start_x)
	ysign = (end_y - start_y)/abs(end_y - start_y)

	while cur_x is not end_x and cur_y is not end_y:
		if chance(xmag, xmag+ymag):
			xmag = xmag - 1
			cur_x = cur_x + xsign
			cur_map[cur_x][cur_y].change_type(terrain)
		else:
			ymag = ymag - 1
			cur_y = cur_y  + ysign
			cur_map[cur_x][cur_y].change_type(terrain)

	if cur_x is not end_x:
		for x in range(cur_x, end_x):
			cur_map[x][end_y].change_type(terrain)
	elif cur_y is not end_y:
		for y in range(cur_y, end_y):
			cur_map[end_x][y].change_type(terrain)

def initialize_fov():
	global fov_recompute, fov_map, enemy_fov_map, stealth_fov_map
	fov_recompute = True



	fov_map = libtcod.map_new(cur_map_width, cur_map_height)
	enemy_fov_map = libtcod.map_new(cur_map_width, cur_map_height)
	stealth_fov_map = libtcod.map_new(cur_map_width, cur_map_height)

	for y in range(cur_map_height):
		for x in range(cur_map_width):
			libtcod.map_set_properties(fov_map, x, y, cur_map[x][y].transparent, cur_map[x][y].walkable)

	for y in range(cur_map_height):
		for x in range(cur_map_width):
			libtcod.map_set_properties(enemy_fov_map, x, y, cur_map[x][y].transparent, cur_map[x][y].walkable)

	for y in range(cur_map_height):
		for x in range(cur_map_width):
			libtcod.map_set_properties(stealth_fov_map, x, y, not cur_map[x][y].stealth, cur_map[x][y].walkable)

	libtcod.console_clear(0)

def move_camera(target_x, target_y):
	global camera_x, camera_y, fov_recompute

	x = target_x - CAMERA_WIDTH / 2
	y = target_y - CAMERA_HEIGHT / 2

	if x < 0: x = 0
	if y < 0: y = 0
	if x > cur_map_width - CAMERA_WIDTH: x = cur_map_width - CAMERA_WIDTH
	if y > cur_map_height - CAMERA_HEIGHT: y = cur_map_height - CAMERA_HEIGHT

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
			names += ' '
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

def parries_info(obj):
	if obj.fighter is None:
		return ''

	if obj.get_equipped_in_slot('weapon') is None:
		return "NO WEAPON"

	max_p = obj.fighter.max_parries
	rem_p = obj.fighter.parries_left

	parries = 'PARRIES: '

	if max_p == 0:
		return parries + 'UNSKILLED'

	parries += ' X' * rem_p
	if obj.fighter.rested:
		parries += ' /' + ' -' * (max_p - rem_p - 1)
	else:
		parries += ' -' * (max_p - rem_p)

	return parries

def wounds_info(obj):
	if obj.fighter is None:
		return ''

	max_w = obj.fighter.max_wounds
	rem_w = obj.fighter.wounds
	wound = 'WOUNDS:' + ' *' * rem_w + ' -' * (max_w -rem_w)

	return wound

def runs_info(obj):
	if obj.fighter is None or obj.mind is None:
		return ''
	if obj.mind.skills[8] == 0:
		return ''
	run = 'RUNS: %i/%i' % (obj.fighter.runs, obj.fighter.max_runs)
	return run

def render_all_night():
	global fov_map
	global enemy_fov_map
	global stealth_fov_map
	global fov_recompute
	global camera_x, camera_y

	move_camera(player.x, player.y)

	if fov_recompute:

		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS+player.mind.skills[6]*3, True, FOV_ALGO)
		libtcod.map_compute_fov(enemy_fov_map, player.x, player.y, ENEMY_SIGHT, True, FOV_ALGO)
		libtcod.map_compute_fov(stealth_fov_map, player.x, player.y, TORCH_RADIUS*player.mind.skills[6]*3, True, FOV_ALGO)
		libtcod.console_clear(board)

		for y in range(CAMERA_HEIGHT):
			for x in range(CAMERA_WIDTH):
				(map_x, map_y) = (camera_x + x, camera_y + y)
				visible = libtcod.map_is_in_fov(fov_map, map_x, map_y)

				wall = not cur_map[map_x][map_y].transparent

				if visible:
					tile = cur_map[map_x][map_y]
					libtcod.console_put_char_ex(board, map_x, map_y, tile.char, tile.fore, libtcod.darkest_blue)
					if player.mind.skills[0]:
						cur_map[map_x][map_y].explored = True
				elif cur_map[map_x][map_y].explored:
					# explored tile logic
					tile = cur_map[map_x][map_y]
					libtcod.console_put_char_ex(board, map_x, map_y, tile.char, tile.fore * 0.5, libtcod.darkest_blue)


	for obj in objects:
		if obj is not player:
			obj.draw()

	player.draw()

	libtcod.console_blit(board, camera_x, camera_y, CAMERA_WIDTH, CAMERA_HEIGHT, 0, 0, 0)

	libtcod.console_clear(panel)

	# create the player info panel

	libtcod.console_set_default_foreground(panel, libtcod.light_gray)
	libtcod.console_print(panel, PLAYER_INFO_X, PLAYER_INFO_Y, parries_info(player))

	libtcod.console_set_default_foreground(panel, libtcod.light_red)
	libtcod.console_print(panel, PLAYER_INFO_X, PLAYER_INFO_Y + 1, wounds_info(player))

	# create the enemy info panel
	if target is not None and target.fighter is not None:

		libtcod.console_set_default_foreground(panel, libtcod.yellow)
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y, 'TARGET: ' + target.name.capitalize())

		libtcod.console_set_default_foreground(panel, libtcod.light_gray)
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y + 1, parries_info(target))

		libtcod.console_set_default_foreground(panel, libtcod.light_red)
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y + 2, wounds_info(target))

	else:
		libtcod.console_print(panel, ENEMY_INFO_X, ENEMY_INFO_Y, 'No current target.')

	libtcod.console_set_default_foreground(panel, libtcod.yellow)
	libtcod.console_print_ex(panel, PANEL_WIDTH-1, 0, libtcod.BKGND_DEFAULT, libtcod.RIGHT, get_names_under_mouse())

	libtcod.console_print(panel, PLAYER_INFO_X, PLAYER_INFO_Y - 1, runs_info(player))

	# create the log panel
	y = 0
	for (line, color) in game_log[-1*LOG_HEIGHT-lookback:]:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print(panel, LOG_X, LOG_Y + y, line)
		y += 1
		if y == 6:
			break

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
		elif key.vk == libtcod.KEY_ENTER or key.vk == libtcod.KEY_SPACE or key.vk == libtcod.KEY_KPENTER:

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
	options.append(['Skills', '', 0],)
	options.append(['Controls', '', 1])
	if game_state == 'playing':
		#when saving and loading is reliable, add them back in here.
		options.append(['Quit', '', 2])
	elif game_state == 'dead':
		options.append(['Quit', '', 3])
	options.append(['Main Menu', '', 4])

	choice = triple_menu('***PAUSED***', options)

	if choice == 0:
		skills_menu()
	elif choice == 1:
		controls_screen()
	elif choice == 2 or choice == 3:
		return 'exit'
	elif choice == 4:
		main_menu()

def skills_menu():
	options = []

	for inx, skill in enumerate(player.mind.skills):
		if skill > 0:
			options.append( [num_to_faculty_name(inx, skill), num_to_faculty_description(inx, skill), inx] )
	if len(options) == 0:
		options.append( ['You have no skills currently.', 'Eat minds to gain skills! Kill creatures to eat their minds.', 0])
	triple_menu('SKILLS', options)

	return None

def controls_screen():
	options = []

	options.append('Num Pad - Move')
	options.append('Space - Rest (recover parries)')
	options.append('e - Eat minds')
	options.append('g - Get item')
	options.append('f - Perform first aid *')
	options.append('r - Run (parries -> free moves) *')
	options.append('d - Dig for \'loot\' *')
	options.append('t - Throw missile weapon *')
	options.append('Escape - Menu')
	options.append('[ - Older messages')
	options.append('] - More recent messages')
	options.append('Arrow Keys - Move')
	options.append('vi Keys - Move')
	single_screen('CONTROLS (* = skill required)', options)
	return None

def end_game_menu():
	options = []
	options.append(['Yes, end the game.', 'You will receive a score based on your accomplishments.', 0])
	options.append(['No, I\'m still working on it!', 'Eat better minds or find more equipment to increase your score.', 1])

	choice = triple_menu('End of map! Leave this region?', options)

	if choice == 1:
		return
	else:
		mind_score = sum(player.mind.skills)
		equipment_score = len(player.inventory)
		wounds_score = player.fighter.wounds
		total_score = mind_score + equipment_score + wounds_score

		options = []

		options.append('Mind Score: %i' %mind_score)
		options.append('Item Score: %i' %equipment_score)
		options.append('Wounds Remaining: %i' %wounds_score)
		options.append('***TOTAL SCORE***')
		options.append('%i'%total_score)
		if total_score < 5:
			options.append('Survival is sweeter than death, but not by much.')
		elif total_score < 12:
			options.append('Your noble efforts are their own reward.')
		elif total_score < 20:
			options.append('Success and victory are yours!')
		else:
			options.append('A true MIND EATER!')

		single_screen('Congratulations! You survived!', options)

		main_menu()

def handle_keys():
	global key, lookback

	if key.vk == libtcod.KEY_ESCAPE:
		return escape_menu()

	if game_state == 'playing':
		key_char = chr(key.c)

		if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8 or key_char == 'k':
			return player_move_or_attack(0,-1)
		elif key.vk == libtcod.KEY_KP9 or key_char == 'u':
			return player_move_or_attack(1,-1)
		elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6 or key_char == 'l':
			return player_move_or_attack(1,0)
		elif key.vk == libtcod.KEY_KP3 or key_char == 'n':
			return player_move_or_attack(1,1)
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2 or key_char == 'j':
			return player_move_or_attack(0,1)
		elif key.vk == libtcod.KEY_KP1 or key_char == 'b':
			return player_move_or_attack(-1,1)
		elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4 or key_char == 'h':
			return player_move_or_attack(-1,0)
		elif key.vk == libtcod.KEY_KP7 or key_char == 'y':
			return player_move_or_attack(-1,-1)
		elif key.vk == libtcod.KEY_KP5 or key.vk == libtcod.KEY_SPACE:
			return player_pause()

		if key_char == 'e':
			return player_eat_mind()
		elif key_char == 'g':
			for obj in objects:
				if obj.x == player.x and obj.y == player.y and obj.item:
					obj.item.equip(player)
					return 'took-turn'
		#elif key_char == 'i':
		#	for thing in player.inventory:
		#		print(thing.name)
		#		print(thing.item.equipped)
		#	return 'no-turn'
		elif key_char == 'f':
			return player.fighter.first_aid()
		elif key_char == 'r' and player.mind.skills[8] > 0:
			return player.fighter.run_prep()
		elif key_char == 'd' and player.mind.skills[9] > 0:
			return player_dig(player.x, player.y)
		elif key_char == 't' and player.mind.skills[12] > 0:
			return player_chuck_javelin()
		elif key_char == 'x' and player.mind.skills[13] > 0:
			return player_inferno()
		#elif key_char == 'D':
		#	while len(player.inventory) > 0:
		#		player.inventory[0].item.drop(player)
		#elif key_char == 'w':
		#	for thing in player.inventory:
		#		thing.item.toggle_equip(player)
		elif key_char == '[':
			lookback += 5
		elif key_char == ']':
			lookback = max(0, lookback - 5)
	elif game_state == 'dead':
		key_char = chr(key.c)

		if key_char == '[':
			lookback += 5
			render_all_night()
		elif key_char == ']':
			lookback = max(0, lookback - 5)
			render_all_night()


	return 'no-turn'

def player_move_or_attack(dx, dy):
	global target

	x = player.x + dx
	y = player.y + dy

	if not in_range(x, y):
		end_game_menu()

	# try to find a target to attack
	targeted = None
	targeted_door = None
	for obj in objects:
		if obj.fighter and x is obj.x and y is obj.y:
			if obj.name == 'door' or obj.name == 'gate':
				targeted_door = obj
			else:
				targeted = obj
				break

	if targeted is None and targeted_door is not None:
		targeted = targeted_door

	if targeted is not None:
		player.fighter.attack(targeted)
		target = targeted
		return 'took-turn'
	elif player.move(dx, dy):
		if player.fighter.runs > 0:
			player.fighter.runs -= 1
			return 'ran'
		return 'took-turn'
	else:
		return 'no-turn'

def player_dig(x, y):
	global fov_recompute

	if cur_map[x][y].type != 'fresh grave':
		log("You dig half-heartedly, but you know there's nothing here...", libtcod.red)
		return 'took-turn'
	elif chance(1,5):
		corpse = great_corpse(x, y)
		objects.append(corpse)
		corpse.send_to_back()
		log("You dig eagerly, and unearth a great treasure!", libtcod.green)
	else:
		corpse = fine_corpse(x, y)
		objects.append(corpse)
		corpse.send_to_back()
		log("You dig hungrily, and unearth a treasure!", libtcod.green)
	cur_map[player.x][player.y].change_type('open grave')
	fov_recompute = True

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
		log('No minds here to be eaten!', libtcod.red)
		return 'no-turn'

	eaten_mind = triple_menu('Which mind to consume?', available_minds)

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

	log('You devour the mind...', libtcod.red)
	log('You know %s!' %num_to_faculty_name(choice, player.mind.skills[choice]), libtcod.blue)

	return 'took-turn'

def player_chuck_javelin():

	missile = player.get_equipped_in_slot('missile')
	if missile is None:
		log('Need a javelin to throw one!', libtcod.red)
		return 'no-turn'

	min_dist = sqrt(cur_map_width ** 2 + cur_map_height **2) + 10
	pin_cushion = None
	for obj in objects:
		if obj is not player and obj.fighter is not None and obj.name != 'gate' and obj.name != 'door' and libtcod.map_is_in_fov(fov_map, obj.x, obj.y) and player.distance_to(obj) < min_dist:
			pin_cushion = obj
			min_dist = player.distance_to(obj)

	if pin_cushion is None:
		log('No target close enough for you!', libtcod.red)
		return 'no-turn'
	if player.distance_to(pin_cushion) < 6:
		player.inventory.remove(missile.owner)
		log('You threw a javelin! BRUTAL!', libtcod.red)
		pin_cushion.fighter.take_damage(2, unblockable=True)
		return 'took-turn'
	else:
		log('No target close enough for you!', libtcod.red)
		return 'no-turn'

def player_inferno():
	global cooldown

	if cooldown > 0:
		cooldown -= 1
		if cooldown > 0:
			log("You build your power... only %i more times to go..."%cooldown, libtcod.fuchsia)
		else:
			log("THE INFERNO IS READY", libtcod.magenta)
		return 'took-turn'

	cooldown = 7
	log('Finally it is ready! You unleash HELLFIRE!', libtcod.fuchsia)

	for obj in objects:
		if obj is not player and obj.fighter is not None and player.distance_to(obj) < 16:
			log('Under your withering flames, the %s burns!'%obj.name, libtcod.red)
			obj.fighter.take_damage(7, unblockable=True)

	return 'took-turn'

def num_to_faculty_name(ind, magnitude=1):
	if ind == 0:
		return 'Mapping'
	if ind == 1:
		return 'Parry %i' % magnitude
	if ind == 2:
		return 'Weapon Use'
	if ind == 3:
		return 'Armor Use'
	if ind == 4:
		return 'First Aid %i' % magnitude
	if ind == 5:
		return 'Stealth %i' % magnitude
	if ind == 6:
		return 'Vision %i' % magnitude
	if ind == 7:
		return 'Open Doors'
	if ind == 8:
		return 'Running %i' % magnitude
	if ind == 9:
		return 'Digging'
	if ind == 10:
		return 'Swimming'
	if ind == 11:
		return 'Vaulting'
	if ind == 12:
		return 'Throwing'
	if ind == 13:
		return 'Infernal Spell'

def num_to_faculty_description(ind, magnitude=1):
	if ind == 0:
		return 'With this, you can remember what terrain you\'ve seen.'
	if ind == 1:
		return 'Each parry lets you block one more attack. Stand still to regain parries slowly.'
	if ind == 2:
		return 'You can use weapons. Weapons are essential to proper parrying, and some do more damage than your limbs.'
	if ind == 3:
		return 'You can now wear armor, just like the filth you hunt. It reduces the damage from each landed blow.'
	if ind == 4:
		return 'This much knowledge of first aid lets you regain a wound if you have %i or fewer left. Not for combat use!' %magnitude
	if ind == 5:
		return 'You can duck down to hide behind or in low obstructions.'
	if ind == 6:
		return 'You can see further and clearer than before.'
	if ind == 7:
		return 'You can open doors without making a racket.'
	if ind == 8:
		return 'You can run at the cost of your defenses. Press r to convert parries into extra spaces of movement.'
	if ind == 9:
		return 'You can go to where the bodies are buried...'
	if ind == 10:
		return 'You can cross over deep water.'
	if ind == 11:
		return 'With a bound, you can now vault over low obstacles.'
	if ind == 12:
		return 'You can jack a javelin straight into some dude\'s chest.'
	if ind == 13:
		return 'Press x repeatedly to build magical power, and then again to unleash it, witheringly!'

def make_faculty_list(mapping=0, parry=0, weapon=0, armor=0, first_aid=0, stealth=0, 
	search=0, doors=0, run=0, dig=0, swim=0, vault=0, throw=0, magic=0):

	return [mapping, parry, weapon, armor, first_aid, stealth, search, doors, run, dig, swim, vault, throw, magic]

def mindeating_menu(eaten_mind):
	options = []

	for i in range(len(player.mind.skills)):
		if eaten_mind.skills[i] > player.mind.skills[i]:

			options.append( [num_to_faculty_name(i, player.mind.skills[i] + 1), num_to_faculty_description(i, player.mind.skills[i] + 1), i] )

	if len(options) == 0:
		eaten_mind.owner.name += ', mindless'
		eaten_mind.owner.mind = None
		log('This mind had nothing new in it! Disgusting!', libtcod.red)
		return -1

	choice = triple_menu('MMM! What to gain from this mind?', options)

	if choice == 'no-choice':
		log('You resist the urge to eat this mind...', libtcod.blue)
		return -1

	eaten_mind.owner.name += ', mindless'
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
	if 0 <= x < cur_map_width and 0 <= y < cur_map_height:
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

libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'THE MIND EATER')

libtcod.sys_set_fps(LIMIT_FPS)
libtcod.console_set_keyboard_repeat(200, 1000/LIMIT_FPS)

initialize_ascii_maps()

panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

libtcod.console_set_default_background(panel, libtcod.darkest_blue)

menu = libtcod.console_new(MENU_WIDTH, MENU_MAX_HEIGHT)

libtcod.console_set_default_background(menu, libtcod.darkest_blue)
libtcod.console_set_default_foreground(menu, libtcod.white)

main_menu()