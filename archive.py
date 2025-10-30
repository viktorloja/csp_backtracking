'''def AC3(csp):
    domains = csp.domains
    queue = []
    while queue:
        (var1, var2) = queue.pop(0)
        if remove_inconsistencies(domains[var1], domains[var2]):
            if not domains[var1]:
                return False
            for neighbour in neighbours[var1]:
                if neighbour '''