# v1.2

import pandas as pd
import json
import sys

if len(sys.argv) < 3:
	print("[!] Usage: ./"+sys.argv[0]+' results.csv events.csv [click_canary]\n')
	print("    click_canary\tParameter string to filter false clicks from results if using an invisible URL.\n")
	sys.exit()

results_f = sys.argv[1]
events_f = sys.argv[2]
canary = sys.argv[3] if len(sys.argv) >= 4 else False

results = pd.read_csv(results_f)
events = pd.read_csv(events_f)

data = {}  # {email{email,first_name,last_name,position,sent,opens,clicks,submits}}
positions = {}  # {position{sent,opens,clicks,submits}}

total = {"sent":0,"opens":0,"clicks":0,"submits":0}

fake_input = []

# Get user information from results
def get_metadata():
	for idx,row in results.iterrows():
		email = row["email"]
		meta = {}
		meta["email"] = row["email"]
		meta["first name"] = row["first_name"]
		meta["last name"] = row["last_name"]
		meta["position"] = row["position"]

		meta["sent"] = meta["opens"] = meta["clicks"] = meta["submits"] = 0
		data[email] = meta

get_metadata()

# Get data from events
def get_events():
	for idx,row in events.iterrows():
		if row["email"] == "":
			continue
		email = row["email"]
		if row["message"] == "Email Sent":
			data[email]["sent"] += 1
		if row["message"] == "Email Opened":
			data[email]["opens"] += 1
		elif row["message"] == "Clicked Link":
			if canary != False and canary in row["details"]:  # check false positive canary
				data[email]["clicks"] -= 1
			else:
				data[email]["clicks"] += 1
		elif row["message"] == "Submitted Data":
			payload = json.loads(row["details"])
			username = payload["payload"]["username"][0]
			username = "NULL" if len(username) == 0 else username
			if username != email:
				fake_input.append({"email":email,"username":username})
			data[email]["submits"] += 1

get_events()

# Check potential fake inputs
def check_fakes():
	if len(fake_input) != 0:
		print("[!] Check for fake false positives. The following submitted data is not he same as the user email:")
		print("  EMAIL\t\t\t\t\t  INPUT")
		for i in fake_input:
			print(i["email"] + " " * (40-len(i["email"])) + i["username"])
		print()

		filename = "fake_input.json"
		with open(filename, 'w') as f:
		    json.dump(fake_input, f)
		print("[+] Created '"+filename+"'")

check_fakes()

# Update total values and by position for each action
def update_totals():
	for key,val in enumerate(data):
		pos = data[val]["position"]
		if pos not in positions:
			positions[pos] = {"sent":0,"opens":0,"clicks":0,"submits":0}

		actions = ["sent","opens","clicks","submits"]
		for action in actions:
			positions[pos][action] += data[val][action]
			total[action] += data[val][action]

update_totals()
		
# Create users at risk (Risks, Users at Critical risk, Users at High risk)
def get_risk_users(data):

	def risk_csv(risk, action):
		risk = {}
		for key,val in enumerate(data):
			if data[val][action] > 0:
				risk[val] = {}
				risk[val]["email"] = data[val]["email"]
				risk[val]["position"] = data[val]["position"]
				risk[val][action] = data[val][action]

		risk = pd.DataFrame.from_dict(risk, orient='index')
		return(risk)

	critical = high = {}
	critical = risk_csv(critical, "submits")
	critical.columns = [x.capitalize() for x in critical.columns]
	high = risk_csv(high, "clicks")
	high.columns = [x.capitalize() for x in high.columns]

	all_users = data
	for val in all_users.values():
		val["clicks"] = 0 if val["clicks"] < 0 else val["clicks"]  # fix negative clicks
		del val["sent"]

	all_users = pd.DataFrame.from_dict(all_users, orient='index')
	all_users.columns = [x.capitalize() for x in all_users.columns]

	filename = "users_at_risk.xlsx"
	with pd.ExcelWriter(filename, engine="openpyxl") as writer:
		critical.to_excel(writer, sheet_name="Users at Critical Risk", index=False)
		high.to_excel(writer, sheet_name="Users at High Risk", index=False)
		all_users.to_excel(writer, sheet_name="Total Results", index=False)
	print("[+] Created '"+filename+"'")

get_risk_users(data)

# Calculate global % and by position
def get_percentages(dictionary):
	p_clicks = dictionary["clicks"] * 100 / dictionary["sent"]
	p_clicks = round(p_clicks, 1) if p_clicks > 0 else 0
	p_submits = dictionary["submits"] * 100 / dictionary["sent"]
	p_submits = round(p_submits, 1) if p_submits > 0 else 0
	dictionary.update({"click %": str(p_clicks)+'%'})
	dictionary.update({"submit %": str(p_submits)+'%'})
	del dictionary["opens"]  # false positives

# Create results by position % for each action
def write_comparison(total, positions):
	get_percentages(total)  # get global %
	total_f = {"Global":total}
	total = pd.DataFrame.from_dict(total_f, orient='index')
	total.columns = [x.capitalize() for x in total.columns]

	for key,val in enumerate(positions):
		get_percentages(positions[val])  # get % by position
	positions = pd.DataFrame.from_dict(positions, orient='index')
	positions = positions.reset_index().rename(columns={'index':'Position'})
	positions.columns = [x.capitalize() for x in positions.columns]

	filename = "position_results.xlsx"
	with pd.ExcelWriter(filename, engine="openpyxl") as writer:
		total.to_excel(writer, sheet_name="Global")
		positions.to_excel(writer, sheet_name="Positions", index=False)
	print("[+] Created '"+filename+"'")

write_comparison(total, positions)
