import random

class Hitman:
	@staticmethod
	def _create_hits(users, weapons, locations):
		hits = []
		weapons = weapons[:]
		locations = locations[:]
		for user in users:
			w = weapons.pop(weapons.index(random.choice(weapons)))
			l = locations.pop(locations.index(random.choice(locations)))
			hits.append((user,w,l))
		return hits
		  
	@staticmethod
	def _assign_hits(players, hits):
		assigned = {}
		players = players[:]	# Shorthand to copy a list
		hits = hits[:]			# This is so we can list.remove() without modifying the list and effecting the function one step up in the call chain
		if not players:			# If for some reason we get a empty players list just return an empty dict
			return assigned		# THIS SHOULD NOT HAPPEN THOUGH
		player = players[0]		
		while True:
			h = random.choice(hits) # Choose a random hit
			if h[0] != player:  # You can't be assigned yourself, so check that
				assigned[player] = h
				hits.remove(h)			# Remove the chosen hit
				players.remove(player)	# and player from their respective lists
				if len(players) > 0:	# If there are any remaining hits/players
					ret = Hitman._assign_hits(players, hits) # Recurse to assign the remaining
					if ret:	# If we were able to assign the remaining hits
						assigned.update(ret)	# Update the assigned dict
						return assigned			# And return it
					else: # If we couldn't assign the rest of the hits, probably because there was only one left and hit.target == player
						hits.append(h)			# Add the player
						players.append(player)	# and the chosen hit back to the list
				else:					# If there are no remaining payers/hits
					return assigned		# return assigned
			elif h[0] == player and len(players) == 1:	# If target == player and its the only one left
				return None

	@staticmethod
	def	create_game(users, weapons, locations):
		hits = Hitman._create_hits(users[:], weapons, locations)
		return Hitman._assign_hits(users[:], hits)
