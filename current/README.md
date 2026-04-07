# csp_backtracking

I will code up my backtracking implementation here



# extract from case records
# add case history to barrister profiles, calculate new winrate
# no ethic committee for now
# progress report
# example input files from court/barrister chambers
# evaluation techniques
# consider graphs, e.g. running scaling inputs to evaluate how runtime/mem scales for each algo
# look at other papers - calendar matching problems, other algos/evaluation techniques

Barrister info pages
https://www.directaccessportal.co.uk/search-barristers.html


# evaluation metrics
# basic greedy algorithm
# generate test data
# add case history to barrister profiles
# research papers with similar problem - what algorithms, what evaluation ### 1


# Hungarian Method (Kuhn, 1955)


# unit tests (test each function)
# validation tests (expected schedules)
# evaluation tests (for evaluation phase: generate tests to compare models)
# implement a naive backtracking
# genetic algorithm?

# computational complexity of algorithms, compare results (or expected results)
# explain field, why is this a problem
# manual scheduling solved with computers
# optimization problem
# group functions, e.g. processing / outputting functions
# mention test data and relevance, compare to real court data (fixed times)




# find existing scheduling tools - results into a text to show steve
# focus on evaluation - show graphs
# implement 1 more algo if time
# create latex document with section headings, basic structure - (look on course webpage)
# overleaf
# create a visual example with UI, useful for including on the diss
# discuss interesting scenarios with specific constraints


# Existing tools research
# Bar specific: tools exist for making clerking workflows more efficient and allowing diary, case management and billing all in a single integrated environment. However these are more-so diary management tools, intended to be used by clerks to speedup their workflow and have everything in a single service - there is no explicit optimisation engine, actual case assignments are still done by clerks. - BarBooks for Chambers, Barrister 365

# More general optimisation tools exist, mainly intended for field service scheduling / routing. Mainly used for optimising schedules of service jobs at different job sites and assigning workers, or used for optimising routing of deliveries and fleets. These tools could be configured to work with a specific field such as barrister scheduling but would take some work and could have potential support issues for some features. - Timefold Field Service Routing, Dynamics 365 Resource Scheduling Optimization


# start writing Preperation section as collecting evaluation results (50/50 split)
# different scenarios: how do the algorithms scale, experiment with different time-limits
# show to barrister chambers, get (anonymous) feedback
# other constraints? - future work 
# describe flow of information in system, inputs, outputs
# show information to barrister chambers to evaluate whether it would get value in real scenario

# case A (A: 30, B: 50), case B (A: 50, B: 100)