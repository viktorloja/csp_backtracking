variables = ["WA", "NT", "SA", "Q", "NSW", "V", "T"]

# --- Domains ---
colors = ["red", "green", "blue"]
domains = {}
for var in variables:
    domains[var] = colors

# --- Constraints ---
neighbors = [
    ("WA", "NT"), ("WA", "SA"), ("NT", "SA"),
    ("NT", "Q"), ("SA", "Q"), ("SA", "NSW"),
    ("SA", "V"), ("Q", "NSW"), ("NSW", "V")
]

# Each neighboring pair must have different colors:
allowed = {(a, b) for a in colors for b in colors if a != b}
constraints = {}
print(allowed)
for (x, y) in neighbors:
    constraints[(x, y)] = allowed
    constraints[(y, x)] = allowed  # constraints are symmetric

#print(variables)
#print(domains)
#print(constraints)