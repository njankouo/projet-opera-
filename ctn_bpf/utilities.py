import datetime

def subperiods_value(per,year):
	details = per.decoup_slip()
	tmp_splits = list()
	tmp_dates = list()
	tmp_values = list()
	if per.m_logic_type == 2:
		a = datetime.datetime(int(year), 1, 1)
		if a.isoweekday() > 1 :
			a -= datetime.timedelta(a.isoweekday())
		for i in range(53):
			tmp = a  + datetime.timedelta(7*i)
			tmp2 = a + datetime.timedelta(6) + datetime.timedelta(7*i) 
			b = tmp.month
			b2 = tmp.day
			c = tmp2.month
			c2 = tmp2.day
			if b < 10:
				b = "0"+str(b)
			if b2 < 10:
				b2 = "0"+str(b2)
			if c < 10:
				c = "0"+str(c)
			if c2 < 10:
				c2 = "0"+str(c2)
			val = str(tmp2.year) + str(c) + str(c2) + str(tmp.year) + str(b) + str(b2)
			tmp_dates.append(val)

	elif per.m_logic_type == 3:
		a = datetime.datetime(int(year), 1, 1)
		if a.isoweekday() > 1 :
			a -= datetime.timedelta(a.isoweekday())
		for i in range(12):
			month = i+1
			if month < 12:
				tmp = datetime.datetime(int(year), month, 1)
				tmp2 = datetime.datetime(int(year), (month+1), 1) - datetime.timedelta(1) 
			else:
				tmp = datetime.datetime(int(year), 12, 1)
				tmp2 = datetime.datetime(int(year)+1, 1, 1) - datetime.timedelta(1)
			b = tmp.month
			b2 = tmp.day
			c = tmp2.month
			c2 = tmp2.day
			if b < 10:
				b = "0"+str(b)
			if b2 < 10:
				b2 = "0"+str(b2)
			if c < 10:
				c = "0"+str(c)
			if c2 < 10:
				c2 = "0"+str(c2)
			val = str(tmp2.year) + str(c) + str(c2) + str(tmp.year) + str(b) + str(b2)
			tmp_dates.append(val)
	return tmp_dates

def save_periods_values(plannify,per="#",details="#"):
	if per == "#":
		per = plannify.m_periode

	if details == "#":
		details = plannify.m_planify.split("_")
	else:
		details = details.split("_")
	tmp_splits = list()
	tmp_dates = list()
	tmp_values = list()
	tmp = {
		"Jan":"01",
		"Fev":"02","Fév":"02","Feb":"02","Féb":"02",
		"Mar":"03","Mars":"03",
		"Avr":"04","Avril":"04","Apr":"04",
		"Mai":"05","May":"05",
		"Jui":"06","Juin":"06","Jun":"06",
		"Jul":"07",
		"Aou":"08","Aout":"08","Aug":"08",
		"Sep":"09",
		"Oct":"10","Opt":"10",
		"Nov":"11",
		"Dec":"12"
	}
	if per.m_logic_type == 2:
		for d in details[:-1]:
			a_split = d.split(" ")
			tmp_splits.append(a_split)
			if len(a_split) > 8:	
				tmp_dates.append([a_split[2],a_split[3],a_split[4],a_split[6],a_split[7],a_split[8]])

		for t in tmp_dates:
			if (len(t) > 5):
				z1 = t[0]
				z2 = t[3]
				
				if int(z2)<10 and len(z2) < 2:
					z2 = "0"+str(z2)
				if int(z1)<10 and len(z1) < 2:
					z1 = "0"+str(z1)
				val = str(t[5]) + tmp[t[4]] + z2 + str(t[2]) + tmp[t[1]] + z1
				tmp_values.append(val)

	elif per.m_logic_type in [3,6,9]:
		for d in details[:-1]:
			a_split = d.split(" ")
			tmp_splits.append(a_split)	
			if len(a_split) > 7:	
				tmp_dates.append([a_split[1],a_split[2],a_split[3],a_split[5],a_split[6],a_split[7]])

		for t in tmp_dates:
			if (len(t) > 5):
				z1 = t[0]
				z2 = t[3]
				if int(z2)< 10  and len(z2) < 2:
					z2 = "0"+str(z2)
				if int(z1)<10  and len(z1) < 2:
					z1 = "0"+str(z1)
				val = str(t[5]) + tmp[t[4]] + z2 + str(t[2]) + tmp[t[1]] + z1
				tmp_values.append(val)
	return tmp_values

def get_period_values(period,plannify):
	return save_periods_values("#",period,plannify)

def set_pv_tp(tp):
	values = "|".join(save_periods_values(tp))
	tp.m_value = values
	tp.save()

def transform_to_plannify(value):
	tmp = {
		"01":"Jan",
		"02":"Fev",
		"03":"Mar",
		"04":"Avr",
		"05":"Mai",
		"06":"Jui",
		"07":"Jul",
		"08":"Aou",
		"09":"Sep",
		"10":"Oct",
		"11":"Nov",
		"12":"Dec"
	}
	result = "du "+str(int(value[14:]))+" "+tmp[str(value[12:14])]+" "+value[8:12]+" au "+str(int(value[6:8]))+" "+tmp[str(value[4:6])]+" "+value[:4]
	return result

def update_plannify():
	from .models import TachePlannify
	tps = TachePlannify.objects.filter()
	for t in tps:
		set_pv_tp(t)