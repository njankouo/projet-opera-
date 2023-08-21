# -*- coding: utf-8 -*-
from asgiref.sync import sync_to_async

from django.http import FileResponse, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout

from django.core.mail import send_mail,send_mass_mail
from django.conf import settings
from django.core.mail import EmailMessage,EmailMultiAlternatives
from django.core.cache import cache
from django.views.decorators.cache import cache_page

from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import ProtectedError
from django.contrib.auth.decorators import login_required

from .models import *
from .utilities import get_period_values,set_pv_tp,subperiods_value,transform_to_plannify
from .utilities2 import split_extras1
import os
import datetime

@login_required(login_url='/log_account') 
def admin_institution(request):
	template = "webpages/ctn_bpf/institution_admin.html"
	context = {
		'edit':0
	}
	return render(request,template,context)

@login_required(login_url='/log_account')
def contact(request):
	template = "webpages/ctn_bpf/contact.html"
	context = {
		'edit':0
	}
	return render(request,template,context) 

def edit_institution(request,institution_id):
	template = "webpages/ctn_bpf/institution_admin.html"
	context = {
		'edit':1,
		'institution':Institution.objects.get(id=int(institution_id))
	}
	return render(request,template,context)	

def save_edit_institution(request):
	nom = request.POST["nom"]
	code = request.POST["code"]
	try:
		file  = request.FILES["file"]
	except:
		file = None
	
	insti_id = int(request.POST['insti_id'])
	institution = Institution.objects.get(id=insti_id)
	institution.sigle = code
	institution.nom = nom
	if file != None:
		institution.img = file
	institution.save()
	return redirect('/')

def save_institution(request):
	nom = request.POST["nom"]
	response = redirect("/")
	try:
		code = request.POST["code"]
	except:
		code = nom
	try:
		image = request.FILES["file"]
	except:
		image = OperaFile.objects.filter(m_name="IDF").first().m_file # Instituti Defaut FIle
	try:
		desc = request.POST['desc']
	except:
		desc = " "
	try:
		app_code = request.POST['app_code']
	except:
		app_code = "#"
	#Informations Savers

	owner = Owner.objects.filter(m_code=app_code).first()
	if owner == None:
		response = specific_log(request,2)
	else:
		nb_institutions = owner.nb_institutions()
		if ( owner.m_bought == False and nb_institutions == 0 ) or (owner.m_bought == True and nb_institutions <= owner.m_type ):
			institution = Institution(sigle=code,nom=nom,img=image)
			institution.owner = owner
			institution.save()
			owner.m_user.personnel.actual_institution = institution
			owner.m_user.personnel.save()
			try:
				check_mail = request.POST['check_mail']
			except:
				check_mail = False
			if check_mail == True:
				owner.m_mail_notified = True
				owner.save()
			#owner.save()
			if request.user.is_authenticated == False:
				user = owner.m_user
				login(request,user)

			# tache hierachy modifier
			entity = EntityType(m_nom="Projet")
			entity.m_fields = "Nom du Projet|Objectif du Projet|"
			entity.m_type_fields = "text|text|"
			entity.m_fields_rapported = "Commentaires|"
			entity.m_type_fields_rapp = "text|"
			entity.save()
			type_entity = InsitutionEntities(m_hierachie=0)
			type_entity.m_entity_type = entity
			type_entity.m_institution = institution
			type_entity.save()

			# Tache Launcher
			entity = EntityType(m_nom="Tache")
			entity.is_tache = True
			entity.m_fields = "Nom de la Tache|Objectif de la Tache|"
			entity.m_type_fields = "text|text|"
			entity.m_fields_rapported = "Commentaires|"
			entity.m_type_fields_rapp = "text|"
			entity.save()
			type_entity = InsitutionEntities(m_hierachie=1)
			type_entity.m_entity_type = entity	
			type_entity.m_institution = institution
			type_entity.save()

			#Initialiasion des Personnels et des Rôles
			personnel = Personnel.objects.get(bd_user__id=request.user.id)
			role = Role(nom="Administrateur "+str(institution),description="Supervise la Plateforme",actual_institution=institution,permissions=100)
			role.save()
			function = Personnel_Function(m_institution=institution,m_personnel=personnel,m_role=role)
			function.save()
			role = Role(nom="Opérant "+str(institution),description="Exécute une Tâche",actual_institution=institution,permissions=0)
			role.save()
			
			# Initialisation des Structures
			structure = Structure(nom=institution.sigle,designation=institution.nom)
			structure.institution = institution
			structure.save()
			pers_struc = Personnel_Structure(m_personnel = personnel,m_structure=structure)
			pers_struc.save()

			#Initialisation des Periodes
			configurations_periodes = Periode.objects.filter(m_initial=True)
			for p in configurations_periodes:
				per = Institution_Periodes(m_periode=p,m_institution=institution,m_default=True)
				per.save()
			institution.default_period = configurations_periodes.last()
			institution.default_subperiod = institution.default_period.sub_periods().first()
			institution.save()
		else:
			request.session['too_much_ins'] = 1
			response = redirect('/log_account/')
	return response

def set_default_period(request,period=0,sub_period="#"):
	#r_institution = request.COOKIES['institution']
	r_institution = request.user.personnel.actual_institution
	if int(period) != 0:
		r_periode = Periode.objects.get(id=int(period))
		r_institution.default_period = r_periode
		r_institution.default_subperiod = r_periode.sub_periods().last()
	if sub_period != "#":
		r_sub_period = SubPeriode.objects.get(id=int(sub_period))
		r_institution.default_subperiod = r_sub_period
	r_institution.save()
	return redirect('/configurations/')

def authorized_institutions(request):
	if request.user.is_staff:
		institutions = Institution.objects.filter()
	else :
		institutions = [request.user.personnel.get_institution]
	return institutions

def basis(request):
	permissions = list()
	actual_institution = None
	animate = None
	animate2 = None
	context = dict()
	user = request.user
	try:
		if request.session['logged'] == 1:
			request.session['logged'] = 0
			animate = 0
	except:
		pass
	try:
		if request.session['new_rapport'] == 1:
			request.session['new_rapport'] = 0
			animate2 = 0
		elif request.session['new_rapport'] == 2:
			request.session['new_rapport'] = 0
			animate2 = 1
	except:
		pass

	if request != None and user.is_authenticated:
		actual_institution = user.personnel.actual_institution
		bool(actual_institution)

		programmes = list() #request.user.personnel.get_programmes()
		nb_programmes = 0

		personnel = request.user.personnel
		bool(personnel)

		prenom =  personnel.prenom
		nom = personnel.nom
		role =  personnel.get_function(actual_institution.id)
		picture =  personnel.photo
		functi = role
		entity_manage = None
		if actual_institution.owner != None and actual_institution.owner.m_user == request.user:
			permissions = 100 
		elif functi == None:
			permissions = 10			
		else:
			permissions = functi.m_role.permissions
			if functi.m_role.m_nature == "1":
				#enti = funxti
				eRACI = personnel.RACI_manage()
				if eRACI != None:
					if eRACI[0] != None:
						entity_manage = eRACI[0]
			elif permissions < 0:
				entity_manage = functi.m_entity
		context = {
			'actual_institution':actual_institution,
			'animate':animate,
			'animate2':animate2,
			'prenom':prenom,
			'role':role,
			'nom':nom,
			'picture':picture,
			'permissions':permissions,
			'programmes':programmes,
			'nb_programmes':nb_programmes,
			'entity_manage':entity_manage
		}
		if entity_manage != None:
			context["my_entities"] = personnel.RACI_list()
			context["no_simple_user"] = context["my_entities"] != []
			context["type_ents"] = entity_manage.m_type_entity
			context["hierachie_ent"] = entity_manage.m_type_entity.hierachie()

		context['default_struc_name'] = actual_institution.default_struc_name
		context['this_period'] = datetime.datetime.now()
		context['operations_name'] = actual_institution.operations_name
		context['insti_structures'] = actual_institution.structures()
		context['default_period'] = context['actual_institution'].default_period

		get_entities = actual_institution.get_entities()
	
		context['get_entities'] = get_entities
		context['get_entities2'] = list(get_entities)[:-1]

		top_entity =  context['actual_institution'].top_entity()
		bool(top_entity)
		context['top_entity'] = top_entity

		last_entity =  context['actual_institution'].last_entity()
		bool(last_entity)
		context['last_entity'] = last_entity


		if actual_institution.finan_options != None:
			context["finances"] = actual_institution.finances()
			context["real_finances"] = 0
			context["finan_options"] = actual_institution.finan_options
			context["depenses_eff"] = actual_institution.depenses_eff

		tmp_week = int(max(1,context['this_period'].day / 7))
		if context['this_period'].day > context['this_period'].isoweekday()*tmp_week :
			tmp_week += 1 
		context['this_week'] = tmp_week
		context['operations_modules'] = Aggregate.objects.filter(m_institution__id = context['actual_institution'].id).select_related('m_institution').first()


	else:
		actual_institution = None
		context["institution"] = None
	return context

def agenda(request):
	template = "webpages/ctn_bpf/agenda_week.html"
	context = basis(request)
	return render(request,template,context)

def log_account(request):
	template = "webpages/ctn_bpf/login.html"
	context = dict()
	try:
		if request.session['too_much_ins'] == 1:
			context['too_much_ins'] = True
			request.session['too_much_ins'] = None
	except:
		pass
	try:
		if request.session['new_user'] == 1:
			#request.session['new_user'] = 0
			animate = 1
			context['new_user'] = animate
			request.session['new_user'] = 0
	except:
		pass
	try:
		context['bad_log'] = ( request.session['bad_log'] != None and request.session['try_log'] != None )
		request.session['try_log'] = None
	except:
		pass
	return render(request,template,context)

#@cache_page(60 * 15)
def index_log(request,nature):
	if True :
		context = basis(request)
		context['menu'] = 'i'
		elements = list()
		top_entity =  context['top_entity']

		tops = top_entity.lines()
		bool(tops)

		context['lvl'] = nature
		if nature == -1 and context['permissions'] >= 0:
			nature = 0

		if context['permissions'] == 0:
			nature = InsitutionEntities.objects.filter(m_institution=context['actual_institution']).select_related('m_institution').last().m_hierachie
			bool(nature)

		context['nature'] = nature
		context['next_nature'] = nature + 1
		# If any Tops have been created, redirection

		if tops.first() == None:
			template = "webpages/ctn_bpf/index_empty.html"
			context['type_entity'] = InsitutionEntities.objects.filter(m_hierachie=nature,m_institution=context['actual_institution']).select_related('m_institution').first().m_entity_type			
			tmp_lines = list()
		else:
			if context["entity_manage"] != None:
				hierachy = context["entity_manage"].m_type_entity.hierachie()
				hierachi_id = context["entity_manage"].id
				return redirect("gestionnaire/"+str(hierachy)+"/"+str(hierachi_id)+"/")
			else:
				template = "webpages/ctn_bpf/operations_home.html"
			nb_elements = 0
			for t in tops:
				elements.append({'entity':t,'values':t.levels(nature,context['actual_institution'])})

			context['elements'] = elements
			context['type_entity'] = InsitutionEntities.objects.filter(m_hierachie=nature,m_institution=context['actual_institution']).select_related('m_institution').first()
			if context['type_entity'] != None:
				context["type_entity"] = context["type_entity"].m_entity_type				
				tmp_lines = context['type_entity'].lines()
			else:
				tmp_lines = list()
		# Moyenne de Progression
		nb_elt = 0
		progress = 0
		"""
		for elt in tmp_lines:
			progress += elt.progression()
			nb_elt += 1
		if nb_elt > 0:
			progress /= nb_elt
		"""

		progress = context['actual_institution'].progression()
		context['actual_progression'] = round(progress,2)
		paginator_o = Paginator(elements,6)
		page_number_o = request.GET.get('page')
		elements_page = paginator_o.get_page(page_number_o)
		#oeuvres_date
		context['pages_o']=elements_page
		context['num_pages']=paginator_o.num_pages
		context['page_range']=paginator_o.page_range
	return render(request,template,context)	
	
def index(request,nature=-1):
	if request.user.is_authenticated:
		return index_log(request,nature)
	else:
		context = dict()
		try:
			personnel_opera = settings.PERSONNAL_OPERA
			context["personnel_opera"] = personnel_opera
			if personnel_opera:
				context['actual_institution_name'] = settings.PERSONNAL_INSTITUTION
		except:
			personnel_opera = None

		template = "webpages/ctn_bpf/presentation.html"
		#context['temoignages'] = Temoignage.objects.filter()[:3]
		context['institution_count'] = Institution.objects.count()
		context['projet_count'] = 0
		tmp1 = InsitutionEntities.objects.filter(m_hierachie=1)
		for t in tmp1:
			context['projet_count'] += t.m_entity_type.lines().count()
		context['operations_count'] = Operation.objects.count()
		context['personnel_count'] = Personnel.objects.count()
	try:
		if request.session['too_much_ins'] == 1:
			context['too_much_ins'] = True
			#request.session['too_much_ins'] = None
	except:
		pass
	try:
		if request.session['assistance'] == 1:
			context['assist_send'] = True
			request.session['assistance'] = None
	except:
		pass
	return render(request,template,context)

def bad_auth(request):
	template = "webpages/ctn_bpf/bad_auth.html"
	context = {
		'error':"Erreur au niveau de l'Adresse/Mot de Passe"
	}
	return render(request,template,context)

def main(request,menu_main=0):
	template = "webpages/ctn_bpf/main.html"
	if menu_main  == 1:
		template = "webpages/ctn_bpf/presentation_framework.html"
	elif menu_main == 2:
		template = "webpages/ctn_bpf/presentation_documentation.html"
	docus = OperaFile.objects.filter(m_category="DOC")
	apps = OperaApp.objects.filter()
	context = {
		"docus":docus,
		"apps":apps
	}
	return render(request,template,context)

def gestionnaire_search(request):
	generator = request.POST['generator']
	name = request.POST['search']
	if generator == '0':
		hierachy = int(request.POST['hierachy'])
		gest = int(request.POST['gest'])
		response = gestionnaire(request,hierachy,gest,name)
	elif generator == 'o':
		gest = int(request.POST['gest'])
		response = ges_taches(request,gest,None,name)
	elif generator == 's':
		response = structures(request,name)
	elif generator == 'r':
		response = roles(request)
	elif generator == 'p':
		response = personnels(request,name)
	elif generator == 'i2':
		hierachy = int(request.POST['hierachy'])
		gest = int(request.POST['gest'])
		response = evaluer(request,hierachy,gest,name)
	elif generator == "ex":
		response = extra(request,name)
	elif generator == "dSV":
		pass
	return response

#@cache_page(60 * 15)
@login_required(login_url='/log_account')
def gestionnaire(request,gest_val,gest_id=0,name=None,structure=None,periode=None,enums="#"):
	tmp_gest_val = gest_val
	context = basis(request)
	actual_institution = context['actual_institution']
	bool(actual_institution)

	context['base_img_val'] = context['actual_institution'].img.url

	if int(gest_val) == -1:
		gest_val = InsitutionEntities.objects.filter(m_institution=actual_institution).select_related('m_institution').last().m_hierachie
		bool(gest_val)
		tmp_gest_val = gest_val
	try:
		entity = InsitutionEntities.objects.filter(m_hierachie=gest_val,m_institution=actual_institution).select_related('m_institution').first().m_entity_type
	except:
		entity = InsitutionEntities.objects.filter(m_institution=actual_institution).select_related('m_institution').last().m_entity_type

	is_tache = False
	context['is_sub_tache'] = False
	context['detail_g_v'] = False
	context['sup_hierachy'] = list()
	if gest_id != 0:
		#gest_val = str(int(gest_val) + 1)
		#entity = InsitutionEntities.objects.filter(m_hierachie=gest_val,m_institution=context['actual_institution']).first().m_entity_type
		sup_entity = Entity.objects.filter(id=gest_id).first()
		if sup_entity != None:
			lines = sup_entity.sub_entities()
		else:
			lines = list()
		tmp_gest_val = str(int(gest_val)+1)
		sub_type = InsitutionEntities.objects.filter(m_hierachie=tmp_gest_val,m_institution=context['actual_institution']).select_related('m_institution').first()

		if context["permissions"]<=0 and sup_entity in context["my_entities"]:
			context["autoE"] = 1
		elif context["permissions"]<=0 :
			for t in sup_entity.sup_hierachie():
				if t in context["my_entities"]:
					context["autoE"] = 1
					break
		if sub_type != None: #Ce n'est pas une tache
			sub_type = sub_type.m_entity_type
			fields = sub_type.fields()
			context['is_sub_tache'] = sub_type.is_tache
			context['sub_entity'] = sub_type
			context['base_val'] = sup_entity
			context['sub_entities'] = sup_entity.sub_entities()
			context['gest_id']=gest_id
			context['objects_field'] = sub_type.objects_field()
			context['calculates_field'] = sub_type.calculates_field()
			if sup_entity != None:
				if sup_entity.m_type_entity.is_pic_represented == True and sup_entity.m_pic_represented != None:
					try:
						context['base_img_val'] = sup_entity.m_pic_represented.url
					except:
						pass
			actu_entity = sub_type
		else:
			is_tache = True
			fields = list()
			actu_entity = entity
		context['detail_g_v'] = True
	else:
		actu_entity = entity
		enmPT = actu_entity.enum_fields()['result']
		"""
		test_PT = dict()
		for e in enmPT:
			test_PT[e['name']] = e['lines']
		"""
		lines = entity.lines()
		is_tache = entity.is_tache
		fields = entity.fields()
		context['objects_field'] = entity.objects_field()
		context['calculates_field'] = entity.calculates_field()


	if name != None:
		tmp = list()
		for l in lines:
			if name in l.get_name():
				tmp.append(l)
		lines = tmp

	if structure != None:
		tmp = list()
		for l in lines:
			if l.structure == structure:
				tmp.append(l)
		lines = tmp

	if periode != None:
		tmp = list()
		for l in lines:
			if periode in l.plannification():
				tmp.append(l)
		lines = tmp


	context['is_tache'] = is_tache
	context['hierachy'] = int(tmp_gest_val)
	context['next_hierachy'] = int(tmp_gest_val) + 1
	context['gest_val'] = int(gest_val)
	context['entity'] = entity
	context['actu_entity'] = actu_entity
	context['sup_zone'] = entity.sup_entity(actual_institution.id)
	context['fields'] = fields	
	#context['lines'] = lines
	context['menu'] = 'g'
	paginator_o = Paginator(list(lines),10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	#oeuvres_date
	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range

	if int(tmp_gest_val) > 0 and gest_id != 0:
		context['sup_hierachy'] = sup_entity.sup_hierachie()


	if ( int(tmp_gest_val)-1 > 0 ) and InsitutionEntities.objects.filter(m_hierachie=(int(tmp_gest_val)-1),m_institution=context['actual_institution']).select_related('m_institution').first() == None:
		context['none_search'] = True
	else:
		context['first_sup_search'] = True

	if tmp_gest_val == '0' and entity.m_enum_values in ["",None]:
		context['none_search'] = True
	context['searches'] = list(InsitutionEntities.objects.filter(m_hierachie=(int(tmp_gest_val)-1),m_institution=context['actual_institution']).select_related('m_institution'))
	"""
	if is_tache or context['is_sub_tache']:
		context['searches'].append({'label':'Structure','code':'s','values':context['structures']})
	"""
	try:
		if context['base_val'] != None:
			taches = list()#context['base_val'].taches()
			struc = set()
			for t in taches:
				struc.add(t.structure)

			context['structures_not_null'] = struc
	except:
		pass
	try:

		if context["entity_manage"] != None:
			context["not_add"] = 1
			entityd = Entity.objects.get(id=context['base_val'].id)
			if entityd in context["my_entities"]:

				if context["role"].m_role.permissions >= 0:
					context["permissions"] = 0
				if context["permissions"] >= 0:
					request.session["permissions_valider"] = True
			else:
				if request.session["permissions_valider"] == True:
					pass#context["permissions"] = -100
	except:
		pass
	if context['permissions'] < 0:
		template = "webpages/ctn_bpf/entities_simple_user.html"
		try:
			if context['base_val'].id == context['entity_manage'].id:
				context["auto_simple"]= 1
		except:
			pass
	else:
		if is_tache or context['is_sub_tache'] == True:
			template = "webpages/ctn_bpf/taches.html"
			context['structures'] = Structure.objects.filter(institution=context['actual_institution']).select_related('institution')
		else:
			template = "webpages/ctn_bpf/entities.html"


	if enums != "#":
		context['da_enums'] = enums
	if is_tache and gest_id != 0:
		response = redirect('/taches/'+str(gest_id)+'/')
	else:
		response = render(request,template,context)
	return response

@login_required(login_url='/log_account')
def messengers(request):
	context = basis(request)
	template = "webpages/ctn_bpf/messengers.html"	
	return render(request,template,context)

#@cache_page(60 * 15)
def ges_taches(request,tache_id,arg_period=None,search=None):
	context = basis(request)
	base_val = Tache.objects.get(id=int(tache_id))
	lines = Operation.objects.filter(tache=base_val).select_related('tache')
	lines_tache = lines
	context['sup_hierachy'] = base_val.sup_hierachie()

	if search != None:
		tmp = lines
		lines = list()
		for l in tmp:
			if search in str(l):
				lines.append(l)
	context['arg_period'] = arg_period
	if arg_period != None:
		periodes = base_val.plan_months()
		prd = periodes[(arg_period-1)]
		context['periodes'] = prd
		lines = lines.filter(m_tache_plannification=prd)
		context['test'] = list()
		actual_institution = context['actual_institution']
		week = list()
		for t in actual_institution.default_subperiod.decoup_desc_slip2():
			week.append({'per':t,'val':list()})
		for l in lines:
			ps = l.periodes()
			t_ps = ps.desc_split()
			i_p=0
			for t in t_ps:
				if int(t) == 0:
					week[i_p]['val'].append(l)
					break
				i_p+=1	
		context['test'] = week


	context['none_search'] = True
	context['entity'] = base_val.m_type_entity
	context['base_val'] = base_val
	context['sub_entity'] = context['actual_institution'].operations_name
	tmp_perso = Personnel.objects.filter()
	context['personnels'] = set()
	for t in tmp_perso:
		if context['actual_institution'] in t.all_institutions():
			context['personnels'].add(t)
	context['roles'] = Role.objects.filter(actual_institution=context['actual_institution']).select_related('actual_institution')
	plan = base_val.plannification()
	if plan != None:
		context['searches'] = [{'label':'Période','values':base_val.plannification().table(),'not_filter':True}]
	else:
		context['searches'] = [{'label':'Période','values':["Aucune Valeur"],'not_filter':True}]
	context['g_v'] = 'o'
	context['menu'] = 'go'
	base_valE = Entity.objects.get(id=base_val.id)

	if context["permissions"]<=0 and base_valE in context["my_entities"]:
		context["autoE"] = 1
	elif context["permissions"]<=0:
		for t in base_val.sup_hierachie():
			if t in context["my_entities"]:
				context["autoE"] = 1
				break

	if context['permissions'] < 0:
		template = "webpages/ctn_bpf/operations_simple_user.html"
		if context['base_val'].id == context['entity_manage'].id:
			context["auto_simple"]= 1
			lines = lines_tache
	else: 
		if arg_period is None:
			template = "webpages/ctn_bpf/operations.html"
		else:
			template = "webpages/ctn_bpf/operations_periodes.html"

	paginator_o = Paginator(lines,12)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	context['lines']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range
	#context['roles_RACI'] =
	try:
		if request.session["permissions_valider"] == True:
			context["permissions"] = 0
			context["not_add"] = 1
	except:
		pass
	return render(request,template,context)

def structure_hie(request):
	return structures(request,None,1)

def structures(request,name=None,hierachie=None):
	template = "webpages/ctn_bpf/structure.html"
	context = basis(request)
	context['entity'] = str(context['actual_institution'].default_struc_name)
	context['lines'] = Structure.objects.filter(institution=context['actual_institution']).select_related('institution')
	if name != None:
		context['lines'] = context['lines'].filter(nom__contains=name)
	context['fields'] = ['Logo','Nom','Désignation','Responsable','Total : '+str(context['actual_institution'].last_entity())]
	context['menu'] = 's'
	context['personnels'] = Personnel.objects.filter(actual_institution=context['actual_institution']).select_related('actual_institution')
	context['g_v'] = 's'
	context['none_search'] = True	
	if hierachie != None:
		stH = context["actual_institution"].Structure_Hierachy()
		vals = ""
		for s2 in stH:
			s3 = s2.m_levels_fields.split("|")[:-1]
			for s in s3:
				vals += str(request.POST[s])+"|"
		tmp = vals.split("#")
		re = ""
		for tm in tmp:
			re += tm.split("|")[0]+"|"
		vals = re
		context['vals'] = vals
		context['lines'] = context['lines'].filter(values_hierachy__contains=vals)
		context["stH"] = stH[0].m_levels_fields
	return render(request,template,context)

def structure_details(request,structure_id=0):
	template = "webpages/ctn_bpf/structure_details.html"
	context = basis(request)
	structure = Structure.objects.get(id=int(structure_id))
	entity = context['actual_institution'].last_entity()
	lines = Tache.objects.filter(structure=structure).select_related('structure')

	paginator_o = Paginator(lines,10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range
	fields = entity.fields()

	context['structure'] = structure
	context['base_val'] = structure
	#context['gest_id']=gest_id
	context['entity'] = entity
	context['sub_entity'] = entity
	context['objects_field'] = entity.objects_field()
	context['fields'] = fields
	context['is_tache'] = True
	return render(request,template,context)


def users_simples(request,search=None):
	template = "webpages/ctn_bpf/roles.html"
	fields_personnel = ['','Nom','Prenom','Adresse Mail','Structure','Fonction','']
	fields_roles = ['Role','Description','Entité']
	personnel = Personnel.objects.filter()
	context = basis(request)
	roles = Role.objects.filter(actual_institution=context['actual_institution'],is_simple_user=1).select_related('actual_institution')

	if search != None:
		roles = roles.filter(nom__contains=search)
	context['entity'] = 'Utilisateur Simple'
	context['fields1'] = fields_personnel
	context['personnel'] = personnel
	context['fields'] = fields_roles
	context['lines'] = roles
	context['g_v'] = 'r'
	context['g_vs'] = 'u2'
	return render(request,template,context)


def personnels(request,name=None,lis_peros=None):
	template = "webpages/ctn_bpf/roles.html"
	context = basis(request)
	context['entity'] = 'Personnel'
	context['fields'] = ['','Nom','Prenom','Téléphone','Adresse Mail','Fonction','Structures']
	context['lines'] = list()
	lines2 = set()
	tmp_perso = Personnel.objects.filter()
	if lis_peros == None:
		for t in tmp_perso:
			if context['actual_institution'] in t.all_institutions():
				atmp = {
				'id':t.id,
				'photo':t.photo,
				'prenom':t.prenom,
				'nom':t.nom,
				'tel':t.tel,
				'mail':t.mail,
				'get_function':t.get_function(context['actual_institution'].id),
				'get_structure':t.get_structure(context['actual_institution'].id)
				}
				context['lines'].append(atmp)
				lines2.add(t)
	else:
		context['lines'] = lis_peros
	#context['lines'] = Personnel.objects.filter(actual_institution=context['actual_institution'])
	if name != None:
		name = name.lower()
		tmps = context['lines']
		context['lines'] = list()
		for tt in tmps:
			ta = (tt["prenom"].lower()+tt["nom"].lower()).split(" ")
			for t in ta: 
				if name in str(t):
					context['lines'].append(tt)
					break
	paginator_o = Paginator(context['lines'],10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)

	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range

	context['menu'] = 'g'
	context['g_v'] = 'p2'
	context['g_vs'] = 'p2'
	context['roles'] = Role.objects.filter(actual_institution=context['actual_institution']).select_related('actual_institution')
	context['searches'] = []
	context['searches'].append({'label':'Fonction','values':Role.objects.filter(actual_institution=context['actual_institution']).select_related('actual_institution')})
	context['searches'].append({'label':'Structure','values':Structure.objects.filter(institution=context['actual_institution']).select_related('institution')})
	context['functions'] = list()
	context['structures'] = list()
	for p in lines2:
		context['functions'].append(p.get_function(context['actual_institution'].id))
		context['structures'].append(p.get_structure(context['actual_institution']))
	try:
		if request.session['perso_saved'] > 0:
			context['perso_saved'] = True
			tmp_user = Personnel.objects.get(id=request.session['perso_saved'])
			context['perso_get'] = tmp_user
			request.session['perso_saved'] = None
	except:
		pass
	return render(request,template,context)


def personnel_id(request,perso_id):
	context = basis(request)
	template = "webpages/ctn_bpf/profile.html"
	personnel = Personnel.objects.get(id=perso_id)
	context["personnel"] = personnel
	context["prenom"] =  personnel.prenom
	context["nom"] = personnel.nom
	context["role"] =  personnel.get_function(context["actual_institution"].id)
	return render(request,template,context)

"""
def roles(request):
	template = "webpages/ctn_bpf/personnel_roles.html"
	context = basis(request)
	context['lines'] = Role.objects.filter(institution=context['actual_institution'])
	context['menu'] = 'g'
	return render(request,template,context)
"""

def filter_perso(request,structure_id=0,role_id=0):
	if structure_id == 0:
		structure = request.POST["Structure"]
		tds = structure
		if str(structure) != '0' :
			structure = Structure.objects.get(id=int(structure))
	else:
		structure = Structure.objects.get(id=structure_id)

	if role_id == 0:
		role = int(request.POST["Fonction"])
		if str(role) != '0' :
			role = Role.objects.get(id=role)
	else:
		role = Role.objects.get(id=role_id)
	personnel = Personnel.objects.filter()
	context = basis(request)
	result = list()
	if structure != '0':
		for p in personnel:
			if p.get_structure() != None and p.get_structure().m_structure == structure:
				result.append(p)
	if role != '0':

		if structure == '0':
			tmp = personnel
		else:
			tmp = result
		result = list()
		for p in tmp:

			if p.get_function() != None and p.get_function().m_role == role:
				result.append(p)		
	return personnels(request,None,result)

def gestionnaire_id(request,gest_val,gest_id):
	pass

def log(request,out=False):
	if out == False:
		response = "/log_account/"
		result = False
		try:
			request.session['bad_log'] += 1
			if request.session['bad_log'] > 0:
				response = "/bad_auth/"
		except:
			request.session['bad_log'] = 1
			request.session['try_log'] = True
		r_email = request.POST['email']
		r_password = request.POST['password']
		users = User.objects.filter(email=r_email)
		r_username = User.objects.filter(email=r_email).last()
		if r_username != None:
			r_username = r_username.username
			user = authenticate(username=r_username,password=r_password)
			if user:
				login(request,user)
				result = True
				response = "/"
			else:
				if users.count() > 2:
					for u in users:
						r_username = u.username
						u_tmp = authenticate(username=r_username,password=r_password)
						if u_tmp:
							login(request,u_tmp)
							result = True
							response = "/"
			request.session['logged'] = 1
			request.session['bad_log'] = None
	else:
		logout(request)
		response = "/"
	return redirect(response)

def specific_log(request,type_view=0):
	template =  "webpages/ctn_bpf/specific_log.html"
	context = {

	}
	if type_view == 2:
		context['specific'] = 0 #Not Code 
	return render(request,template,context)

def save_entity(request):
	try:
		institution = Institution.objects.get(id=int(request.POST['institution']))
	except:
		institution = basis(request)['actual_institution']
	try:
		operation_aggregate = request.POST['ope_aggregate']
	except:
		entity_nom = request.POST['entity_nom']
		entity_hierachy = request.POST['entity_hierachy']
		fields_name = request.POST['fields_name']
		fields_type = request.POST['fields_type']
		rapp_fields_name = request.POST['fields_name2']
		rapp_fields_type = request.POST['fields_type2']
		if request.POST['entity_image'] == '0':
			entity_image = False
		else:
			entity_image = True
		edit_or_create = request.POST['edit_or_create']
		operation_aggregate = None
		enum_fields = request.POST['enum_fields']
	if operation_aggregate is None:			
		if edit_or_create == 'e':
			edit_id = request.POST['edit_id']
			institutionEntity = InsitutionEntities.objects.get(id=int(edit_id))
			entity = institutionEntity.m_entity_type
			actual_fields = entity.fields()
			actual_values = entity.lines()
			for l in actual_values:
				value = l.m_value_fields
				tmp = ""
				for f in fields_name.split("|")[:-1]:
					if f not in actual_fields:
						tmp += " |"
					else:
						tmp += str(l.get_value(f)) +"|"
				l.m_value_fields = tmp
				l.save()
		else:
			entity = EntityType(m_nom=entity_nom)
		entity.is_pic_represented = entity_image
		entity.m_nom = entity_nom
		entity.m_fields = fields_name
		entity.m_type_fields = fields_type
		entity.m_fields_rapported = rapp_fields_name
		entity.m_type_fields_rapp = rapp_fields_type
		entity.m_enum_values = enum_fields
		entity.indicateur_fields = request.POST['indicateurs_field']
		entity.save()
		# tache hierachy modifier
		hierachie = int(entity_hierachy) + 1

		# Decalage des Relations
		if edit_or_create != 'e':
			# Decalage des Entités
			to_decaler = InsitutionEntities.objects.filter(m_hierachie__gte=hierachie,m_institution=institution)
			for d in to_decaler:
				d.m_hierachie += 1
				d.save()
			institutionEntity = InsitutionEntities(m_hierachie=hierachie,m_entity_type=entity,m_institution=institution)
			if to_decaler.first() == None:
				institutionEntity.m_entity_type.is_tache = True
				institutionEntity.m_entity_type.save()	
		else:
			institutionEntity.m_hierachie = hierachie
		institutionEntity.save()
	else:
		edit_or_create = request.POST['edit_or_create_O']
		aggregate_name = request.POST['aggregate_name']
		aggregate_fields_name = request.POST['aggregate_fields_name']
		aggregate_fields_type = request.POST['aggregate_fields_type']
		aggregate_rap_fields_name = request.POST['aggregate_rap_fields_name']
		aggregate_rap_fields_type = request.POST['aggregate_rap_fields_type']
		
		# Aggregates launching
		aggregates = institution.operations_modules()
		# Aggregates launching

		if aggregates == None:
			aggregates = Aggregate(m_institution = institution)

		aggregates.m_nom = aggregate_name
		aggregates.m_fields = aggregate_fields_name
		aggregates.m_type_fields = aggregate_fields_type
		aggregates.m_fields_rapported = aggregate_rap_fields_name
		aggregates.m_type_fields_rapp = aggregate_rap_fields_type
		aggregates.save() 
	return redirect('/configurations/')

def save_entity_value(request):
	institution = int(request.POST['institution'])
	hierachie = int(request.POST['hierachie'])
	if hierachie != -1:
		type_entity = InsitutionEntities.objects.filter(m_hierachie=hierachie,m_institution__id=institution).first()
	else:
		type_entity = InsitutionEntities.objects.filter(m_institution__id=institution).last()
	type_entity = type_entity.m_entity_type
	fields_value = request.POST['fields']
	edit_or_create = request.POST['edit_or_create']

	is_tache = request.POST['is_tache']
	if is_tache == 'True':
		if edit_or_create == 'e':
			edit_id = request.POST['edit_id']
			entity = Tache.objects.get(id=int(edit_id))
			entity.m_value_fields=fields_value
			entity.m_type_entity=type_entity
		else:
			entity = Tache(m_value_fields=fields_value,m_type_entity=type_entity)
		structures_list = request.POST['structures_list']#getFieldValues()
		structures_roles = request.POST['structures_roles']
		try:
			entity.montant = float(request.POST["finances"])
		except:
			pass
		entity.save()
		r_struc = list()
		tmp_struc = list()
		r_roles = structures_roles
		r_roles = r_roles.split('\n')
		i=0

		for s in structures_list.split('|')[:-1]:
			if s not in tmp_struc:
				tmp_struc.append(s)
		for s in tmp_struc:
			r_struc.append(Structure.objects.get(id=int(s)))
		r_struc.sort(key=lambda x: x.nom)
		try:
			if edit_or_create == 'e':
				for s in entity.structures.filter():
					s.delete()
			for s in r_struc:
				if s == 0:
					pass
				else:
					r_str = StructureRole(m_structure=s,m_role=r_roles[i])
					r_str.save()
					entity.structures.add(r_str)
					i+=1
			entity.structure = entity.structures.first().m_structure#next(iter(r_struc)).m_structure
		except:
			pass

		entity.save()
		calendar = request.POST['calendar_selected']
		periode = Periode.objects.get(id=int(request.POST['calendar_periode']))
		if edit_or_create == 'e' and calendar != "#":
			plani_tche = TachePlannify.objects.filter(m_tache=entity)
			for p in plani_tche:
				p.delete()
		if calendar != "#":
			plani_tche = TachePlannify(m_tache=entity,m_planify=calendar,m_periode=periode)
			plani_tche.save()
			set_pv_tp(plani_tche)
	else:
		if edit_or_create == 'e':
			edit_id = request.POST['edit_id']
			entity = Entity.objects.get(id=int(edit_id))
			entity.m_value_fields=fields_value
			entity.m_type_entity=type_entity
		else:
			entity = Entity(m_value_fields=fields_value,m_type_entity=type_entity)
		entity.save()
	try:
		sup_entity = request.POST['sup_entity']
	except:
		sup_entity = None
	#relations_entities
	if sup_entity != None:
		sup_entity = Entity.objects.get(id=int(sup_entity))

		if edit_or_create == 'e':
			delete_hierachie = EntityHierachie.objects.filter(m_sub_entity=entity).first()
			if delete_hierachie != None:
				delete_hierachie.delete()
		entity_hierachie = EntityHierachie(m_sub_entity=entity,m_sup_entity=sup_entity)
		entity_hierachie.save()

	#Image de Couverture
	try:
		entity.m_pic_represented = request.FILES["cover_img"]
		entity.save()
	except:
		pass

	i_f = 0
	fields_name = entity.m_type_entity.fields()
	for f in entity.m_type_entity.type_fields():
		if f in ['file','image']:
			try:
				eF = EntityFile(m_entity=entity,m_field=f,m_file=request.FILES[fields_name[i_f]]) 
				eF.save()
				entity.set_value(fields_name[i_f],str(eF.id))
			except:
				entity.set_value(fields_name[i_f],str("Aucun Fichier"))
			entity.save()
		i_f+=1
	base_val = request.POST["base_val"]

	#Enumerations Values
	split_extras1(entity) # Clean the Error Files

	if base_val not in ['',' ','0',None]:
		response = "/gestionnaire/"+str(hierachie-1)+"/"+str(base_val)+"/"
	else:
		response = "/gestionnaire/"+str(hierachie)+"/"
	response = redirect(response)
	return response

def save_gestion(request):
	context = basis(request)
	generator = request.POST['generator']
	edit_or_create = request.POST['edit_or_create']
	try:	
		r_redirect = request.POST['redirect']
	except:
		pass
	if generator == 'i':
		r_sigle = request.POST['sigle']
		r_nom = request.POST['nom']
		r_image = request.FILES['image']
		institution = Institution(sigle=r_sigle,nom=r_nom,img=r_image)
		institution.save()
		response = "/gestionnaire/i/"
	elif generator == 'eD':
		r_nom = request.POST['nom']
		#r_fields_type = request.POST['fields_type']
		#r_fields = request.POST['fields']
		r_domain_type = request.POST['domain_type']
		r_value_type = request.POST['value_type']
		r_aggregation_type = request.POST['aggregation_type']
		r_description = request.POST['description']
		try:
			r_null_conserv = request.POST['null_conserv']
		except:
			r_null_conserv = 0
		try:
			r_fill_valid = request.POST['fill_valid']
		except:
			r_fill_valid = 0
		try:
			r_logo = request.FILES['logo']
		except:
			r_logo = None
		r_default_value = request.POST["default_value"]

		dE = DataElement(m_name = r_nom)
		if r_logo != None:
			m_logo=r_logo
		dE.m_domain_type = r_domain_type
		dE.m_value_type = r_value_type
		dE.m_aggregation_type = r_aggregation_type
		dE.m_description = r_description

		try:
			if int(r_null_conserv) == 1:
				dE.is_zero_collect = True
		except:
			dE.is_zero_collect = False
		try:
			if int(r_fill_valid) == 1:
				if request.POST['default_value'] == None:
					tmp = 0
				else:
					tmp = request.POST['default_value']
				dE.m_default_value = int(tmp)
		except:
			dE.m_default_value = None
		actual_institution = context['actual_institution']
		dE.m_institution = actual_institution
		dE.save()
		response = "/dataelts/"
	elif generator == 'a0':
		r_user = User.objects.get(id=int(request.POST['user']))
		r_message = request.POST['message']
		a = Assistance(m_user=r_user,m_message=r_message)
		a.save()
		request.session['assistance'] = 1
		response = "/assistance/"
	elif generator == "str":
		actual_institution = context['actual_institution']
		r_value = request.POST['value']
		actual_institution.default_struc_name = r_value
		actual_institution.save()
		response = "/structures/"
	elif generator == "p2":
		r_nom = request.POST['nom']
		r_prenom = request.POST['prenom']
		r_mail = request.POST['mail']
		r_tel = request.POST['tel']
		personnel_saved = Personnel.objects.filter(mail = r_mail).first()
		try:
			r_img = request.FILES['photo']
		except:
			if edit_or_create != 'e':
				r_img = OperaFile.objects.filter(m_name="USR").first().m_file
			else:
				r_img = None
		if personnel_saved == None:
			tes_none = (User.objects.filter(email = r_mail).first())
			if tes_none != None:
				try:
					personnel_saved = tes_none.personnel
				except:
					personnel_saved = Personnel(bd_user=tes_none,nom=r_nom,prenom=r_prenom,mail=r_mail,photo=r_img,actual_institution=context['actual_institution'])
					personnel_saved.save()

		try:
			r_structure = request.POST['Structure']
		except:
			r_structure = '0'
		if r_structure != '0':
			r_structure = Structure.objects.get(id=int(r_structure))
		else:
			r_structure = None
		r_role = request.POST['Fonction']
		r_role = Role.objects.get(id=int(r_role))
		edit_or_create = request.POST['edit_or_create']
		if  edit_or_create != 'e':
			if personnel_saved == None:
				import random
				password = ""
				for i in range(0,8):
					password += str(random.randint(0,9))
				usn = str(password) + str(User.objects.count()+2)
				r_bd_user = User(username=usn,email=r_mail)
				subject = "Nouveau Compte Opera +"
				message_context = {
					'password':password,
					'name':r_nom+""+r_prenom
				}
				message = render_to_string('webpages/ctn_bpf/mails/new_personnel.html',message_context)
				email = r_mail
				email_from = settings.EMAIL_HOST_USER
				recipient_list = [email,]
				msg = EmailMessage(subject, message, email_from, recipient_list)
				msg.content_subtype = 'html'
				try:
					msg.send()
					r_bd_user.set_password(password)
				except:
					r_bd_user.set_password("user1234")
				#r_bd_user.set_password('User'+password)
				r_bd_user.save()
				personnel = Personnel(nom=r_nom,prenom=r_prenom,mail=r_mail,photo=r_img,actual_institution=context['actual_institution'])
				personnel.bd_user = r_bd_user
			else:
				personnel = personnel_saved
		else:
			edit_id = request.POST['edit_id']
			if personnel_saved == None:
				personnel = Personnel.objects.get(id=int(edit_id))
			else:
				personnel = personnel_saved
			personnel.nom=r_nom
			personnel.prenom=r_prenom
			personnel.mail=r_mail
			personnel.bd_user.email =r_mail
			personnel.m_tel = r_tel
			personnel.bd_user.save()
			if r_img != None:
				personnel.photo = r_img
		if personnel_saved == None:
			personnel.save()
		else:
			request.session['perso_saved'] = personnel_saved.id
		try:
			simple_user = request.POST['simple_user']
		except:
			simple_user = '0'
		if simple_user == '0':
			ps = Personnel_Structure(m_personnel=personnel,m_structure=r_structure)
			ps.save()
			pf = Personnel_Function.objects.filter(m_personnel=personnel,m_institution=context['actual_institution']).first()
			if pf == None:
				pf = Personnel_Function(m_personnel=personnel,m_role=r_role,m_institution=context['actual_institution'])
			else:
				pf.m_role = r_role
			pf.save()
		else:
			entity = Entity.objects.get(id=int(simple_user))
			pf = Personnel_Function.objects.filter(m_personnel=personnel,m_institution=context['actual_institution']).first()
			if pf == None:
				pf = Personnel_Function(m_personnel=personnel,m_role=r_role,m_institution=context['actual_institution'])
			pf.m_entity = entity
			pf.save()

			ps = Personnel_Function.objects.filter(m_personnel=personnel,m_institution=context['actual_institution']).first()			
			ps = Personnel_Structure(m_personnel=personnel,m_structure=r_structure)
			ps.save()
		response = "/personnels/"
	elif generator == "r":#Role
		r_nom = request.POST['nom']
		r_description = request.POST['description']
		r_permission = request.POST['permission']
		r_institution = Institution.objects.get(id=int(request.POST['institution']))
		r_ros_click = request.POST["ros_click"]

		if int(r_ros_click) in [1,2] :
			r_permission = "-1"

		if r_permission == '-1':
			r_permission = 0
		else:
			permissions_hierachie = InsitutionEntities.objects.filter(m_institution=r_institution).last().m_hierachie
			if (permissions_hierachie+1) >= int(r_permission):
				r_permission = 0#(permissions_hierachie+1) - int(r_permission)
			else:
				r_permission = int(r_permission)
		if  edit_or_create == 'c':
			role = Role(actual_institution=r_institution,nom=r_nom,description=r_description,permissions=r_permission)
		else:
			edit_id = request.POST['edit_id']		
			role = Role.objects.get(id=int(edit_id))
			role.nom=r_nom
			role.description=r_description
			role.permissions=r_permission
		if int(r_ros_click) == 1:
			r_entity_administr = request.POST["permission_entity"]
			eH = InsitutionEntities.objects.filter(id=int(r_entity_administr)).first().m_entity_type
			role.m_simple_auth = eH
			entities = list()
			"""
			for e in r_entity_administr.split("#")[:-1]:
				entities.append(Entity.objects.get(id=int(e)))
			"""
			role.save()
			#role.m_entities.set(entities)
			role.m_nature = "1"
		elif int(r_ros_click) == 2:
			role.permissions = -100
			user_simple_entity = request.POST['user_simple_entity']
			role.is_simple_user = 1
			role.m_simple_auth = EntityType.objects.get(id=int(user_simple_entity))
		role.save()
		response = "/roles/"
	elif generator == "s":
		try:
			r_pic = request.FILES["logo"]
		except:
			r_pic = None
		r_nom = request.POST['nom']
		r_designation = request.POST['designation']
		r_institution = request.POST['Institution']
		r_institution = Institution.objects.filter(id=int(r_institution)).first()
		try:
			r_responsable = Personnel.objects.filter(id=int(request.POST['responsable'])).first()
		except:
			r_responsable = None
		if edit_or_create == 'e':
			edit_id = int(request.POST['edit_id'])
			structure = Structure.objects.get(id=int(edit_id))
			structure.photo = r_pic
			structure.nom = r_nom
			structure.designation=r_designation
			structure.institution=r_institution
		else:
			structure = Structure(nom=r_nom,designation=r_designation,institution=r_institution)#,responsable=r_responsable
			if r_pic != None:
				structure.photo = r_pic
		structure.save()

		if r_responsable != None:
			if edit_or_create == 'c':
				sR = StructureResponsable(m_structure=structure,m_responsable=r_responsable)
			else:
				edit_id = int(request.POST['edit_id'])
				structure = Structure.objects.get(id=int(edit_id))
				sR = StructureResponsable.objects.filter(m_structure=structure).first()
				if sR == None:
					sR =  StructureResponsable(m_structure=structure,m_responsable=r_responsable)
				else:
					sR.m_responsable = r_responsable
			sR.save()
		response = "/structures/"
	elif generator == 'd_s_1':
		if edit_or_create == "c":
			dS = DataSet()
			dS.save()
			response = "/data_sets/design/"+str(dS.id)+"/"
			form_part = False
		else:
			edit_id = request.POST["edit_id"]
			dS = DataSet.objects.get(id=int(edit_id))

			try:
				form_html = request.POST["form_design"]
				response = "/data_form/-1/0/"
				form_part = True
				for v in dS.m_dataelements.filter():
					form_html = form_html.replace("dE$"+str(v.id)+"$","<div class='variableSelector'>  <div><input class='form-control' name='D0elt"+str(v.id)+"' type='text'></div> </div>") #<div><label><small>"+str(v)+"</small></label></div>
				for v in dS.m_indicateurs.filter():
					form_html = form_html.replace("dI$"+str(v.id)+"$","<div class='indicSelector' data-id='"+str(v.id)+"'> </div>") 
				dS.m_formulaire = form_html					
			except:
				response = "/data_sets/design/"+str(dS.id)+"/"
				form_part = False
		if not form_part:
			form_name = request.POST["form_name"]
			if form_name not in [None,""]:
				dS.m_name = form_name
			dS.m_periode = request.POST["periode"]
			dS.m_sub_periode = request.POST["sub_periode"]

			"""
			r_indicateur = Indicateur.objects.get(id=int(request.POST["indicateur"]))
			dS.m_indicateur = r_indicateur
			"""
			dS.m_institution =  context["actual_institution"]
			#ephoxVariables_input = request.POST["ephoxVariables_input"]
			variables_list = request.POST["variables_list"].split("#")
			indicateurs_list = request.POST["indicateurs_list"].split("#")
			variables_set = set()
			indicateurs_set = set()

			for v in variables_list[:-1]:
				dE = DataElement.objects.get(id=int(v))
				variables_set.add(dE)

			for v in indicateurs_list[:-1]:
				dI = Indicateur.objects.get(id=int(v))
				indicateurs_set.add(dI)

			"""
			if ephoxVariables_input != "#":
				id_insert = 1
				ephoxVar = ephoxVariables_input.split("#")
				for v in ephoxVar[1:-1]:
					dE = DataElement.objects.get(id=int(v))
					dS.m_formulaire = dS.m_formulaire.replace("de$"+str(v)+"$","<div class='variableSelector'> <div><label><small>"+str(dE)+"</small></label></div> <div><input class='form-control' name='"+str(id_insert)+"' type='text'></div> </div>") 
					id_insert += 1
					variables_set.add(dE)
				dS.save()
			"""
			variables_set = list(variables_set)
			indicateurs_set = list(indicateurs_set)
			dS.m_dataelements.set(variables_set)
			dS.m_indicateurs.set(indicateurs_set)


			r_structure = request.POST["structures_list"].split("$")
			structures_set = list()
			for r in r_structure[:-1]:
				structures_set.append(Structure.objects.get(id=int(r)))
			dS.m_structures.set(structures_set)


			r_role = request.POST["roles_list"].split("$")
			roles_set = list()
			for r in r_role[:-1]:
				roles_set.append(Role.objects.get(id=int(r)))
			dS.m_roles.set(roles_set)

		dS.save()
	elif generator == 'o':
		r_m_tache_plannification = request.POST['tache_periode']
		r_tache = request.POST['tache']
		response = "/taches/"+r_tache+"/"
		r_tache = Tache.objects.get(id=int(r_tache))

		#r_code = request.POST['code']

		r_nom = request.POST['nom']
		r_perso = request.POST['perso']
		r_accountable = request.POST['accountable']
		r_consulted = request.POST['consulted']
		r_informed = request.POST['informed']
		try:
			r_role = request.POST['role']
		except:
			pass
		if r_perso != "0":
			r_perso = Personnel.objects.get(id=int(r_perso))
		else:
			r_perso = None
		if r_accountable != "0":
			r_accountable = Personnel.objects.get(id=int(r_accountable))
		else:
			r_accountable = None
		if r_consulted != "0":
			r_consulted = Personnel.objects.get(id=int(r_consulted))
		else:
			r_consulted = None
		if r_informed != "0":
			r_informed	 = Personnel.objects.get(id=int(r_informed))
		else:
			r_informed = None

		"""		try:
			r_perso = Personnel.objects.get(id=int(r_perso))
			r_accountable = Personnel.objects.get(id=int(r_accountable))
			r_consulted = Personnel.objects.get(id=int(r_consulted))
			r_informed	 = Personnel.objects.get(id=int(r_informed))
		except:
			pass"""
		try:
			r_montant = int(request.POST['montant'])
		except:
			r_montant = 0
		file_oko = None
		r_chronogr = request.POST['chronogr']
		r_who_assign = int(request.POST['who_assign'])
		r_sub_period = request.POST['sub_period']
		r_notification = request.POST['notification']
		r_priorite = request.POST['priorite']
		try:
			r_operation_aggregates = request.POST['operation_aggregates']
		except:
			r_operation_aggregates = None
		if edit_or_create == 'c':
			operation = Operation(tache=r_tache,nom=r_nom,montant=r_montant,notification=r_notification,priorite=r_priorite)
			operation.m_value = ""
			t2 = r_tache.sup_entity()
			tmp = str(r_tache.id)+"#"
			while t2 != None :
				tmp = str(t2.id)+"#"+tmp
				t2 = t2.sup_entity()
			operation.code = tmp

			if  context['actual_institution'].default_options != True:
				try:
					if r_operation_aggregates is not None:
						operations_values = r_operation_aggregates.split("|")
						i_val = 0
						for val in context['actual_institution'].operations_modules().fill_fields():
							if val["type"] in ['file','image']:
								try:
									oF = OperationFile(operation=operation,m_field=val['field'],m_file=request.FILES[val['field']+'_nam'])
									operation.save()
									oF.save()
								except:
									pass
							operation.m_value+= str(operations_values[i_val]) + "|" #str(operations_values[i_val]) + "|"
							i_val+=1
					else:
						operation.m_value = r_operation_aggregates
				except:
					pass
				operation.m_value += " "
			else:
				try:
					file_oko = request.FILES['file_oko']
					operation.fichier_joint = file_oko
				except:
					pass
		else:

			edit_id = request.POST['edit_id']
			operation = Operation.objects.get(id=int(edit_id))
			operation.nom=r_nom
			operation.montant=r_montant
			operation.notification=r_notification
			operation.priorite=r_priorite
			if r_operation_aggregates is None:
				for val in context['actual_institution'].operations_modules().fields_rapported()[:-1]:
					operation.m_value+= " " + "|"
			else:
				operation.m_value = r_operation_aggregates
		operation.m_tache_plannification = r_m_tache_plannification
		# Add Institution to Operation
		operation.m_institution = context["actual_institution"]

		list_operations = list()
		if r_who_assign == 0:
			if r_perso != "0":
				operation.personnel=r_perso
			if r_accountable != "0":
				operation.accountable = r_accountable
			if r_consulted != "0":
				operation.consulted = r_consulted
			if r_informed != "0" :
				operation.informed = r_informed
			list_operations.append(operation)
		elif r_who_assign == 1:
			role = Role.objects.get(id=int(r_role))
			for perso in role.persos():
				operation.personnel=perso.m_personnel
				list_operations.append(operation)
		else:
			list_operations.append(operation)

		for o in list_operations:
			o.save()
			if edit_or_create == 'e':
				op = OperationPeriode.objects.filter(m_operation=o).first()
				if op != None :
					tmp_chrono = SubPeriode.objects.filter(id=int(r_sub_period)).first()
					if tmp_chrono != None :
						op.m_chronogramme= tmp_chrono					
					op.m_desc_realisation=r_chronogr
					op.save()
				else:
					op = OperationPeriode(m_operation=o,m_chronogramme=SubPeriode.objects.get(id=int(r_sub_period)),m_desc_realisation=r_chronogr)
					op.save()
			else:
				op = OperationPeriode(m_operation=o,m_chronogramme=SubPeriode.objects.get(id=int(r_sub_period)),m_desc_realisation=r_chronogr)
				op.save()
		subject = "Attribution - "+str(operation.institution().operations_name())
		email_from = settings.EMAIL_HOST_USER
		try:
			raci_roles = [operation.personnel,operation.accountable,operation.consulted,operation.informed]
			all_emails = list()
			msg_emails = list()
			i_r = 0
			for r in raci_roles:
				i_r +=1
				if r is not None:
					tmp_context = {
						'operation':operation,
						'personnel':r,
						'tache':operation.tache,
						'institution':operation.institution()
					}
					if i_r == 2:
						tmp_context['role'] = 'A'
					elif  i_r == 3:
						tmp_context['role'] = 'C'

					elif i_r == 4:
						tmp_context['role'] = 'I'
					else:
						tmp_context['role'] = 'Responsable'
					message = render_to_string('webpages/ctn_bpf/mails/new_operation.html',tmp_context)
					#message2 = (subject, message, email_from, [r_role.m_personnel.mail])
					message2 = EmailMessage(subject, message, email_from, [r.mail,])
					message2.content_subtype = 'html'

					msg_emails.append(message2)
					try:
						message2.send()
					except:
						pass
			#recipient_list = all_emails
			#send_mass_mail((msg_emails), fail_silently=False)
		except:
			message_context = {
				'operation':operation,
				'personnel':operation.personnel,
				'tache':operation.tache,
				'institution':operation.institution()
			}
			message = "<html><head></heady><body><b>Vous avez une Opération qui vous a ete attribué</b></body></html>"
			message = render_to_string('webpages/ctn_bpf/mails/new_operation.html',message_context)
			if r_perso != '0':
				email = r_perso.mail
				recipient_list = [email,]
				msg = EmailMessage(subject, message, email_from, recipient_list)
				msg.content_subtype = 'html'
				try:
					if file_oko != None:
						msg.attach(file_oko.name, file_oko.read(), file_oko.content_type)
					msg.send()
				except:
					pass
		"""
		try:
			send_mail( subject, message, email_from, recipient_list, fail_silently=False)	
			msg = EmailMessage(subject, message, email_from, recipient_list)
			msg.content_subtype = 'html'
			msg.send()
		except:
			pass
		"""
	elif generator == 'w':
		r_nom = request.POST['nom']
		r_prenom = request.POST['prenom']
		r_mail = request.POST['mail']
		r_password = request.POST['password']
		r_username = User.objects.count()+1
		try:
			r_user = User(username=r_username,email=r_mail)
			r_user.set_password(r_password)
			r_user.save()
		except:
			r_user = User(username='ngb'+str(r_username+1000),email=r_mail)
			r_user.set_password(r_password)
			r_user.save()

		# Code generator
		code = ""
		import random
		for i in range(6):
			code += str(random.randint(0,9))
		#code = "000111"
		owner = Owner(m_user=r_user,m_code = code)
		owner.save()
		personnel = Personnel(nom=r_nom,prenom=r_prenom,mail=r_mail,bd_user=r_user)
		personnel.photo = OperaFile.objects.filter(m_name="USR").first().m_file
		personnel.save() 
		subject = "Création d'une Institution Opera +"
		message = " Bonjour, utilisez ce code pour renseigner une Institution au sein d'Opera "+str(code) 
		email = r_mail
		email_from = settings.EMAIL_HOST_USER
		recipient_list = [email,]
		try:
			send_mail( subject, message, email_from, recipient_list, fail_silently=False)
		except:
			pass # No cconnexion
		response = "/log_account/"
		request.session['new_user'] = 1
	elif generator == "i2":
		id_e = int(request.POST["entity_id"])
		entity = Entity.objects.get(id=id_e)
		for i in entity.get_indicateurs():
			tmp_per = request.POST["period"+str(i.id)]
			tmp_num = request.POST["numer"+str(i.id)]
			tmp_field = request.POST["id"+str(i.id)]
			tmp_field = DataElement.objects.filter(id=int(tmp_field)).first() 
			#i.m_values = str(tmp_per)+"#"+str(tmp_num)+"\n" + str(i.m_values)
			iV = IndicateurVal(m_indicateur=i,m_periode=tmp_per,m_valeur=tmp_num,m_numerateur=tmp_field)
			iV.save()

		entity.is_rapported = True
		entity.save()
		response = "/chaine_indicateurs/"
		context['indique'] = True
	elif generator == "dSv":
		r_dataset = DataSet.objects.get(id=int(request.POST["dSv_id"]))
		r_user = request.user.personnel
		r_variables = r_dataset.m_dataelements
		r_values = request.POST["variables_value"].split("#")
		r_values_names = request.POST["variables_names"].split("#") 
		r_values_dict = dict()

		for v in r_variables.filter():
			r_values_dict["D0elt"+str(v.id)] = None

		for i in range(len(r_values)):
			r_values_dict[r_values_names[i]] = r_values[i]

		r_structures = [request.POST["struc_selec"]]
		r_period1 = request.POST["period1_saisie"]
		r_period2 = request.POST["period2_saisie"]
		entity = DataSetValue(m_dataset = r_dataset,m_user = r_user,m_period_value = r_period1,m_sub_period_value = r_period2)
		entity.save()

		i = 0
		for v in r_variables.filter():
			dt = DSet_DElt(m_dataelement=v,m_dataset_value=entity,m_value=r_values_dict["D0elt"+str(v.id)])#r_values[i])
			dt.save()
			i+=1
		for v in r_structures:
			stru = Structure.objects.get(id=int(v))
			entity.m_structures.add(stru)
		entity.save()
		response = "/data_form/"+str(r_dataset.id)+"/"+str(0)+"/"
	elif generator == "ieD":
		formula = request.POST["formule"]
		indicateur = Indicateur.objects.get(id=int(request.POST["indicateur"]))
		indicateur.m_datalets_calcul = formula
		indicateur.save()
		response = "/dataelts/indic/"
	elif generator == "pass":
		password = request.POST["password"]
		user = request.user
		user.set_password(password)
		user.save()
		response = "/profile/"
	elif generator == "ind_va":
		entity = EntityType.objects.get(id=int(request.POST["entity_ind_id"]))
		entity.indicateur_fields = request.POST["ind_val"]
		entity.save()
		response = "/configurations/"
	elif generator == "cOi":
		entity = Tache.objects.get(id=request.POST["configOp_id"])
		tA = TacheAggregate.objects.filter(m_tache = entity).first()
		if tA == None:
			tA = TacheAggregate(m_tache=entity)
		i=1
		for i1 in context["actual_institution"].operations_modules().fields():
			if request.POST["fiel1"+str(i)] not in ["#",""," "]:
				tA.m_values1 += request.POST["fiel1"+str(i)]+"§"
			else:
				tA.m_values1 += "#"+"§"
		i=1
		for i1 in context["actual_institution"].operations_modules().fill_fields_rapp():
			if request.POST["fiel2"+str(i)] not in ["#",""," "]:
				tA.m_values2 += request.POST["fiel2"+str(i)]+"§"
			else:
				tA.m_values2 += "#"+"§"
			i+=1
		tA.save()
		response = "/taches/"+str(entity.id)
	return redirect(response)

def planifier2(request,period_id=0):
	template = "webpages/ctn_bpf/plannifier.html"
	annees = set()
	context = basis(request)
	entity = InsitutionEntities.objects.filter(m_institution=context['actual_institution']).last().m_entity_type
	tasks = entity.lines()

	#actual_period =
	
	context['searches'] = list()
	context['g_v'] = '1'
	context['institution'] = Institution.objects.last()
	if period_id != 0:
		context['actual_period'] = Institution_Periodes.objects.get(id=int(period_id))
	else:
		period = request.user.personnel.actual_institution.default_period
		institutionPe = Institution_Periodes.objects.filter(m_institution=request.user.personnel.actual_institution,m_periode=period).first()
		context['actual_period'] = institutionPe
	context['taches'] = tasks
	context['ranges'] = ['0','1','2','3','4','5','6','7','8','9','10','11']
	return render(request,template,context)

def roles(request,search=None):
	template = "webpages/ctn_bpf/roles.html"
	fields_personnel = ['','Nom','Prenom','Adresse Mail','Structure','Fonction','']
	fields_roles = ['Role','Description','Permissions','Entités']
	personnel = Personnel.objects.filter()
	context = basis(request)
	roles = Role.objects.filter(actual_institution=context['actual_institution']).select_related('actual_institution')
	if search != None:
		roles = roles.filter(nom__contains=search)
	context['entity'] = 'Rôle'
	context['fields1'] = fields_personnel
	context['personnel'] = personnel
	context['fields'] = fields_roles
	context['lines'] = roles
	context['g_v'] = 'r'
	context['g_vs'] = 'r2'
	return render(request,template,context)

def repartir_tache(request):
	r_tache = request.POST['tache']
	r_roles_tache = request.POST['roles_tache']
	r_personnel_tache = request.POST['personnel_tache']
	roles = r_roles_tache.split("_")
	personnels = r_personnel_tache.split("_")
	r_roles = list()
	r_persos = list()
	for r in roles:
		if r != '':
			r_roles.append(Role.objects.get(id=int(r)))
	for p in personnels:
		if p != '':
			r_persos.append(Personnel.objects.get(id=int(p)))
	tache = Tache.objects.get(id=int(r_tache))
	subject = "Attribution de la Tache"
	message = " Vous avez une Tache qui vouis a ete attribué" 
	email = r_persos[0].mail
	email_from = settings.EMAIL_HOST_USER
	recipient_list = [email,]
	#send_mail( subject, message, email_from, recipient_list, fail_silently=False)	

	repartition = TacheRepartition(m_tache=tache)
	repartition.save()
	repartition.m_personnels.set(r_persos)
	repartition.m_roles.set(r_roles)
	repartition.save()
	return redirect("/gestionnaire/t/")

def modify(request,arg_val=""):
	r_personnel_id = request.POST['personnel']
	r_role_id = request.POST['role']
	personnel = Personnel.objects.get(id=int(r_personnel_id))
	role = Role.objects.get(id=int(r_role_id))
	r_institution = Institution.objects.get(id=int(request.POST['institution']))
	p_f = Personnel_Function(m_personnel=personnel,m_role=role,m_institution=r_institution)
	p_f.save()
	return redirect('/personnels/')

def save_plannify(request):
	tache_id = request.POST['calendar_tache']
	calendar = request.POST['calendar_selected']
	periode = Periode.objects.get(id=int(request.POST['calendar_periode']))
	tache = Tache.objects.get(id=int(tache_id))
	try:
		plani_tche = TachePlannify.objects.filter(m_tache__id = int(tache_id)).first()
		plani_tche.m_planify = calendar	
		plani_tche.m_periode = periode
	except:
		plani_tche = TachePlannify(m_tache=tache,m_planify=calendar,m_periode=periode)
	plani_tche.save()
	institutionPe = Institution_Periodes.objects.filter(m_institution=request.user.personnel.actual_institution,m_periode=periode)
	return redirect("/planifier/"+str(institutionPe.first().id)+"/")

#@cache_page(60 * 15)
def operations_home(request,lvl=-1,arg_structure="#",periode="#",search="#",only_not=0):
	template = "webpages/ctn_bpf/index.html"
	context = basis(request)
	if lvl == -1:
		entity = InsitutionEntities.objects.filter(m_institution=context['actual_institution']).last().m_entity_type
	else:
		entity = InsitutionEntities.objects.filter(m_institution=context['actual_institution'],m_hierachie=lvl).last().m_entity_type
	lines = entity.lines()
	tache_lvl = entity.is_tache
	if arg_structure not in ["#",'0']:
		tmp_structure = Structure.objects.get(id=int(arg_structure))
		try:
			tmp = list()
			for l in lines:
				if l.structure == tmp_structure:
					tmp.append(l)
				else:
					pass
			lines = tmp
			context['arg_structure'] = int(arg_structure)
		except:
			pass
	if periode not in ["#",'0']:
		try:
			tmp = list()
			for t in lines:
				if periode in t.plannification().table():
					tmp.append(t)
			lines = tmp
		except:
			pass
	if search != "#":
		tmp = list()
		for t in lines:
			if search in t.get_name():
				tmp.append(t)
		lines = tmp
	context['entity'] = entity
	context['sup_entity'] = entity.sup_entity(context['actual_institution'].id)
	context['lines'] = lines
	context['fields']=entity.fields()
	context['operation'] = 1
	context['personnel'] = Personnel.objects.filter()
	context['menu'] = 'o'
	context['lvl'] = lvl
	context['g_v'] = 'o'
	context['periode'] = periode
	context["tache_lvl"] = tache_lvl

	paginator_o = Paginator(lines,10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	#oeuvres_date
	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range
	return render(request,template,context)

@login_required(login_url='/log_account')
def notifications(request):
	template = "webpages/ctn_bpf/index.html"
	context = basis(request)
	entity = InsitutionEntities.objects.filter(m_institution=context['actual_institution']).select_related('m_institution').last().m_entity_type
	lines = list()
	for l in entity.lines():
		if l.progression() < 100:
			operations = l.operations()
			appd = False 
			for o in operations:
				if o.personnel == request.user.personnel:
					lines.append(l)
					break
	context['notif'] = True 
	context['entity'] = entity

	#context['lines'] = lines
	paginator_o = Paginator(lines,10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	#oeuvres_date
	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range

	context['fields']=entity.fields()
	context['personnel'] = Personnel.objects.filter()
	context['menu'] = 'o'
	context['g_v'] = 'o'
	return render(request,template,context)

@login_required(login_url='/log_account')
def alert_notifs(request,search=None,tree=None,report=0):
	context = basis(request)
	template = "webpages/ctn_bpf/alert_notifs.html"
	perso = request.user.personnel
	context['report'] = report
	repeat_mode = context["actual_institution"].repeat_mode
	if repeat_mode:
		na_class = OperationDetails
		if report == 0:
			main_operations = Operation.objects.filter(personnel=perso.id,etat='0')#.values('m_institution','code','nom','id','date_creation')
		elif report == 1:
			main_operations = na_class.objects.filter(m_operation__accountable=perso.id,etat='1')#.values('m_institution','code','nom','id','date_creation')			
		elif report == 2:
			main_operations = na_class.objects.filter(m_operation__consulted=perso.id,etat='1')#.values('m_institution','code','nom','id','date_creation')
		elif report == 3:
			main_operations = na_class.objects.filter(m_operation__informed=perso.id,etat='2')#.values('m_institution','code','nom','id','date_creation')
		elif report == 100:
			main_operations = na_class.objects.filter()
	else:
		na_class = Operation
		if report == 0:
			main_operations = na_class.objects.filter(personnel=perso.id,etat='0')#.values('m_institution','code','nom','id','date_creation')
		elif report == 1:
			main_operations = na_class.objects.filter(accountable=perso.id,etat='1')#.values('m_institution','code','nom','id','date_creation')			
		elif report == 2:
			main_operations = na_class.objects.filter(consulted=perso.id,etat='1')#.values('m_institution','code','nom','id','date_creation')
		elif report == 3:
			main_operations = na_class.objects.filter(informed=perso.id,etat='2')#.values('m_institution','code','nom','id','date_creation')
		elif report == 100:
			main_operations = na_class.objects.filter()
	bool(main_operations)
	if repeat_mode and report != 0:
		tmp = list()
		for n in main_operations:
			tmp.append(n.m_operation.id)
		main_operations = Operation.objects.filter(id__in=tmp)

	main_operations = main_operations.order_by('-date_creation')
	if tree == '1':
		entHidden = request.POST["entHidden"]
		context["entHidden"] = entHidden.split("#")
		main_operations = main_operations.filter(code__contains=entHidden)
	tmp = list()
	try:
		n = InsitutionEntities.objects.filter(m_institution=context['actual_institution']).count()
	except:
		n=0

	for i in range(n):
		tmp.append(set())


	for o in main_operations:
		if o.code != None:
			o2 = o.code.split("#")
			try:
				for i in range(n):
					tmp[i].add(o2[i])
			except:
				pass

	ents = list()
	for i in range(n):
		try:
			ents.append({
				"hierachie":i,
				'entities':Entity.objects.filter(id__in=list(tmp[i]))
			})
		except:
			pass
	context['ents'] = ents
	context['n'] = n

	main_operations2 = OperationRole.objects.filter(m_personnel=perso.id).values('m_operation')
	context['main_operations2'] = main_operations2
	#operations = perso.get_taches() #get_operations()

	results = list()
	results = list(main_operations)
	"""
	for o in operations:
		if o.progression() == 0 and o.rapported() in ['0',None] :
			results.append(o)
	"""
	paginator_o = Paginator(results,10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	#oeuvres_date
	context['menu'] = 'aN'
	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range
	context['lines'] = context['pages_o']
	return render(request,template,context)	

def save_rapport(request):
	context = basis(request)
	r_operation = Operation.objects.get(id=int(request.POST['operation_id']))
	if context["actual_institution"].repeat_mode == True:
		r_operation = OperationDetails(m_operation=r_operation)
		r_operation.personnel = request.user.personnel
		r_operation.save()
		fil_class = OperationDetailsFile
	else:
		fil_class = OperationFile
	try:
		r_commentaire = request.POST['operation_comm']
	except:
		r_commentaire = None
	try:
		r_fichier = request.FILES['operation _fichier']
	except:
		r_fichier = None
	if context['actual_institution'].default_options != True:
		rapport_input = request.POST['rapport_input']
		rapport_values =  request.POST['rapport_values']
		try:
			aggregates = context['actual_institution'].operations_modules().type_fields_rapported()
			aggs_fields = context['actual_institution'].operations_modules().fields_rapported()
		except:
			aggregates = list()
		i = 1
		for a in aggregates:
			if a == 'file':
				delet = fil_class.objects.filter(m_field=aggs_fields[(i-1)],operation=r_operation)
				delet.delete()
				oF = fil_class.objects.create(m_field=aggs_fields[(i-1)],operation=r_operation)
				try:
					oF.m_file=request.FILES['file_r'+str(i)]
				except:
					pass
				oF.save()
			i+=1
		r_operation.m_value_reported = rapport_values
		r_operation.etat = '1'
		r_operation.date_rapported = datetime.datetime.now()
		r_operation.m_commentaire = r_commentaire
		r_operation.save()
	else:
		r_operation.etat = '1'
		rapport_input = request.POST['rapport_input']
		if rapport_input != 'c':
			rapport = OperationRapport(operation=r_operation,commentaire=r_commentaire)
		else:
			#r_nom = request.POST['operation_nom']
			rapport = OperationRapport(piece_jointe=r_fichier,operation=r_operation,commentaire=r_commentaire)
			#r_operation.etat = '1' #nom_piece_jointe=r_nom
			periode = r_operation.periodes()
			desc_tmp = periode.desc_split()
			desc_tmp.append("")
			index = 0
			for i in desc_tmp:
				if i == '9':
					pass
				elif i == '0':
					desc_tmp[index] = '1'
					rapport.period = index
					rapport.save()
					request.session['new_rapport'] = 1
					break
				elif i == '1':
					request.session['have_to_done'] = 1
					break
				index+=1
			desc_tmp = "_".join(desc_tmp)

			periode.m_desc_realisation = desc_tmp
			periode.save()
	try:
		finances = request.POST["finances"]
		r_operation.montant2 = int(finances)
	except :
		r_operation.montant2 = 0
	r_operation.save()
	request.session['new_rapport'] = 1
	try:
		operation = r_operation 
		peA = None
		tmps = [operation.accountable,operation.consulted]
		message_context1 = {
			'operation':operation,
			'role':'A',
			'commentaires':r_commentaire,
			'lien':"/decision/o/"+str(operation.id)+"/",
			'institution':operation.institution()
		}
		message_context2 = {
			'operation':operation,
			'role':'C',
			'commentaires':r_commentaire,
			'lien':"/decision/o/"+str(operation.id)+"/",
			'institution':operation.institution()
		}

		subject = str(operation) + " - attente de validation"
		message1 = render_to_string('webpages/ctn_bpf/mails/rapport_operation.html',message_context1)
		message2 = render_to_string('webpages/ctn_bpf/mails/rapport_operation.html',message_context2)
		recipient_list1 = [operation.accountable.bd_user.email,]
		if operation.consulted != None:
			recipient_list2 = [operation.consulted.bd_user.email,]
		else:
			recipient_list2 = list()
		email_from = settings.EMAIL_HOST_USER
		msg1 = EmailMessage(subject, message1, email_from, recipient_list1)
		msg1.content_subtype = 'html'
		msg2 = EmailMessage(subject, message2, email_from, recipient_list2)
		msg2.content_subtype = 'html'
		try:
			if r_fichier != None:
				msg1.attach(r_fichier.name, r_fichier.read(), r_fichier.content_type)
				msg2.attach(r_fichier.name, r_fichier.read(), r_fichier.content_type)
			msg1.send()
			msg2.send()
		except:
			pass
	except:
		pass
	response = redirect('/operations/')
	return response

def assign_supervisor(request):
	tache = Tache.objects.get(id=int(request.POST["assign"]))
	supervisor = Personnel.objects.get(id=int(request.POST['perso']))
	tache.superviseur = supervisor
	tache.save()
	return redirect('/gestionnaire/t/')

def valid_rapport(request):
	opera_valider_id = request.POST['opera_valider_id']
	operation = Operation.objects.get(id=int(opera_valider_id))
	try:
		operation_rapport = request.POST["operation_rapport"]
		operation_rapport = OperationDetails.objects.get(id=int(operation_rapport))
		operation_rapport.etat = "2"
		operation_rapport.save()
	except:
		operation.etat = '2'

	index = 0
	# if defaulted configurations
	try:
		periode = operation.periodes()
		desc_tmp = periode.desc_split()
		desc_tmp.append("")
		for i in desc_tmp:
			if i in ['9','0']:
				pass
			elif i == '1':
				desc_tmp[index] = '2'
				request.session['validation_done'] = 1
				break
			index+=1
		desc_tmp = "_".join(desc_tmp)
		periode.m_desc_realisation = desc_tmp
		periode.save()
	except:
		pass
	operation.save()

	subject = " Evolution "+str(operation)
	message_context = {
		'operation':operation,
	}
	message = render_to_string('webpages/ctn_bpf/mails/inform_evolution.html',message_context)

	email_from = settings.EMAIL_HOST_USER
	recipient_list = [operation.personnel.bd_user.email,]
	if operation.informed != None :
		recipient_list.append(operation.informed.bd_user.email)
	msg = EmailMessage(subject, message, email_from, recipient_list)
	msg.content_subtype = 'html'
	try:
		msg.send()
		send = '0'
	except:
		send = '1'

	return redirect('/operations/')

def in_valid_rapport(request):
	opera_invalider_id = request.POST['opera_invalider_id']
	commentaire = request.POST["opera_invalider_comment"]
	operation = Operation.objects.get(id=int(opera_invalider_id))
	operation.etat = '0'
	periode = operation.periodes()
	desc_tmp = periode.desc_split()
	desc_tmp.append("")
	try:
		operations_rapport = request.POST["operation_rapport"]
		operation_rapport = OperationDetails.objects.get(id=int(operation_rapport))
		operation_rapport.etat = "0"
		operation_rapport.delete() #:save()
	except:
		pass
	index = 0
	for i in desc_tmp:
		if i in ['1']:
			desc_tmp[index] = '0'
			request.session['validation_done'] = 1
		index+=1
	desc_tmp = "_".join(desc_tmp)
	periode.m_desc_realisation = desc_tmp
	periode.save()
	operation.save()
	message_context = {
		'operation':operation,
		'commentaire':commentaire
	}

	subject = " Rapport non Valide"
	message = render_to_string('webpages/ctn_bpf/mails/operation_invalid.html',message_context)
	email = operation.personnel.bd_user.email
	email_from = settings.EMAIL_HOST_USER
	recipient_list = [email,]
	msg = EmailMessage(subject, message, email_from, recipient_list)
	msg.content_subtype = 'html'
	try:
		msg.send()
		send = '0'
	except:
		send = '1'

	return redirect('/operations/')

def delete(request):
	id_entity = request.POST['id_entity']
	generator = request.POST['generator']
	try:
		force = False
		if generator == 'o':
			entity = Operation.objects.get(id=int(id_entity))
			response = redirect('/taches/'+str(entity.tache.id)+'/')
		elif generator == 'eD':
			entity = DataElement.objects.get(id=int(id_entity))
			response = redirect('/dataelts/')
		elif generator == 'p2':
			entity = Personnel.objects.get(id=int(id_entity))
			response =redirect('/personnels/')
		elif generator == 'r':
			entity = Role.objects.get(id=int(id_entity))
			response = redirect('/roles/')	
		elif generator == 's':
			entity = Structure.objects.get(id=int(id_entity))
			response = redirect('/structures/')	
		elif generator == 'e':
			entity = InsitutionEntities.objects.get(id=int(id_entity))
			hierachie = entity.m_hierachie
			institution = entity.m_institution
			to_decaler = InsitutionEntities.objects.filter(m_hierachie__gte=hierachie,m_institution=institution)
			for d in to_decaler:
				d.m_hierachie -= 1
				d.save()
			response = redirect('/configurations/')	
			entity = entity.m_entity_type
		elif generator == 'i2':
			entity = Indicateur.objects.get(id=int(id_entity))
			response = redirect('/evaluer/'+str(entity.m_enti.m_type_entity.hierachie()))	
		elif generator == 'iF3':
			entity = IndicateurVal.objects.get(id=int(id_entity))
			sup = entity.m_indicateur.m_enti
			try:
				s_sup = sup.sup_entity().id
				sup_hierachie = sup.m_type_entity.hierachie()

				response = redirect('/data_form/'+str(sup_hierachie)+'/'+str(s_sup)+'/')
			except:
				response = redirect('/data_form/-1/0/')
		elif generator == 'y':
			entity = Institution_Periodes.objects.get(id=int(id_entity))
			response = redirect('/configurations/')	
		elif generator == 'z':
			entity = SubPeriode.objects.get(id=int(id_entity))
			response = redirect('/configurations/')	
		elif generator == 'p2_RACI':
			entity = PersonnelRACI.objects.get(id=int(id_entity))
			response = redirect('/personnels_raci/')	
		elif generator == "dSV":
			entity = DataSet.objects.get(id=int(id_entity))
			response = redirect("/data_form/-1/0/")
		else:
			hierachie = int(request.POST['hierachy'])
			try:
				base_val = int(request.POST["base_val"])
			except:
				base_val = "0"
			if base_val not in ['','0',None]:
				response = "/gestionnaire/"+str(hierachie-1)+"/"+str(base_val)+"/"
			else:
				response = "/gestionnaire/"+str(hierachie)+"/"

			entity = Entity.objects.get(id=int(id_entity))
			response = redirect(response)
		entity.delete()
	except ProtectedError:
		# render the template with your message in the context
		# or you can use the messages framework to send the message:
		template = "webpages/ctn_bpf/error_delete.html"
		context = basis(request)
		entity = Entity.objects.filter(id=int(id_entity)).first()
		if entity != None:
			context["entity"] = entity
			tmp_hierachie = entity.m_type_entity.hierachie()
			context['hierachie'] = tmp_hierachie			
			if entity.m_type_entity.is_tache == True:
				subs = context["actual_institution"].operations_name
			else:
				tmp_hierachie += 1
				subs = InsitutionEntities.objects.filter(m_institution=context["actual_institution"],m_hierachie=tmp_hierachie).first()
			context['subs'] = subs
			context['element'] = 1
		response = render(request,template,context)
	return response

def ajax_lines(request):
	type_search = request.GET.get('type_search')
	value_search= request.GET.get('value_search')
	sub_search = request.GET.get('sub_search')
	results = list()
	lines = list()
	progressions = list()
	lines_count = 0

	if value_search != "|": # La Recherche se fait à partir de la Valeur de la ZOne de Texte
		results = objets[type_search].objects.filter(nom__contains=value_search) 		
	else : # La Recherche se fait à partir d'un Filtre
		pass
	# Allez, on recupere les résultats
	if type_search == 'o':
		for r in results:
			progressions.append(r.progression())
			lines.append(r.nom+"|"+str(r.personnel)+"|"+str(r.montant)+"|"+r.semaines+"|")	

	lines_count = results.count()
	data = {
		'progressions':progressions,
		'lines':lines,
		'lines_count':lines_count
	}
	return JsonResponse(data,safe=False)

@login_required(login_url='/log_account')
def configurations(request):
	template = "webpages/ctn_bpf/configurations.html"
	context = basis(request)
	context['institution'] = request.user.personnel.actual_institution
	context['menu'] = 'c'
	context['g_v'] = 'e'
	context['basis_periodes'] = Periode.objects.filter(m_initial=True)
	return render(request,template,context)

def profile(request):
	template = "webpages/ctn_bpf/profile.html"
	context = basis(request)
	context['institution'] = context['actual_institution']
	context["personnel"] = request.user.personnel
	return render(request,template,context)

def filter_op_search(request):
	search = request.POST['search']
	return filter_op(request,search)

def filter_op(request,search="#"):
	try:
		niveau = int(request.POST['niveau'])
		periode = request.POST['periode']
		structure = request.POST['structure']
	except:
		niveau = -1
		periode = "#"
		structure = "#"
	try:
		only_not = int(request.POST["only_not"])
	except:
		only_not = 0
	return operations_home(request,niveau,structure,periode,search,only_not)

def notifs(request):
	user_id = request.GET.get('value')
	insti_id = request.GET.get('institution')
	actual_institution = Institution.objects.get(id=int(insti_id))	
	perso = Personnel.objects.get(bd_user__id=int(user_id))
	if actual_institution.repeat_mode == False:
		operations1 = list()
		operations = Operation.objects.filter(personnel=perso)
		operations_report =  Operation.objects.filter(accountable=perso,etat='1')
		count_is_consulted = Operation.objects.filter(consulted=perso,etat='1').count() 
		count_is_informed = Operation.objects.filter(informed=perso,etat='2').count()
	else:
		operations1  = Operation.objects.filter(personnel=perso)
		operations = OperationDetails.objects.filter(m_operation__personnel=perso)
		operations_report =  OperationDetails.objects.filter(m_operation__accountable=perso,etat='1')
		count_is_consulted = OperationDetails.objects.filter(m_operation__consulted=perso,etat='1').count() 
		count_is_informed = OperationDetails.objects.filter(m_operation__informed=perso,etat='2').count()

	# General_Results
	nb_taches = 0
	nb_have_rapported = 0
	nb_is_done = 0
	nb_have_to_do = 0
	nb_observations = 0

	nb_have_rapported2 = 0
	nb_is_done2 = 0
	nb_have_to_do2 = 0
	nb_observations2 = 0
	if True:
		for o in operations1:
			if o.etat == '0':
				nb_have_to_do += 1
				nb_taches+=1
				if o.institution() == actual_institution:
					nb_have_to_do2 += 1			
		for o in operations:
			if o.etat == '1':
				nb_have_rapported +=1
				if o.institution() == actual_institution:
					nb_have_rapported2 += 1
			else :
				nb_is_done +=1
				if o.institution() == actual_institution:
					nb_is_done2 += 1

		for o in operations_report:
			nb_observations += 1
			if o.institution() == actual_institution:
				nb_observations2 += 1

	data = {
		'result':nb_taches,
		'have_to_done':nb_have_to_do,
		'is_done':nb_is_done,
		'have_rapported':nb_have_rapported,
		'have_to_done2':nb_have_to_do2,
		'is_done2':nb_is_done2,
		'have_rapported2':nb_have_rapported2,
		'nb_observations':nb_observations,
		'nb_observations2':nb_observations2,
		'count_is_consulted':count_is_consulted,
		'count_is_informed':count_is_informed
	}
	#entities = institution.get_entities()
	indicateurs_all = Indicateur.objects.filter(m_institution=actual_institution).count()
	data["indi_total"] = indicateurs_all
	return JsonResponse(data)

def indicateurs_ajax(request):
	actual_institution = request.GET.get("institution")
	actual_year = request.GET.get("actual_year")

	try:
		entity_type = int(request.GET.get("entity_type"))
		type_indic = request.GET.get("type_indic")
	except:
		entity_type = None

	try:
		id_entity = int(request.GET.get("id_entity"))
		id_entity = Entity.objects.get(id=id_entity)
	except:
		id_entity = None



	if entity_type == None:
		if id_entity != None:
			indicateurs_all = Indicateur.objects.filter(m_enti=id_entity)	
		else:
			indicateurs_all = Indicateur.objects.filter(m_institution=actual_institution)
		nb_all = indicateurs_all.count()	
		indicateurs_renseignes = list()
		nb_renseignes = 0

		for i in indicateurs_all:
			if i.actu_value != None :
				indicateurs_renseignes.append(i)
				nb_renseignes += 1

		indicateurs_values = list()
		cibles = list() 
		for i in indicateurs_renseignes:
			cibles.append(i.get_cibles(actual_year))
			indicateurs_values.append(i.actu_value())
		data = {
			'all':nb_all,
			'nb_renseignes':nb_renseignes,
			'cibles':cibles,
			'indicateurs_values':indicateurs_values
		}
	elif type_indic == "F":
		if id_entity == None:
			eT = EntityType.objects.filter(id=entity_type).first()
			entities = eT.lines()
		else:
			eT = id_entity.m_type_entity
			entities = id_entity.sub_entities()
		resul1 = list()
		resul2 = list()
		for e in entities:
			try:# it may be Operation
				operations = e.operations()
				if eT.is_tache == False:
					taches = e.taches()
				else:
					taches = [e]
				tmp = 0
				tmp2 = 0
				for t in taches:
					if t.montant != None:
						tmp += int(t.montant)
				for o in operations:
					tmp2 += int(o.montant2)
				resul1.append(tmp)
				resul2.append(tmp2)
			except:
				pass

		data = {
			'list_montant1':resul1,
			'list_montant2':resul2
		}
		entq = list()
		entq_id = list()
		for e in entities:
			entq.append(str(e))
			entq_id.append(str(e.id))
		data['entities'] = entq
		data["entities_id"] = entq_id
	else:
		if id_entity == None:
			eT = EntityType.objects.filter(id=entity_type).first()
			entities = eT.lines()
		else:
			entities = [id_entity]
		indicateurs_all = Indicateur.objects.filter(m_enti__in=entities)
		ens = dict()
		ens_good = dict()
		ens_bad = dict()
		nbE = indicateurs_all.count()
		for i in entities:
			ens[str(i.id)]=0
			ens_good[str(i.id)]=0
			ens_bad[str(i.id)]=0

		for i in indicateurs_all:
			ens[str(i.m_enti.id)]+=1
			try:			
				if int(i.get_cibles(actual_year)) > int(i.actu_value()):
					ens_bad[str(i.m_enti.id)] += 1
				else:
					ens_good[str(i.m_enti.id)] += 1
			except:
				pass

		if nbE > 0:
			for i in entities:
				ens[str(i.id)]=ens[str(i.id)]#*100/nbE
				ens_good[str(i.id)]=ens_good[str(i.id)]#*100/nbE
				ens_bad[str(i.id)]=ens_bad[str(i.id)]#*100/nbE

		list_ens = list()
		list_ens_good = list()
		list_ens_bad = list()
		for i in entities:
			list_ens.append(ens[str(i.id)])
			list_ens_good.append(ens_good[str(i.id)])
			list_ens_bad.append(ens_bad[str(i.id)])
		data = {
			'list_ens':list_ens,
			'list_ens_good':list_ens_good,
			'list_ens_bad':list_ens_bad
		}
		entq = list()
		entq_id = list()
		for e in entities:
			entq.append(str(e))
			entq_id.append(str(e.id))
		data['entities'] = entq
		data["entities_id"] = entq_id
	return JsonResponse(data,safe=False)

def institutions(request,search=None):
	template = "webpages/ctn_bpf/institution.html"
	context = basis(request)
	institutions1 = list()
	structures = Personnel_Structure.objects.filter(m_personnel=request.user.personnel)
	for s in structures :
		if s.m_structure.institution not in institutions1:
			institutions1.append(s.m_structure.institution)
	for i in Institution.objects.filter(owner__m_user__id=request.user.id):
		if i not in institutions1:
			institutions1.append(i)
	if search != None:
		tmp = institutions1
		institutions1 = list()
		for i in tmp:
			if search in i.nom or search in i.sigle:
				institutions1.append(i)		
	institutions1 = sorted(institutions1, key= lambda t: t.sigle)
	paginator_o = Paginator(institutions1,12)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
		#oeuvres_date
	context['institutions1']=elements_page
	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range
	context['menu'] = 'i'
	return render(request,template,context)


def set_institution(request,institution_id):
	institution = Institution.objects.get(id=institution_id)
	request.user.personnel.actual_institution = institution
	request.user.personnel.save()
	return redirect("/")

def operations_details_list(request,operation_id):
	template = "webpages/ctn_bpf/operations_details_list.html"
	context = basis(request)
	operation = Operation.objects.get(id=operation_id)
	context["operation"] = operation
	return render(request,template,context)

def operations_details(request,operation_id):
	template = "webpages/ctn_bpf/operations_details.html"
	context = basis(request)
	operation = Operation.objects.get(id=operation_id)
	actual_institution = context['actual_institution']
	if operation.institution() != context['actual_institution']:
		request.user.personnel.actual_institution = operation.institution()
		request.user.personnel.save()
		context = basis(request)
	lines = list()

	tache = operation.tache
	if actual_institution.default_options != True:
		try:
			i = 0
			for th in actual_institution.operations_modules().fill_fields_rapp():
				a = th
				if a["type"] == "choix":
					a["extras"] = operation.get_value(a["field"])
				lines.append(a)
			aggs2 = tache.aggregates2()
			for a in aggs2:
				lines[i]["field"] = a
				i+=1
		except:
			pass
	context["lines"] = lines

	tache = operation.tache
	context['operation'] = operation
	context['tache'] = tache
	context['institutions'] = Institution.objects.filter()
	context['menu'] = 'o'
	return render(request,template,context)

def history(request,dates="#"):
	template = "webpages/ctn_bpf/history.html"
	context = basis(request)
	entity = InsitutionEntities.objects.filter(m_institution=context['actual_institution']).select_related('m_institution').last().m_entity_type
	tasks = entity.lines()
	if context['actual_institution'].default_options == True:
		context['fields'] = [entity.m_nom,'Operation','Personnel','Rapport Technique','Date']
		unsorted_results = list()
		for t in tasks:
			for o in t.operations():
				aka = OperationRapport.objects.filter(operation__id=o.id)
				for o2 in aka:
					unsorted_results.append(o2)
	else:
		if context["actual_institution"].repeat_mode == True:
			template = "webpages/ctn_bpf/history_rapport.html"
			tasks = context["actual_institution"].taches()
			context["taches"] = tasks

			context['menu'] = 'h'
			#context['dates'] = dates
			paginator_o = Paginator(tasks,10)
			page_number_o = request.GET.get('page')
			elements_page = paginator_o.get_page(page_number_o)
			#oeuvres_date
			context['pages_o']=elements_page
			context['num_pages']=paginator_o.num_pages
			context['page_range']=paginator_o.page_range
			"""
			paginator_o = Paginator(sorted_result,10)
			page_number_o = request.GET.get('page')
			elements_page = paginator_o.get_page(page_number_o)
			#oeuvres_date
			context['pages_o']=elements_page
			context['num_pages']=paginator_o.num_pages
			context['page_range']=paginator_o.page_range
			"""
		else:
			tmpas = context['actual_institution'].operations_modules().fill_fields_rapp()
			aggregates = list()
			for t in tmpas:
				if t['type'] == 'choix':
					aggregates.append(t['extras'])
				else:
					aggregates.append(t['field'])
			context['fields'] = [entity.m_nom,context['actual_institution'].operations_name]+aggregates+['Personnel','Date']

			unsorted_results = list()
			for t in tasks:
				for o in t.operations():
					unsorted_results.append(o)

			sorted_result = sorted(unsorted_results, key= lambda t: t.date_creation)
			if dates != "#":
				start_date = request.POST['start_date']
				end_date = request.POST['end_date']
				context['start_date'] = start_date
				context['end_date'] = end_date

				start_date = start_date.split("-")
				end_date = end_date.split("-")
				start_date = [int(elt) for elt in start_date]
				end_date = [int(elt) for elt in end_date]

				result = list()
				for t in sorted_result:
					start_date_cmp = start_date == list() or (t.date_creation.year > start_date[0] or t.date_creation.year == start_date[0] and t.date_creation.month > start_date[1] or t.date_creation.year == start_date[0] and t.date_creation.month == start_date[1] and t.date_creation.day >= start_date[2])
					end_date_cmp = end_date == list() or (t.date_creation.year < end_date[0] or t.date_creation.year == end_date[0] and t.date_creation.month < end_date[1] or t.date_creation.year == end_date[0] and t.date_creation.month == end_date[1] and t.date_creation.day <= end_date[2])
					
					if start_date_cmp and end_date_cmp:
						result.append(t)
			sorted_result = result

			context['lines'] = sorted_result
			context['nb_lines'] = len(sorted_result)
			context['institutions'] = Institution.objects.filter()
			context['menu'] = 'h'
			context['dates'] = dates
			paginator_o = Paginator(sorted_result,10)
			page_number_o = request.GET.get('page')
			elements_page = paginator_o.get_page(page_number_o)
			#oeuvres_date
			context['pages_o']=elements_page
			context['num_pages']=paginator_o.num_pages
			context['page_range']=paginator_o.page_range
	return render(request,template,context)

def calendar(request):
	template = "webpages/ctn_bpf/agenda_week.html"
	context = basis(request)
	return render(request,template,context)

def save_period(request):
	institution = request.POST['institution']
	periode = request.POST['periode']
	decoupage = request.POST['decoupage']
	edit_or_create = request.POST['edit_or_create']
	try:
		big_period = request.POST["big_periode"]
		sub_period = 0
	except:
		sub_period = None
	if sub_period != None:
		r_big_period = Periode.objects.get(id=int(big_period))
		sub_period = request.POST["sub_period"]
		details = request.POST["details"]
		if edit_or_create != 'e':
			r_sub_period = SubPeriode(m_periode=r_big_period,m_sub_value=periode,m_decoupage=decoupage,m_decoupage_description=details)
		else:
			edit_id = request.POST['edit_id']
			r_sub_period = SubPeriode.objects.get(id=int(edit_id))
			r_sub_period.m_periode = r_big_period
			r_sub_period.m_sub_value = periode
			r_sub_period.m_decoupage = decoupage
			r_sub_period.m_decoupage_description = details
		r_sub_period.save()
	else:
		if edit_or_create != 'e':
			r_period = Periode(m_value=periode,m_decoupage=decoupage)
		else:
			edit_id = request.POST['edit_id']
			r_period = Periode.objects.get(id=int(edit_id))		
			r_period.m_value = periode
			r_period.m_decoupage = decoupage
		r_period.save()
		if edit_or_create != 'e':
			institution = Institution.objects.get(id=int(institution))
			i_periode = Institution_Periodes(m_institution=institution,m_periode=r_period)
			i_periode.save()
	return redirect("/configurations/")

def ajax_graphiques(request):
	data = dict()
	id_tache = int(request.GET.get('id_graph'))
	type_graph = request.GET.get('type_graph')
	nature_graph = int(request.GET.get('nature_graph'))
	inst_graph = Institution.objects.get(id=int(request.GET.get('inst_graph')))
	actual_config = inst_graph.default_options
	#Aka c'est ici où tu recuperes l'element
	if nature_graph != -1:
		element = InsitutionEntities.objects.filter(m_institution=inst_graph,m_hierachie=nature_graph).first().m_entity_type
	else:
		element = InsitutionEntities.objects.filter(m_institution=inst_graph).last().m_entity_type

	if element.is_tache:
		entity = Tache.objects.get(id=id_tache)
		operations = entity.operations()
		nb_operations = len(operations)
	else:
		entity = Entity.objects.get(id=id_tache)
	# Evolution d'une Tache selon les Périodes 
	if type_graph == 'eT':
		if element.is_tache:
			tache_tmp = Tache.objects.get(id=entity.id)
			plansT = list()
			for p in tache_tmp.plannification().table():
				plansT.append(p)
			x_abcisses = list()
			for p in plansT:
				for xi in inst_graph.default_subperiod.decoup_desc_slip2():
					x_abcisses.append(str(p)+"-"+str(xi))
			
			# Matrice des mois	
			result = list()

			x_interval = tache_tmp.plannification().table()
			operations = tache_tmp.operations()
			nb_operations = operations.count()
			tmp_sum = 0
			nb_x_abcisses = 0
			tmp_dict = list()
			for x in x_interval:
				#tmp_sum = 0
				operations_2 = operations.filter(m_tache_plannification=x)
				all_dict = list()
				for op in operations_2:
					x_dict = list()
					for t in op.periodes().desc_split():
						x_dict.append(0)
					i_x_d = 0

					for t in op.periodes().desc_split():
						if actual_config == True:
							if t == '2':
								tmp_val = 100
							else:
								tmp_val = 0
						else:
							if t != '9':
								ds = {'0':0,'1':0,'2':100}
								tmp_val = ds[op.etat]
							else:
								tmp_val = 0

						x_dict[i_x_d] += tmp_val
						i_x_d += 1
					all_dict.append(x_dict)
				#all_dict contient la matrice d'un mois i)

				tmp_dict_result = list()
				if operations_2.first() != None:
					for t in operations_2[0].periodes().desc_split():
						tmp_dict_result.append(0)
					for a_dict in all_dict:
						ia=0
						for a in a_dict:
							tmp_dict_result[ia]+=a
							ia+=1
				tmp_dict += tmp_dict_result
			result_tmp = 0
			result = list()
			for t in tmp_dict:
				result_tmp += t
				result.append((result_tmp/nb_operations))
		else:
			x_abcisses = inst_graph.default_period.decoup_slip()
			tmp = list()
			taches = entity.taches()
			discovered = list()
			index_tmp = 0
			nb_taches = len(taches)
			for x in x_abcisses:
				tmp.append(0)
				for t in taches :
					if x in t.plannification().table() and t not in discovered:
						tmp[index_tmp] += t.progression()
						discovered.append(t)
				index_tmp += 1 
			y_abcisses = list()
			for y in range(index_tmp):
				if nb_taches > 0:
					y_abcisses.append((tmp[y]/nb_taches))
				else:
					y_abcisses.append(0)
			result = list()
			rst = 0
			for y in y_abcisses:
				rst += y
				result.append(rst)
	elif type_graph == 'p':
		x_abcisses = set()
		result_x = list()
		y_abcisses = list()
		for o in operations:
			x_abcisses.add(o.personnel)
		for perso in x_abcisses:
			y_abcisses.append(perso.progression_taches(inst_graph))
		for x in x_abcisses:
			result_x.append(str(x))
		x_abcisses = result_x
		result = y_abcisses
	elif type_graph == 't':
		x_abcisses = list()
		result = list()
		subs = entity.sub_entities()
		try:
			sub_name = str(subs[0].m_type_entity)
		except:
			sub_name = " "
		i=0
		for x in subs:
			result.append(x.progression())
			x_abcisses.append(str(x))
			i+=1
		data['nb_sub'] = i
		data['sub_names'] = sub_name
	data['x_abcisses'] = x_abcisses
	data['y_abcisses'] = result
	return JsonResponse(data,safe=False)

@login_required(login_url='/log_account')
def decision(request,nature="#",element_id=0,operation_rapport_id=None):
	context = basis(request)
	if nature == "o":
		template = "webpages/ctn_bpf/decision.html"
		operation = Operation.objects.get(id=element_id)
		if context["actual_institution"].repeat_mode == True:
			template = "webpages/ctn_bpf/decision_rapport.html"
			operation = Operation.objects.get(id=element_id)
			if operation_rapport_id == None:
				operation_rapport = operation.get_operation_details_invalid().last()
				context["operation_rapport"] = operation_rapport
		context['operation'] = operation
		context['tache']=operation.tache
	else:
		context["entity"] = Entity.objects.get(id=int(element_id))
		template = "webpages/ctn_bpf/decision_plus.html"
	return render(request,template,context)

def get_elements(request):
	#Elements can be Entity, Forms
	if True: #try:
		other_limk = request.GET.get("other")
		institution = Institution.objects.get(id=int(request.GET.get('institution')))
		if other_limk == "dS":
			dSs = DataSet.objects.filter(m_institution=institution)
			data = {
				"datasets":list(),
				"datasets_id":list()
			}
			for d in dSs:
				data["datasets"].append(str(d))
				data["datasets_id"].append(str(d.id))
		elif other_limk == "dE_code":
			data = dict()
			codes = request.GET.get("codes").split("#")
			result = list()
			codes_replace = list()
			for code in codes[:-1]:
				res = list()
				j=0
				n = len(code)
				while j <n:
					if code[j] == "$":
						j += 1
						k =j
						while code[j] != "$":
							j+= 1


						res.append(code[k:j])
						j+=2
					else:
						j+=1
				tmp_res = list()
				tmp_res2 = list()
				for r in res:
					tmp_res.append(str(DataElement.objects.get(id=int(r))))
					tmp_res2.append(r)
				result.append(tmp_res)
				codes_replace.append(tmp_res2)
			data["data_elts"] = result
			data["codes_replace"] = codes_replace
		elif other_limk == "dI_formula":
			values = request.GET.get("value").split("#")
			data_elts = DataSet.objects.get(id=int(request.GET.get("dataset")))
			result_formula = list()
			for v in values[:-1]:
				ind = Indicateur.objects.get(id=int(v))
				result_formula.append(ind.m_numerateur)
			data = dict()
			data["data_elts"] = data_elts.join_dataelts()
			data["formulas"] = result_formula
	else: #except:
		value = int(request.GET.get('value'))
		nature = int(request.GET.get('nature'))
		institution = Institution.objects.get(id=int(request.GET.get('institution')))
		entity_type = InsitutionEntities.objects.filter(m_hierachie=nature,m_institution=institution).select_related('m_institution').first().m_entity_type
		# entity to upload
		entity = Entity.objects.get(id=value)
		default_fields = entity_type.fields()
		default_fields_type = entity_type.type_fields()
		default_fields_values = entity.values()
		#Default Values to putt
		expected_fields = entity_type.fields_rapported()
		expected_types_type = entity_type.type_fields_rapported()	
		results = list()
		data = {
			'entity':str(entity),
			'default_fields':default_fields,
			'default_fields_type':default_fields_type,
			'default_fields_values':default_fields_values,
			'expected_fields':expected_fields,
			'expected_types_type':expected_types_type
		}
	return JsonResponse(data,safe=False)

def get_elements_hierachy(request):
	nature = int(request.GET.get('nature'))
	institution = Institution.objects.get(id=int(request.GET.get('institution')))
	if nature == -100:
		type_entity = request.GET.get('type_entity')
		role = Role.objects.get(id=int(type_entity))
		entity_type = role.m_simple_auth
	elif nature != -1:
		entity_type = InsitutionEntities.objects.filter(m_hierachie=nature,m_institution=institution).first().m_entity_type
	else:
		entity_type  = InsitutionEntities.objects.filter(m_institution=institution).last().m_entity_type
	try:
		big_entity = int(request.GET.get('big_entity'))
		ent = Entity.objects.get(id=int(big_entity))
		lines = ent.sub_entities()
	except:
		lines = entity_type.lines()
	tmp = list()
	ids = list()
	for l in lines:
		tmp.append(str(l))
		ids.append(l.id)
	data = {
		'lines':tmp,
		'ids':ids
	}
	return JsonResponse(data,safe=False)

def get_entities_subsequency(request):
	pass

def get_elements_subsequency_true(request):
	nature = int(request.GET.get('nature'))
	entity = int(request.GET.get('entity'))
	report = int(request.GET.get('report'))
	try:
		institution = int(request.GET.get("institution"))
	except:
		institution = None
	if entity != -1:
		try:
			entity = Entity.objects.get(id=entity)
		except:
			entity = 0
		elts = entity.child_trees()
	else:
		elts = [Institution.objects.get(id=institution).top_entity().lines()]

	data_names = list()
	data_ids = list()
	for elt in elts:
		tmp_id = list()
		tmp_name = list()
		for e in elt:
			tmp_id.append(e.id)
			tmp_name.append(str(e))
		data_names.append(tmp_name)
		data_ids.append(tmp_id)

	data = {
		'data_ids':data_ids,
		'data_names':data_names
	}
	return JsonResponse(data,safe=False)

def get_elements_subsequency(request):
	nature = int(request.GET.get('nature'))
	entity = int(request.GET.get('entity'))
	report = int(request.GET.get('report'))
	try:
		institution = int(request.GET.get("institution"))
	except:
		institution = None
	try:
		entity = Entity.objects.get(id=entity)
	except:
		entity = 0

	if report == 0:
		operations = Operation.objects.filter(etat='0',personnel=request.user.personnel).values('code')
	elif report ==1:
		operations = Operation.objects.filter(etat='1',accountable=request.user.personnel).values('code')
	elif report == 2:
		operations = Operation.objects.filter(etat='1',consulted=request.user.personnel).values('code')
	elif report == 3:
		operations = Operation.objects.filter(etat='2',informed=request.user.personnel).values('code')
	else:
		operations = Operation.objects.filter().values('code')

	if institution != None:
		institution = Institution.objects.get(id=institution)
		operations = operations.filter(m_institution=institution)

	bool(operations)
	result = list()
	if entity != 0:
		for o in operations:
			try:
				if o['code'] not in ["",None] and o['code'].split("#")[nature] == str(entity.id):
					result.append(o)
			except:
				pass
	else:
		pre_hierachie = int(request.GET.get("pre_hierachy"))
		if pre_hierachie not in [0,-1]:
			for o in operations:
				if o['code'] not in ["",None] and o['code'].split("#")[(nature-1)] == str(pre_hierachie):
					result.append(o)
		elif nature == 0:
			result = list(operations)
	steps = list()

	k=0
	if True:
		if report != 100:
			for i in operations[0]['code'].split("#"):
				steps.append(set())
				k+=1
		else:
			for i in list(operations)[-1]['code'].split("#"):
				steps.append(set())
				k+=1
	else:
		pass

	# Recuperer les Operations
	i = 0
	for o in result:
		i = 0
		for j in range(k):
			if o['code'] not in [None,""," "] :
				steps[i].add(o['code'].split("#")[j])
				i+=1

	# Transformer en Liste
	ajax_steps = list()
	for s in steps:
		ajax_steps.append("#".join(list(s)))

	ajax_steps2 = list()
	for s in steps:
		s3 = list(s)
		s2 = list()
		for t in s3:
			if t not in ['',None]:
				s2.append(int(t))
		a = Entity.objects.filter(id__in=list(s2))
		a2 = [str(t) for t in list(a)]
		ajax_steps2.append("#".join(a2))

	data = {
		'operations':result,
		'ajax_steps':ajax_steps,
		'ajax_steps2':ajax_steps2
	}
	return JsonResponse(data,safe=False)

def save_valid_rapport(request):
	nature = request.POST['nature']
	resultat = request.POST['resultat_realise']
	institution = Institution.objects.get(id=int(request.POST['institution']))
	entity_type = InsitutionEntities.objects.filter(m_hierachie=nature,m_institution=institution).first().m_entity_type
	entity = Entity.objects.get(id=int(request.POST['value']))
	entity.is_rapported = True
	entity.save()
	tR = EntityRapport(m_entity=entity,m_resultat_realise=resultat)
	tR.save()
	return redirect('/'+nature+'/')

def filter_entities(request):
	institution = Institution.objects.get(id=int(request.POST['institution']))
	sub_value = request.POST['sub_value']
	hierachie = int(request.POST['hierachie'])
	tmp_hierachie = hierachie-1
	if hierachie <= 0:
		hierachie = 0
		value = '0'
	else:
		entity_type = InsitutionEntities.objects.filter(m_institution=institution,m_hierachie=(hierachie-1)).first().m_entity_type
		entity_type_actual = InsitutionEntities.objects.filter(m_institution=institution,m_hierachie=(hierachie)).first().m_entity_type
		enums_list = list()
		enums = entity_type_actual.enum_fields()['result']
		if entity_type_actual.m_enum_values not in ['',None]:
			for val in enums:
				enums_list.append(request.POST["enum_"+val['name']])
		if enums_list != list():
			enums_list = "||".join(enums_list)
		value = request.POST[str(entity_type)]
	#gestionnaire(request,gest_val,gest_id=0,name=None,structure=None,periode=None)
	if value != '0':
		element = Entity.objects.get(id=int(value))
		if enums_list != list():
			response = redirect('/gestionnaire/'+str(tmp_hierachie)+'/'+str(element.id)+'/')
		else:
			response = gestionnaire(request,str(tmp_hierachie),str(element.id),None,None,None,enums_list)
	else:
		response = redirect('/gestionnaire/'+str(hierachie)+'/')
	return response

def search(request):
	if request.user.is_authenticated == True:
		template = "webpages/ctn_bpf/search.html"
		val = request.POST['search']
		context = basis(request)
		searches = list()
		entities = context['actual_institution'].get_entities()
		for e in entities:
			lines = e.m_entity_type.lines()
			hierachie = e.m_hierachie
			def_color = '#00a2c3'
			if e.m_entity_type.is_tache:
				def_color = 'orange'
			for l in lines:
				if val in str(l):
					searches.append({'nature':'e','label':e,'value':l,'hierachie':hierachie,'color':def_color})

		for s in Structure.objects.filter(nom__contains=val,institution=context['actual_institution']):
			searches.append({'nature':'s','label':'Structure','value':s,'color':'#9012a1'})

		for s in Personnel.objects.filter(nom__contains=val):
			searches.append({'nature':'p','label':'Personnel','value':str(s),'color':'#12c304'})

		context['searches'] = searches
	else:
		return redirect("/")
	return render(request,template,context)

def search2(request,menu):
	search = request.POST["search"]
	if menu == 'i':
		response = institutions(request,search)
	elif menu == 'p2':
		response = personnels(request,search)
	elif menu == 'p2_RACI':
		response = personnels_raci(request,search)
	elif menu == 'r':
		response = roles(request,search)
	elif menu == 'aN':
		response = alert_notifs(request,search)
	return response

@login_required(login_url='/log_account')
def messages(request):
	template = "webpages/ctn_bpf/search.html"
	context = basis(request)
	context['msg_view'] = True
	results = list()
	personnel = request.user.personnel
	accounted = personnel.operations_accounted()
	bool(accounted)
	"""
	for o in Operation.objects.filter():
		if  o.rapported() not in [None,'0'] and o.progression()<100 and context['permissions'] > 0:
			results.append({'value':o,'name':'Operation','link':'o','nature':'r'})
	"""
	for o in accounted:
		if o.rapported() not in [None,'0'] and o.progression()<100 :
			#and context['permissions'] > 0
			results.append({'value':o,'name':'Operation','link':'o','nature':'r'})
	entities_type = context['actual_institution'].get_entities()
	nb_observations = 0
	"""
	for e in entities_type:
		lines = e.m_entity_type.lines()
		for l in lines :
			if l.is_rapported != True and l.progression() == 100:
				results.append({'value':l,'name':str(l.m_type_entity),'link':'o','nature':'o'})
	"""
	context['msgs'] = True
	paginator_o = Paginator(results,10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	#oeuvres_date
	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range
	return render(request,template,context)

def bad_pass(request):
	mail = request.POST['mail']
	sent = False
	try:
		subject = "Restauration de Mot de Passe"
		code = ""
		import random
		for i in range(0,6):
			code += str(random.randint(0,9))
			#r_bd_user.set_password('User'+password)
		message = " Entrez ce code pour restaurer votre Compte " 
		email = r_perso.mail
		email_from = settings.EMAIL_HOST_USER
		recipient_list = [email,]
		send_mail( subject, message, email_from, recipient_list, fail_silently=False)
		sent = True
	except:
		pass
	data = {
		'sent':sent
	}
	if sent == True:
		data['code'] = code
	return JsonResponse(data)

def notifs_rapp(request):
	user_id = request.GET.get('value')
	insti_id = request.GET.get('institution')
	insti_id = Institution.objects.get(id=int(insti_id))
	#perso = Personnel.objects.get(bd_user__id=int(user_id))
	operations = Operation.objects.filter(personnel=request.user.personnel)
	# General_Results
	nb_is_rapported = 0
	nb_have_to_report = 0
	nb_observations = 0

	nb_is_rapported2 = 0
	nb_have_to_report2 = 0
	nb_observations2 = 0


	actual_institution = insti_id

	context = basis(request)
	perso = request.user.personnel
	for o in operations:
		if o.etat == '0':
			nb_have_to_report += 1
			if o.institution() == actual_institution:
				nb_have_to_report2 +=1
		elif o.etat == '1':
			nb_is_rapported+=1
			if o.institution() == actual_institution:
				nb_is_rapported2 +=1
	entities_type = insti_id.get_entities()

	nb_observations = Operation.objects.filter(etat='1',accountable=perso).count()	

	for e in entities_type:
		lines = e.m_entity_type.lines()
		for l in lines :
			if l.is_rapported != True and l.progression() == 100:
				nb_observations += 1

	personnel = request.user.personnel
	# for o in operations
	"""
	for o in accounted:#o.institution() in context['personnel'].all_institutions() and 
		if o.progression() < 100 and o.rapported() not in ['0',None]:
			# and context['permissions'] > 0
			nb_observations += 1
	"""
	data = {
		'nb_have_to_report':nb_have_to_report,
		'nb_is_rapported':nb_is_rapported,
		'nb_observations':nb_observations,
		'nb_have_to_report2':nb_have_to_report2,
		'nb_is_rapported2':nb_is_rapported2,
		'nb_observations2':nb_observations2
	}
	return JsonResponse(data)

def valid_observations(request):
	element_id = request.POST["element_id"]
	valid_attributes = request.POST['attributes']

	element = Entity.objects.get(id=int(element_id))
	is_tache = element.m_type_entity.is_tache
	if is_tache:
		element = Tache.objects.get(id=int(element_id))
	element.is_rapported = True
	element.m_reported_fields = valid_attributes
	element.save()
	return redirect('/operations/')

def print_mail_file(request):
	owners = Owner.objects.filter()
	mail_lists = list()
	for o in owners:
		mail_lists.append(o.m_user.email)
	context = {
		'mail_lists':mail_lists
	}
	template = "webpages/ctn_bpf/csv_template.html"
	return render(request,template,context)

def assistance(request):
	template = "webpages/ctn_bpf/assistance.html"
	context = basis(request)
	result = render(request,template,context)
	try:
		if request.session['assistance'] == 1:
			result = redirect('/')
	except:
		pass
	return result

def ajax_restore(request):
	import random
	r_mail = request.GET.get('mail')
	code = ""
	for i in range(6):
		code += str(random.randint(0,9))
	message_context = {
		'code':code,
	}
	subject = " Récupération de Compte Opera +"
	message = render_to_string('webpages/ctn_bpf/mails/new_code.html',message_context)
	email = r_mail
	email_from = settings.EMAIL_HOST_USER
	recipient_list = [email,]
	msg = EmailMessage(subject, message, email_from, recipient_list)
	msg.content_subtype = 'html'
	try:
		msg.send()
		send = '0'
	except:
		send = '1'
	data = {
		'code':code,
		'send':send
	}
	return JsonResponse(data)

def restorepass(request):
	mail = request.POST['restore']
	password = request.POST['password']
	user = User.objects.filter(email=mail).first()
	user.set_password(password)
	user.save()
	login(request,user)
	return redirect('/')

def documentation(request):
	document = OperaFile.objects.filter(m_name="DOCU").first().m_file.url
	return redirect(document)

# New Updates
@login_required(login_url='/log_account')
def chaine_indicateurs(request):
	template = "webpages/ctn_bpf/chaine_resultat.html"
	context = basis(request)
	actual_institution = context['actual_institution']
	context['menu'] = 'l'
	context['top_entities'] = actual_institution.top_entity().lines()
	context['this_entities'] = actual_institution.get_entities()
	return render(request,template,context)

def get_indicateur_value(request):
	indicateur = Indicateur.objects.get(id=int(request.GET.get('id_indicateur')))
	fields = indicateur.m_fields
	periodicite = indicateur.m_periodicite
	final_cible = indicateur.m_final_cible
	if final_cible == None:
		final_cible = ""
	cibles = indicateur.m_cibles
	data_verification = indicateur.m_data_verification

	verification_indi = indicateur.m_verification_indi

	data = {
	'obj':indicateur.m_objectif_indi,
	'indicateur':indicateur.m_name,
	'fields':fields,
	'periodicite':periodicite,
	'final_cible':final_cible,
	'cibles':cibles,
	'verification_indi':verification_indi,
	'data_verification':data_verification,
	"data_verificationind":"#",
	'others':"#"
	}
	tmp_verifi = data_verification.split("#")
	if tmp_verifi[0] == "1":
		ind_ve = DataSet.objects.get(id=int(tmp_verifi[1]))
		data["data_verificationind"] = str(ind_ve)
		data["data_verificationind_url"] = "/data_form/"+str(ind_ve.id)+"/0/"
	if indicateur.m_others not in [None,""]:
		data["others"] = indicateur.m_others
	return JsonResponse(data,safe=False)

def ajax_institution(request):
	sens = request.GET.get('sens')
	devise = request.GET.get('devise')
	institution = request.GET.get('institution')
	institution = Institution.objects.get(id=int(institution))
	if int(sens) == 1:
		institution.default_options = False
	elif int(sens) == 0:
		institution.default_options = True
	elif int(sens) == 3:
		institution.finan_options = None
	elif int(sens) == 2:
		institution.finan_options = devise
	institution.save()
	data = {
		'nada':True	
	}
	return JsonResponse(data,safe=False)

def save_indicateur(request):
	edit_or_create = request.POST["edit_or_create"]
	gest_id = request.POST['gest_id']
	gest_val = request.POST['gest_val']
	name = request.POST["nature_indicateur"]

	fields = request.POST["indi_adds"]
	periodicite = request.POST["periodicite"]
	periodicite2 = request.POST["periodicite2"]

	cibles = request.POST["indi_cibls"]
	type_entity = request.POST["entity_id"]
	data_verification = request.POST["indi_srcs"] 

	numerateur = request.POST["numerateur"]
	denominateur = request.POST["denominateur"]

	objectif_indi = request.POST["objectif_indi"]
	verification_moyen = request.POST["verification_moyen"]+"#"+request.POST["veri_type"]

	sources_speci = request.POST["specig_form"]
	if sources_speci == "1":
		try:
			sources_speci += "#"+request.POST["dataSt"]
		except:
			pass

	codes_colors = request.POST["codes_colors"]
	alerts_modals = request.POST["alert_modals"]
	others = request.POST["other"]

	cibles = request.POST["indi_cibls"]
	coeficient = int(request.POST["coefficient"])

	unite = request.POST["unite_indicateur"]

	try:
		default_calcul = request.POST["default_calcul"]		
	except:
		default_calcul = 1

	if edit_or_create == "c":

		entity = Entity.objects.get(id=int(type_entity))
		indi = Indicateur(m_name=name,m_fields=fields,m_periodicite=periodicite,m_sub_periodicite=periodicite2,m_data_verification=data_verification,m_cibles=cibles,m_enti=entity)
	else:
		edit_id = request.POST["edit_id"]
		indi = Indicateur.objects.get(id=int(edit_id))
		indi.m_name=name
		indi.m_fields=fields
		indi.m_periodicite=periodicite
		indi.m_sub_periodicite=periodicite2
		indi.m_data_verification=data_verification
		indi.m_cibles=cibles
	indi.m_institution = basis(request)["actual_institution"]
	indi.m_cibles = cibles
	indi.m_numerateur = numerateur
	indi.m_denominateur = denominateur
	indi.m_coefficient = coeficient
	indi.m_data_verification = sources_speci
	indi.m_unite = unite

	indi.objectif_indi = objectif_indi
	indi.m_colors_code = codes_colors
	indi.m_verification_indi = verification_moyen
	indi.alerts_code = alerts_modals
	indi.m_others = others

	try:
		ind.m_secundo_options = request.POST["other_fields"]
	except:
		pass
	if int(default_calcul) == 1:
		formula = "$"+str(numerateur)+"$"+" * "+str(coeficient)+" /"+"$"+str(denominateur)+"$" 
		indi.m_datalets_calcul = formula
	indi.save()
	return redirect('/evaluer/'+gest_val+'/'+gest_id)	

@login_required(login_url='/log_account')
def evaluer(request,hierachie="0",gest_id=0,search=None,specifi_id=None):
	context = basis(request)
	hierachie = int(hierachie)
	if specifi_id == None:
		if hierachie != -1:
			entity = InsitutionEntities.objects.filter(m_hierachie=hierachie,m_institution=context['actual_institution']).first().m_entity_type
		else:
			entity = InsitutionEntities.objects.filter(m_institution=context['actual_institution']).last().m_entity_type
		context['entity'] = entity
		context['hierachie'] = hierachie
		context['hierachy'] = hierachie
		if gest_id == 0:
			elements = entity.lines()
		else:
			get_e = Entity.objects.get(id=int(gest_id))
			context['base_val'] = get_e
			elements = list(get_e.sub_entities())
			context['sup_hierachy'] = list()
			for t in get_e.sup_hierachie():
				context['sup_hierachy'].append(t)
			context['sup_hierachy'].append(get_e)

		if search != None:
			tmp = elements
			elements = list()
			for t in tmp:
				if search in t.m_value_fields:
					elements.append(t)

	else:
		a_entity = Entity.objects.get(id=specifi_id)
		entity = a_entity.m_type_entity
		context['entity'] = entity
		context['hierachie'] = hierachie
		context['hierachy'] = hierachie
		elements = [a_entity]
	paginator_o = Paginator(elements,10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	#oeuvres_date
	dataelts = DataElement.objects.filter(m_institution=context["actual_institution"])

	context["indi_options"] = entity.indicateurs
	try:
		context["indi_options"][0] == None
		context["no_secund"] = False
	except:
		context["no_secund"] = None

	context['menu']='g'
	context['g_v'] ='i2'
	context['gest_id']=gest_id
	context['gest_val'] = hierachie
	context['gest_val_1'] = hierachie+1
	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range
	context['dataelts']=dataelts
	context['dataelts2']=dataelts.exclude(m_default_value=None)

	template = "webpages/ctn_bpf/evaluer.html"
	return render(request,template,context) 

def evaluer_detail(request,gest_id=0):
	return evaluer(request,"0",0,None,gest_id)

def indic_plus(request,indic_id):
	context = basis(request)
	entity = Entity.objects.get(id=int(indic_id))
	template = "webpages/ctn_bpf/indic_plus.html"
	context['entity'] = entity
	return render(request,template,context) 

def data_elements(request):
	context = basis(request)
	entity = Entity.objects.get(id=int(indic_id))
	template = "webpages/ctn_bpf/indic_plus.html"
	context['entity'] = entity
	return render(request,template,context) 

def duplicate(request):
	from .utilities2 import duplicate_entity_logic,duplicate_tache,duplicate_entity,duplicate_operation
	generator_d = request.POST['generator_d']
	response = ""
	if generator_d == 'e':
		value = request.POST['dup_id']
		entity = Entity.objects.get(id=int(value))
		link = request.POST['link']
		response = redirect(link)
		#new = int(request.POST['new_dup'])
		new = 0
		try:
			name = request.POST['nom_dup']
			if name in [None,'']:
				name = "#"
		except:
			name = "#"
		try:
			relogic_dup = int(request.POST['relogic_dup'])
		except:
			relogic_dup = 0

		if relogic_dup == 0:
			duplicate_entity(entity,name)
		else:
			duplicate_entity_logic(entity,name)

	elif generator_d == 'o':
		value = request.POST['dup_id']
		entity = Operation.objects.get(id=int(value))
		link = request.POST['link']
		response = redirect(link) #redirect("/taches/"+str(operation.m_tache.id))
		try:
			name = request.POST['nom_dup']
			if name in [None,'']:
				name = "#"
		except:
			name = "#"
		o2 = duplicate_operation(entity,name)
		o2.tache = entity.tache
		try:
			relogic_dup = (request.POST['reraci_dup'])
			r_personnel = Personnel.objects.get(id=int(request.POST["perso"]))
			r_accountable = Personnel.objects.get(id=int(request.POST["accountable"]))
			r_consulted = Personnel.objects.get(id=int(request.POST["consulted"]))
			r_informed = Personnel.objects.get(id=int(request.POST["informed"]))
			o2.personnel = r_personnel
			o2.accountable = r_accountable
			o2.consulted = r_consulted
			o2.informed = r_informed
		except:
			relogic_dup = 0
		o2.save()

	elif generator_d == 'i':
		values = request.POST['values_d'].split("|")
		response = redirect("/institution/")
		try:
			entity_dup = request.POST['entity_dup']
		except:
			entity_dup = "0"
		for v in values[:-1]:
			ins = Institution.objects.get(id=int(v))
			tmp = ins
			tmp.id = None
			tmp.save()

			# entity Institutions
			ins_entities = InsitutionEntities.objects.filter(m_institution__id = int(v))
			for i in ins_entities:
				tmp11 = i.m_entity_type
				tmp11.id = None
				tmp11.save()
				tmp1 = InsitutionEntities(m_institution=tmp,m_hierachie=i.m_hierachie,m_entity_type=tmp11)
				tmp1.save()
				if entity_dup == '1':
					for i2 in tmp11.lines():
						tmp2 = i2
						tmp2.m_type_entity =  tmp11
						if tmp11.is_tache:
							tmp3 = Tache.objects.get(id=tmp2.id)
							tmp3.m_type_entity =  tmp11
						tmp2.id = None
						tmp3.id = None
						tmp2.save()
						tmp3.save()

			# structures
			structures = Structure.objects.filter(institution__id = int(v))
			for i in structures:
				tmp2 = i 
				tmp2.id = None
				tmp2.institution = ins
				tmp2.save()

			#aggregates
			aggregates = Aggregate.objects.filter(m_institution__id = int(v)).first()
			if aggregates != None:
				tmp3 = aggregates
				tmp3.id = None
				tmp3.m_institution = ins
				tmp3.save()

			#roles
			roles = Role.objects.filter(actual_institution__id = int(v))
			for r in roles:
				tmp4 = r
				tmp4.id = None
				tmp4.actual_institution = ins
				tmp4.save()
		request.session['new_ins'] = 1
	return response

def print_pdf(request):
	ind = int(request.GET.get('ind'))

	context = basis(request)
	operations = list()
	if ind == 1:
		tmp_ops = Operation.objects.filter()
	elif ind == 2:
		p = request.user.personnel
		tmp_ops = Operation.objects.filter(personnel=p)
	if ind in [1,2]:
		for t in tmp_ops:
			if t.institution() == context['actual_institution']:
				operations.append(t)
		lines = list()
		taches_lines = list()
		for o in operations:
			tmp_line = str(o.tache)+"§"+str(o)+"§"+str(o.personnel)
			if o.periodes() != None:
				tmp_line += "§"+str(o.periodes().details_periode())
			else:
				tmp_line += "§"+" "
			if context['actual_institution'].default_options != True:
				values = o.value_split()
				agr_fields = o.agr_fields()
				i=0
				for v in agr_fields:
					if v != 'file':
						try:
							tmp_line += "§"+str(values[i])
						except:
							tmp_line += "§"+" "
					else:
						tmp_line += "§" +" -- "
					i+=1
				tmp_line += "§" + o.status_op()
			lines.append(tmp_line)
	elif ind == 4:
		taches = context['actual_institution'].last_entity().lines()
		lines = list()
		for t in taches:
			hierachie = ""
			for h in t.sup_hierachie():
				hierachie += str(h.get_name()) + "§"
			fields = ""
			for f in t.values():
				fields += str(f) + "§"
			lines.append(hierachie+fields+str(t.progression())+ "% §"+str(t.m_date_modif))
	data = {
		'lines':lines	
	}
	return JsonResponse(data,safe=False)

@login_required(login_url='/log_account')
def dataelts(request,elt_id=0,elt_str=0):
	context = basis(request)
	context['g_v'] = 'eD'
	if elt_id == 0:
		template = "webpages/ctn_bpf/dataelts.html"
		indicateurs = Indicateur.objects.filter()
		dataelts = DataElement.objects.filter(m_institution=context["actual_institution"])
		context['indicateurs'] = indicateurs
		context['dataelts'] = dataelts
	else:
		template = "webpages/ctn_bpf/data_element_id.html"
		dataelt = DataElement.objects.get(id=int(elt_id))
		context["dataelt"] = dataelt
		context["structures"] = Structure.objects.filter(institution=context["actual_institution"])
		if elt_str == 0:
			context["actu_struc"] = context["structures"].first()
		else:
			context["actu_struc"] = Structure.objects.get(id=int(elt_str))
		#lines = dataelt
		tmps = dataelt.element_values(context["actu_struc"])
		periods_tmp = dict()
		p_tmps = list()

		class DEL:
			def __init__(self,e1,e2,e3=0):
				self.sup_period = e1
				self.period = e2
				self.value = e3
			def __repr__(self):
				return self.sup_period

		for t in tmps:
			a = t.m_dataset_value.m_period_value+"-"+t.m_dataset_value.m_sub_period_value
			if a in	p_tmps:
				if t.m_value not in ["",None]:
					periods_tmp[a].value += float(t.m_value)
			else:
				elts = DEL(t.m_dataset_value.m_sub_period_value,t.m_dataset_value.m_period_value,0)
				if t.m_value not in ["",None]:
					elts.value = float(t.m_value)
				else:
					elts.value = 0
				periods_tmp[a] = elts
				p_tmps.append(a)
		context["values"] = list()
		for p in p_tmps:
			context["values"].append(periods_tmp[p])
		#context["values"].group_by = ['designation']
	return render(request,template,context)

@login_required(login_url='/log_account')
def dataelts_edit(request,elt_id):
	template = "webpages/ctn_bpf/dataelts_edit.html"
	context = basis(request)
	indicateurs = Indicateur.objects.filter()
	dataelts = DataElement.objects.filter(id=elt_id).first()
	context['indicateurs'] = indicateurs
	context['dataelts'] = dataelts
	return render(request,template,context)

@login_required(login_url='/log_account')
def dataelts_indic(request):
	template = "webpages/ctn_bpf/dataelts_indic.html"
	context = basis(request)
	context['is_indi'] = True
	context['indicateurs'] = list()
	tmps_is = Indicateur.objects.filter()
	dataelts = DataElement.objects.filter()
	for i in tmps_is:
		enti = i.m_enti
		if enti != None:
			if enti.m_type_entity.get_institution(context['actual_institution']) != None:
				context['indicateurs'].append(i)
	context['dataelts'] = dataelts
	return render(request,template,context)

def ajax_progression(request):
	plannify = request.GET.get("plannify")
	periode = Periode.objects.get(id=int(request.GET.get("periode")))

	year = request.GET.get("year")
	institution = request.GET.get("institution")
	institution = Institution.objects.get(id=int(institution))
	sub_period = institution.default_subperiod

	try:
		mods = request.GET.get("mods")
	except:
		mods = None

	try:
		entity =  request.GET.get("entity")
		#entity_type =  request.GET.get("entity_type")
	except:
		entity = None

	progression = 0
	t_plannify = list()

	"""
	for t in taches:
		t_plannify.append(t.plannification())
	"""
	result = list()
	if plannify != "#":
		cumulate = int(request.GET.get("cumul1")) #1 #Mettre une variable
		nb_ops = 0
		ops = list()
		if entity == None:
			operations = Operation.objects.filter(m_institution=institution)
		else:
			operations = Entity.objects.get(id=int(entity)).operations()
		bool(operations)
		for o in operations:
			ops.append(o)

		try:
			tmp_val = get_period_values(periode,plannify+"_")[0]
		except:
			tmp_val = None

		if tmp_val != None:
			result.append(tmp_val)
			for o in ops:
				if o.m_tache_plannification != None:
					v = get_period_values(periode,o.m_tache_plannification+"_")
					cond1 = ( cumulate == 0 ) and int(v[0]) == int(tmp_val)
					cond2 = ( cumulate == 1 ) and int(v[0]) <= int(tmp_val)
					if len(v) > 0:
						if cond1 or cond2:
							progression += o.progression()
							nb_ops += 1
				else:
					pass
		glob_ops = int(request.GET.get("cumul2"))#1
		if glob_ops == 1:
			nb_ops = operations.count()
		if nb_ops > 0:
			progression /= nb_ops
	else:
		if mods in [None,"0"]:
			prs = list()
			tops = institution.top_entity().lines()
			plannify_all = request.GET.get("plannify_all")
			plannify_all = plannify_all.split("#")[:-1]
			t_plannify2 = t_plannify
			t_plannify =  subperiods_value(periode,year)
			mrd_t = list()
			i_t = 0
			for t in tops:
				mrd_t.append(list())
				for p in t_plannify:
					mrd_t[i_t].append(0)			
				i_t +=1

			i_t = 0
			
			for to in tops:
				nb_jT = 0
				if to.m_type_entity.is_tache == False:
					tach = to.taches()
				else:
					tach = [to]
				ops = list()
				for t in tach:
					ops += t.operations()
				t_plannify2 = list()
				for a in tach:
					a = Tache.objects.get(id=a.id)
					t_plannify2.append(a.plannification())
				j_t = 0
				for p in t_plannify:
					progression = 0
					nb_jT = 0
					nb_ops = 0
					if p != None:
						for o in ops:
							try:
								v = get_period_values(periode,o.m_tache_plannification+"_")
								if len(v) > 0:
									if int(v[0]) == int(p):
										progression += o.progression()
									nb_ops += 1
							except:
								pass
						if nb_ops != 0:
							mrd_t[i_t][j_t] = round(progression/nb_ops,2)
						j_t+=1
				i_t += 1
			prs = list()
			j =0
			for t in mrd_t:
				tmp = ""
				for s in t:
					tmp += str(s) + "#"
				prs.append(tmp)
		else:
			prs = list()
			tops = institution.top_entity().lines()
			for t in tops:
				result = list()
				operations = t.operations()
				nb_x = len(institution.default_period.decoup_slip()) * len(institution.default_subperiod.decoup_desc_slip())
				if institution.default_period.m_logic_type == 3:
					chronogrs = ["0_9_9_9_9_","9_0_9_9_9_","9_9_0_9_9_","9_9_9_0_9_","9_9_9_9_0_"]
					year = request.GET.get("year")
					TP1 = subperiods_value(institution.default_period,int(year))
					TP2 = list()
					dic_ops = dict()
					for t in TP1:
						a = transform_to_plannify(t)
						TP2.append(a)
						for c in chronogrs:
							dic_ops[a+"-"+c] = {
								"progress":0,
								"nb_ops":0
							}
					#operations = operations.filter(m_tache_plannification__in=TP2)

					for o in operations:
						dic_ops[o.m_tache_plannification+"-"+o.periodes().m_desc_realisation]["progress"] += o.progression()
						dic_ops[o.m_tache_plannification+"-"+o.periodes().m_desc_realisation]["nb_ops"] += 1
					for a in TP2:
						for c in chronogrs:
							if dic_ops[a+"-"+c]["nb_ops"] > 0:
								tmp = str(dic_ops[a+"-"+c]["progress"] / dic_ops[a+"-"+c]["nb_ops"])
							else:
								tmp = "0"
							result.append(tmp)
					prs.append("#".join(result))
	#progression /= len(taches)
	data = {
		'plannify':plannify,
		'result':result,
		'progression':round(progression,2)
	}
	if plannify == "#":
		data['progressions'] = prs
	return JsonResponse(data)

def ajax_calcul_date(request):
	plannify = request.GET.get('plannify')
	periode = Periode.objects.get(id=int(request.GET.get("periode")))
	tmp_val = get_period_values(periode,plannify+"_")[0]

	ta1 = datetime.date(int(tmp_val[:4]),int(tmp_val[4:6]),int(tmp_val[6:8]))
	ta2 = datetime.date(int(tmp_val[8:12]),int(tmp_val[12:14]),int(tmp_val[14:16]))
	ta3 = ta2
	test = ta2.isoweekday()
	if test > 1 :
		ta2 -= datetime.timedelta(test-1)
		ta3 += datetime.timedelta(7-test)
	test_dates =list()
	for i in range(5):
		test_dates.append("Du "+str(ta2)+" Au "+str(ta3))
		ta2 += datetime.timedelta(7)
		ta3 += datetime.timedelta(7)
	bumps1 = [int(tmp_val[:4]),int(tmp_val[4:6])-1,int(tmp_val[6:8])]
	bumps2 = [int(tmp_val[8:12]),int(tmp_val[12:14])-1,int(tmp_val[14:16])]
	data = {
		'tmp_val':tmp_val,
		'test_dates':test_dates,
		'ta1':str(ta2),
		'result':tmp_val
	}
	return JsonResponse(data)

def delete_mul(request):
	entities = request.POST["multi_values"]
	hierachy = int(request.POST['hierachy'])
	g_v = request.POST['g_v']
	try:
		g_v_2 = request.POST['g_v_2']
	except:
		g_v_2 = None

	from .utilities2 import delete_entities,delete_operations
	if g_v != "o":
		delete_entities(entities)
		response = '/gestionnaire/'+str(hierachy)
		if g_v_2 is not None:
			response = '/gestionnaire/'+str(hierachy-1)
			response += '/'+str(g_v_2)+'/'
	else:
		a=delete_operations(entities)
		response = '/taches/'+str(a.id)+'/'
	return redirect(response)

@login_required(login_url='/log_account')
def data_form(request,nature=-1,elt_id=0):
	template = "webpages/ctn_bpf/data_form.html"
	context = basis(request)
	nature = int(nature)
	context["nature"] = nature
	context["elt_id"] = elt_id
	if nature != -1:
		template = "webpages/ctn_bpf/data_form_plus.html"
		dataform = DataSet.objects.filter(id=nature,m_institution=context["actual_institution"]).first()
		context["element"] = dataform
		if dataform != None:
			next_nature = nature+1
			lines = dataform.dS_values()
		else:
			lines = list()
	else:
		next_nature = 1
		lines = DataSet.objects.filter(m_institution=context["actual_institution"])
		try:
			if context["permissions"] == 0 or context["no_simple_user"] == False:
				#role
				role = request.user.personnel.get_function(context["actual_institution"].id).m_role
				lines = lines.filter(m_roles=role)
		except:
			pass
	paginator_o = Paginator(lines,10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	#oeuvres_date
	context["g_v"] = "dSV"
	context["menu"] = "h"
	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range


	return render(request,template,context)

def error_404(request,exception):
	if request.user.is_authenticated:
		template = "webpages/ctn_bpf/errors.html"
		context = basis(request)
	else:
		template = "webpages/ctn_bpf/errors_zero.html"
		context = dict()
	context['error'] = 404
	context['exception'] = exception
	return render(request,template,context)

def error_500(request):
	if request.user.is_authenticated:
		template = "webpages/ctn_bpf/errors.html"
		context = basis(request)
	else:
		template = "webpages/ctn_bpf/errors_zero.html"
		context = dict()
	return render(request,template,context)

def extra(request,name=""):
	context=basis(request)
	if request.user.is_authenticated:
		template = "webpages/ctn_bpf/extra.html"
		files = OperaFile.objects.filter(m_institution=context["actual_institution"]).select_related("m_institution")
		bool(files)
		try:
			personnel_opera = settings.PERSONNAL_OPERA
			context["personnel_opera"] = personnel_opera
			if personnel_opera:
				context['actual_institution_name'] = settings.PERSONNAL_INSTITUTION
		except:
			personnel_opera = None
	else:
		try:
			personnel_opera = settings.PERSONNAL_OPERA
			context["personnel_opera"] = personnel_opera
			if personnel_opera:
				context['actual_institution_name'] = settings.PERSONNAL_INSTITUTION
		except:
			personnel_opera = None
		template = "webpages/ctn_bpf/extra.html"	
		files = OperaFile.objects.filter(is_public=1)
		bool(files)
	if name != None:
		tmp1 = files.filter(m_name__contains=name) 
		tmp2 = list()#files.filter(m_file__url__contains=name)
		files = list()
		for t in tmp1:
			files.append(t)
		for t in tmp2:
			files.append(t)
	paginator_o = Paginator(files,10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	#oeuvres_date
	context["g_v"] = "ex"
	context["menu"] = "x"
	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range
	return render(request,template,context)

def get_progressions(request):
	list_ids = request.GET.get('list_ids').split("#")[:-1]
	list_ids = [ int(i) for i in list_ids]
	entities = Entity.objects.filter(id__in=list_ids)

	result = list()
	data_ids = list()
	type_Progression = request.GET.get("type_progression")
	if type_Progression == "P":
		for i in entities: 
			result.append(i.progression())
			data_ids.append(str(i.id))
	elif  type_Progression == "T":
		for i in entities: 
			result.append(i.technical_progression())
			data_ids.append(str(i.id))
	elif  type_Progression == "F":
		for i in entities: 
			result.append(i.finan_progression())
			data_ids.append(str(i.id))
	data = {
		'result':result,
		'ids':data_ids
	}
	return JsonResponse(data,safe=False)

def get_indi_data(request):
	data_id = request.GET.get('indi_id')
	ind = Indicateur.objects.get(id=int(data_id))
	nums = list()
	ids = list()
	for i in ind.indi_numerateur():
		nums.append(str(i))
		ids.append(i.id)
	denums = list()
	for i in ind.indi_denum():
		denums.append(str(i))

	period = ind.m_periodicite
	sub_period = ind.m_sub_periodicite
	cibles = ind.m_cibles
	data = {
		'nom':str(ind),
		'nums':nums,
		'denums':denums,
		'ids':ids
	}
	return JsonResponse(data,safe=False)


def consult_oper(request):
	operation = Operation.objects.get(id=int(request.POST["operation"]))
	nb_stars = request.POST["nb_stars"]
	
	request.session['new_rapport'] = 2
	observations = request.POST["observations"]
	oC = OperationConsulted(m_operation=operation,m_stars=nb_stars,m_observations=observations)
	oC.save()
	return redirect("/operations/")

@login_required(login_url='/log_account')
def personnels_raci(request,name=None):
	template = "webpages/ctn_bpf/persos_raci.html"
	context = basis(request)
	context['g_vs'] = 'p2'
	context['g_v'] = 'p2_RACI'

	context['searches'] = []
	context['searches'].append({'label':'Fonction','values':Role.objects.filter(actual_institution=context['actual_institution']).select_related('actual_institution')})
	context['searches'].append({'label':'Structure','values':Structure.objects.filter(institution=context['actual_institution']).select_related('institution')})

	ents = list()
	ieS = list(context['actual_institution'].get_entities())
	bool(ieS)
	#n = ieS.count()
	j=0

	for i in ieS[:-2]:
		if True:
			tmp = {
				"hierachie":i.m_hierachie,
				"label":str(i),
				'entities':list()
			}
			if j == 0:
				tmp["entities"] = ieS[0].m_entity_type.lines()
			ents.append(tmp)
			j+=1
		else:
			pass
	context['ents'] = ents

	#context['matieres'] = ies[-2].lines() 

	elements = list()
	tmps = Personnel.objects.filter()
	for t in tmps:
		if context['actual_institution'] in t.all_institutions():
			elements.append(t)

	akas=list()
	tmp_perso = Personnel.objects.filter()
	#pFs = Personnel_Function.objects.filter(m_institution=context["actual_institution"]).values("m_personnel")

	if True :
		for t in tmp_perso:
			if context['actual_institution'] in t.all_institutions():
				atmp = {
				'id':t.id,
				'prenom':t.prenom,
				'nom':t.nom,
				'photo':t.photo,
				'get_function':t.get_function(context['actual_institution'].id),
				'RACI_entities':t.RACI_entities()
				}
				akas.append(atmp)
				#lines2.add(t)
	else:
		context['lines'] = lis_peros

	if name != None:
		name = name.lower()
		tmps = akas
		akas = list()
		context['lines'] = list()
		for tt in tmps:
			ta = (tt["prenom"].lower()+tt["nom"].lower()).split(" ")
			for t in ta: 
				if name in str(t):
					akas.append(tt)
					break

	paginator_o = Paginator(akas,10)
	page_number_o = request.GET.get('page')
	elements_page = paginator_o.get_page(page_number_o)
	#oeuvres_date

	context['pages_o']=elements_page
	context['num_pages']=paginator_o.num_pages
	context['page_range']=paginator_o.page_range
	return render(request,template,context)

def data_sets(request,indi_id=0):
	context = basis(request)
	indicateurs = Indicateur.objects.filter(m_institution=context["actual_institution"])
	template = "webpages/ctn_bpf/data_sets.html"
	context["dataelts"] = DataElement.objects.filter(m_institution=context["actual_institution"])
	context["indicateurs"] = indicateurs
	context["menu"] = "h"
	if indi_id != 0:
		dataset = DataSet.objects.get(id=int(indi_id))
		context["dataset"] = dataset
	"""
	context["indicateur"] = indicateur
	context["element"]= indicateur.m_enti
	context["indi_id"] = indi_id
	"""
	return render(request,template,context)

def data_sets_design(request,dS_id):
	data_set = DataSet.objects.get(id=dS_id)
	template = "webpages/ctn_bpf/data_sets_design.html"
	context = basis(request)
	context["dataset"] = data_set
	context["design"] = 1
	return render(request,template,context)

def ajax_form(request):
	dF = DataSet.objects.get(id=int(request.GET.get("id_dataset")))
	#dF = indicateur.dataset()
	structures = list()
	structure_id = list()
	for s in dF.m_structures.filter():
		structures.append(str(s))
		structure_id.append(s.id)
	data = {
		'periode':dF.m_periode,
		'subperiode':dF.m_sub_periode,
		'structures':structures,
		'structures_id':structure_id,
		'form':dF.m_formulaire
	}
	return JsonResponse(data,safe=False)

def ajax_hiera_struc(request):
	institution = request.GET.get("institution")
	logic_strc = request.GET.get("logic_strc")
	m_institution = Institution.objects.get(id=int(institution))
	elt_logic = ""
	for e in logic_strc.split("|")[:-1]:
		a = e.split("#")
		if len(a)>1:
			elt_logic += a[1]+"|"
		else:
			elt_logic += a[0]+"|"
	structures = Structure.objects.filter(institution=m_institution,values_hierachy__contains=elt_logic)
	data = {
		'ids':list(),
		'names':list()
	}
	data["nb_s"] = elt_logic
	for s in structures:
		data["ids"].append(s.id)
		data["names"].append(str(s))
	return JsonResponse(data,safe=False)


def ajax_RACI_user(request):
	type_RACI = request.GET.get("type_RACI")
	perso = request.GET.get("perso")
	institution = request.GET.get("institution")
	entity_filter = request.GET.get("entity_filter")

	data = dict()
	if type_RACI == "1":
		personnel = Personnel.objects.get(id=int(perso))
		rEL = list()
		data["elts"] = list()
		data["elts_id"] = list()
		data["elts_hierachy"] = list()

		if entity_filter not in ["0",None]:
			entity_filter = int(entity_filter)
			pR = PersonnelRACI.objects.get(id=entity_filter)
			data["elt_actu_id"] = str(pR.m_entity)
			data["elt_actu"] = pR.m_entity.id
		else:
			data["elt_actu_id"] = "#"
			data["elt_actu"] = "#"

		for p in personnel.get_function(institution).m_role.entity_levels():
			rEL.append(str(p))
			data["elts_hierachy"].append(p.m_hierachie)
			tmp_elt = list()
			tmp_id = list()
			for p2 in p.m_entity_type.lines():
				tmp_elt.append(str(p2))
				tmp_id.append(int(p2.id))
			data["elts"].append(tmp_elt)
			data["elts_id"].append(tmp_id)
		data["roles"] = rEL
		#data["test_rEL"] = rEL
	return  JsonResponse(data,safe=False)


def ajax_RACI_user_manage(request):
	menu = request.GET.get("menu")
	#entity = Entity.objects.get(id=int(request.GET.get("entity")))
	if menu == "o":
		tache = Tache.objects.get(id=int(request.GET.get("entity")))	
		perRACI = tache.personnelRACI()	
		data = {
			"responsable":perRACI["responsable"],
			"accounted":perRACI["accounted"],
			"consulted":perRACI["consulted"],
			"informed":perRACI["informed"],
			"test":""
		}
		allis = ["responsable","accounted","consulted","informed"]
		for s in tache.sup_hierachie():
			all_none = False
			perRACI = s.personnelRACI()
			for al in allis:
				data["test"] += str(perRACI[al]) + "#"
				if data[al] == [None]:
					all_none = True
					if perRACI[al] != [None] :
						data[al] = perRACI[al][1].id
				if all_none == False:
					break
	return JsonResponse(data,safe=False)

def assign_RACI(request):
	personnel = Personnel.objects.get(id=int(request.POST["perso_assign"]))
	values_assign = request.POST["values_assign"].split("$")
	try:
		operations_check = request.POST["operations_recursive"]
	except:
		operations_check = None 
	for v in values_assign[:-1]:
		#entity = Entity.objects.get(id=int(v.split("#")[0]))
		entity = int(v.split("#")[0].replace("'",""))
		entity = Entity.objects.get(id= entity)
		raci_role = v.split("#")[1]
		if "1" in raci_role:
			if operations_check != None:
				operations = entity.operations()
				rs = raci_role.split("|")
				for o in operations:
					if rs[0] == "1":
						o.personnel = personnel
					if rs[1] == "1":
						o.accountable = personnel
					if rs[2] == "1":
						o.consulted = personnel
					if rs[3] == "1":
						o.informed = personnel
					o.save()
			pR = PersonnelRACI(m_personnel = personnel, m_entity = entity, m_roles =raci_role)

			pR.save()
	return redirect("/personnels_raci/")

def print_pdf(request):
	name_pdf = request.GET.get("name_pdf")
	html = request.GET.get("html")
	html = html.replace("<table","<table border='1' width='100%' cellpadding='5px'")
	html = html.replace("<td","<td width='100' ")
	html = html.replace("<th","<th width='100' ")

	data = dict()

	class MyFPDF(FPDF, HTMLMixin):
		pass
	pdf = MyFPDF()
	pdf.add_page()
	pdf.write_html(html)
	pdf.output('html3.pdf', 'F')
	return JsonResponse(data,safe=False)