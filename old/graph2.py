import matplotlib.pyplot as plt

assignments = {
    "CaseA": "Barrister1",
    "CaseB": "Barrister2",
    "CaseC": "Barrister3",
}

# Simple plot
barristers = list(set(assignments.values()))
cases = list(assignments.keys())
positions = range(len(cases))

plt.barh(positions, [1]*len(cases), color="skyblue")
plt.yticks(positions, cases)
for i, case in enumerate(cases):
    plt.text(0.5, i, assignments[case], ha='center', va='center')
plt.xlabel("Assignment slot")
plt.title("Barrister–Case Assignments")
plt.show()