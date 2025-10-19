class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables  # list like ["X", "Y", "Z"]
        self.domains = domains      # dict: {var: [possible_values]}
        self.constraints = constraints  # dict: { (X, Y): constraint_fn }

    def is_consistent(self, var, value, assignment):
        # Check that assigning var=value doesn’t violate any constraints
        for (x, y), constraint in self.constraints.items():
            if x == var and y in assignment:
                if not constraint(value, assignment[y]):
                    return False
            if y == var and x in assignment:
                if not constraint(assignment[x], value):
                    return False
        return True