from django.db import models
from django.contrib.auth.models import User

# Create your models here.
import datetime
class New(models.Model):
	m_title = models.CharField(max_length=128,blank=True,null=True)
	m_author = models.OneToOneField(User,blank=True,null=True,on_delete=models.CASCADE)
	m_date_posted = models.DateTimeField(blank=True,null=True)
	m_cover_picture = models.FileField(blank=True,null=True)
	m_template = models.TextField(blank=True,null=True)

class Vaccin(models.Model):
	m_nom = models.CharField(max_length=128,blank=True,null=True)
	m_description = models.TextField(blank=True,null=True)
	m_elt_tables  = models.TextField(blank=True,null=True)

class Maladie(models.Model):
	m_nom = models.CharField(max_length=128,blank=True,null=True)
	m_description = models.TextField(blank=True,null=True)
	m_mode_de_transmission = models.TextField(blank=True,null=True)
	m_signes_et_symptomes = models.TextField(blank=True,null=True)
	m_manifeste = models.TextField(blank=True,null=True)
	m_complications = models.TextField(blank=True,null=True)
	m_traitement = models.TextField(blank=True,null=True)
	m_prevention = models.TextField(blank=True,null=True)
	is_active = models.BooleanField(blank=True,null=True,default=False)

class Contact(models.Model):
	m_phone  = models.TextField(blank=True,null=True)
	m_mail = models.TextField(blank=True,null=True)
	m_networks = models.TextField(blank=True,null=True)

class Partenaire(models.Model):
	#OMS, GAVI, UNFPA, MINSANTE, GIZ, UNESCO
	m_logo = models.FileField(blank=True,null=True)
	m_nom = models.CharField(max_length=128,blank=True,null=True)