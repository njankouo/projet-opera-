# -*- coding: utf-8 -*-
from .models import *

def delete_entities(es):
	es = es.split("#")
	for e in es[:-1]:
		e = Entity.objects.get(id=int(e))
		e.delete()

def delete_operations(es):
	es = es.split("#")
	a = Operation.objects.get(id=int(es[0])).tache
	for e in es[:-1]:
		e = Operation.objects.get(id=int(e))
		e.delete()
	return a

def duplicate_operation(o,name="#"):
	o2 = Operation()
	if name == "#":
		o2.nom = o.nom
	else:
		o2.nom = name
	o2.personnel = o.personnel
	o2.accountable = o.accountable
	o2.consulted = o.consulted
	o2.informed = o.informed
	o2.m_institution = o.m_institution
	o2.etat = '0'
	o2.m_tache_plannification = o.m_tache_plannification
	o2.m_value = o.m_value
	o2.m_value_reported = o.m_value_reported
	o2.save()
	# Duplicate OperationFile
	oF = OperationFile.objects.filter(operation=o).first()
	if oF is not None:
		oF2 = OperationFile(operation=o2,m_file=oF.m_file,m_field=oF.m_field)
		oF2.save()
	# Duplicate OperationPeriode
	oP = OperationPeriode.objects.filter(m_operation=o).first()
	if oP is not None:
		oP2 = OperationPeriode(m_operation=o2,m_chronogramme=oP.m_chronogramme,m_desc_realisation=oP.m_desc_realisation)
		oP2.save()
	# Duplicate Operation Rapport
	# NO
	o2.save()
	return o2

def duplicate_tache(t,new_name="#"):
	const_id = t.id
	eH = None
	eH = EntityHierachie.objects.filter(m_sup_entity=t.sup_entity(),m_sub_entity=t).first()
	if eH != None:
		eH2 = EntityHierachie(m_sup_entity=t.sup_entity())
	t = Tache.objects.get(id=t.id)

	clone = Tache(structure=t.structure)
	clone.save()
	for s in t.structures.filter():
		clone.structures.add(s)

	#clone.structures.set(t.structures)
	clone.m_nom = t.m_nom
	clone.m_type_entity = t.m_type_entity
	clone.m_value_fields = t.m_value_fields
	clone.m_reported_fields = t.m_reported_fields
	clone.m_pic_represented = t.m_pic_represented
	clone.m_indicateurs_reels = t.m_indicateurs_reels
	clone.montant = t.montant
	clone.save()
	if new_name != "#":
		clone.set_name(new_name)

	clone.save()

	#SDDSD
	t3 = TachePlannify.objects.filter(m_tache__id=const_id).first()
	clone3 = TachePlannify(m_tache=clone,m_periode=t3.m_periode,m_value=t3.m_value,m_planify=t3.m_planify)
	clone3.save()

	"""
	clone.structures.set(t.structures.filter())
	clone.save()
	"""

	
	if eH2 != None:
		eH2.m_sub_entity = Entity.objects.get(id=clone.id)
		eH2.save()
	return clone

def duplicate_entity(e,new_name="#"):
	if e.m_type_entity.is_tache == True:
		tmp = duplicate_tache(e,new_name)
		tmp = Entity.objects.get(id=tmp.id)
	else:
		actu_e = e.id
		tmp = e
		tmp.id = None #Entity.objects.order_by('id').last().id+1
		if new_name != "#":
			tmp.set_name(new_name)
		tmp.save()

	#if e.
	try:
		
		actu_e = Entity.objects.get(id=actu_e)
		if actu_e.sup_entity() != None and actu_e.sup_entity() != actu_e :
			eH = EntityHierachie.objects.filter(m_sup_entity=actu_e.sup_entity(),m_sub_entity=tmp).first()
			if eH == None:
				eH = EntityHierachie(m_sup_entity=actu_e.sup_entity(),m_sub_entity=tmp)
				eH.save()
		
		#pass
	except:
		pass
	return tmp

def duplicate_entity_logic(e,new_name="#"):
	sub_entities = e.sub_entities()
	if e.m_type_entity.is_tache == True:
		#tmp = duplicate_tache(e,new_name)
		tmp = duplicate_entity(e,new_name)
	else:
		tmp = duplicate_entity(e,new_name)

	for s in sub_entities:
		#eHS = EntityHierachie.objects.filter(m_sub_entity__id=s.id).first()
		if tmp.m_type_entity.is_tache == False:
			tmp3 = duplicate_entity_logic(s)
			tmp2 = EntityHierachie.objects.filter(m_sub_entity=tmp3).first()
			if tmp2 == None :
				tmp2 = EntityHierachie(m_sup_entity=tmp,m_sub_entity=tmp3)
			else:
				tmp2.m_sup_entity=tmp
			tmp2.save()
		else:
			tmp3 = duplicate_operation(s)
			tmp3.tache = Tache.objects.get(id=int(tmp.id))
			# Generate Code of the Tache
			tmp3.save()
			assign_code_operations([tmp3])
			#tmp3.save()
	return tmp

def reassign_multiple(e1,e3):
	e2s = e1.sub_entities()
	for e2 in e2s:
		tmp = duplicate_entity(e3)
		eH = EntityHierahie(m_sub_entity=tmp,m_sup_entity=e2)
		eH.save()

def duplicate_entity_sup(e1,e2,logic=False):
	# e1 and e2 must be Entities
	if not logic:
		tmp = duplicate_entity(e1)
	else:
		tmp = duplicate_entity_logic(e1)
	eH = EntityHierachie.objects.filter(m_sub_entity=tmp)
	eH.delete()
	eH = EntityHierachie(m_sup_entity=e2,m_sub_entity=tmp)
	eH.save()

def duplicate_institution_full(institution):
	tops = institution.top_entity().lines()
	pass

def clone_to_sup(e):
	sup = e.sup_entity()
	for s in sup.sub_entities():
		if s != e:
			for a in e.sub_entities():
				tmp = duplicate_entity_logic(a)
				eH = EntityHierachie.objects.filter(m_sub_entity__id=tmp.id).first()
				if eH != None:
					eH.m_sup_entity = s
					eH.save()

def assign_supervisors_entity(entity):
	nom = "Responsable "+str(entity)
	description = "Supervise "+str(entity)
	actual_institution = entity.m_type_entity.get_institution()
	m_entities = entity
	m_nature = '1'
	r = Role(nom = nom,description = description,actual_institution=actual_institution)
	r.save()
	r.m_entities.set([entity])
	r.save()

def assign_supervisors_entities(entities):
	for e in entities:
		assign_supervisors_entity(e)

def clean_entities():
	entities = list(Entity.objects.filter())
	entities  += list(Tache.objects.filter())
	for tmp in entities:
		eH = EntityHierachie.objects.filter(m_sub_entity__id=tmp.id).first()
		if eH == None and tmp.m_type_entity.hierachie() != 0:
			tmp.delete()

def assign_institution(operations):
	for o in operations:
		o.m_institution = o.institution2()
		o.save()

def assign_code_operations(operations):
	for o in operations:
		t = o.tache
		if t != None :
			t2 = t.sup_entity()
			if t2 != None:
				tmp = str(t.id)+"#"
				while t2 != None :
					tmp = str(t2.id)+"#"+tmp
					t2 = t2.sup_entity()
				o.code = tmp
				#print(o)
				o.save()

def split_extras1(elt):#Entities
	nb_fields = elt.m_type_entity.m_fields.split("|")
	actual = elt.m_value_fields.split("|")
	tmp_field = ""
	j = 0
	for i in nb_fields[:-1]:
		tmp_field += actual[j]+"|"
		j+=1
	tmp_field += actual[j]
	elt.m_value_fields = tmp_field
	elt.save()

def split_extras2(elt):#Operations
	institution = elt.institution()
	nb_fields = institution.operations_modules().m_fields.split("|")
	tmp_field = ""
	actual = elt.m_value.split("|")
	for i in nb_fields[:-1]:
		tmp_field += actual[j]+"|"
		j+=1
	tmp_field += actual[j]
	elt.m_value = tmp_field
	elt.save()

def fill_extras(elt):
	institution = elt.institution()
	fields = institution.operations_modules().m_fields.split("|")
	actual = elt.m_value.split("|")
	start_index = len(fields) - len(actual)
	tmp_field = ""
	if start_index > 0:
		for i in range(0,len(actual)):
			tmp_field += actual[i] + "|"
		for i in range(len(actual),len(fields)-1):
			tmp_field += " "+"|"
	elt.m_value = tmp_field
	elt.save()

def fill_taches_periodes(id_institution):
	institution = Institution.objects.filter(id=id_institution)
	taches = institution.taches()
	tmp_plannification = "du 1 Jan 2023 au 31 Jan 2023_du 1 Fev 2023 au 28 Fev 2023_du 1 Mars 2023 au 31 Mars 2023_du 1 Avr 2023 au 30 Avr 2023_du 1 Mai 2023 au 31 Mai 2023_du 1 Jui 2023 au 30 Jui 2023_du 1 Jul 2023 au 31 Jul 2023_du 1 Aou 2023 au 31 Aou 2023_du 1 Sep 2023 au 30 Sep 2023_du 1 Oct 2023 au 31 Oct 2023_du 1 Nov 2023 au 30 Nov 2023_du 1 Dec 2023 au 31 Dec 2023_"
	value = "2023013120230101|2023022820230201|2023033120230301|2023043020230401|2023053120230501|2023063020230601|2023073120230701|2023083120230801|2023093020230901|2023103120231001|2023113020231101|2023123120231201"
	period = institution.default_period
	for t in taches:
		tp = TachePlannify.objects.filter(m_tache = t)
		if tp == None:
			tp = TachePlannify(m_value=value,m_tache_plannification=tmp_plannification,m_periode=period)
			tp.m_tache = t
			tp.save()

def fill_operations_periodes(id_institution):
	institution = Institution.objects.filter(id=id_institution).first()
	taches = institution.taches()
	for t in taches :
		plannification = t.plannification().table()
		operations = t.operations()
		operations.delete()
		i = 0
		for p in plannification:
			op = Operation(m_institution=institution,tache=t,m_tache_plannification=p)
			dtr_pl = p.split(" ")
			dtr_pl = dtr_pl[2]+" "+dtr_pl[3]
			if i < 10:
				code = "0"+str(i+1)
			op.nom = code+" - Rapport "+str(t)+" ("+dtr_pl+") "
			i += 1
			assign_code_operations([op])
			op.save()

def assign_operationRACI_accountable(id_institution):
	pass