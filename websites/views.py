from django.shortcuts import render,redirect
from django.conf import settings
from .models import *
# Create your views here.
def index(request):
	template = "websites/index.html"
	context = {
		'site':0
	}
	
	return redirect("http://beininfoplus.com") #render(request,template,context)

def vaccins(request):
	pass

def maladies(request,maladie_id=None):
	pass

def calendar_vac(request):
	pass