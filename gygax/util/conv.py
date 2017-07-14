

def make_list(data):
	'''wraps data in a list if it isn't already a list'''
	return data if isinstance(data, (list, tuple)) else [data]