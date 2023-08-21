from django.urls import path
from . import views
app_name = 'websites'

urlpatterns = [
	path('',views.index,name ='index'),
	path("vaccins/",views.vaccins,name="vaccins"),
	path("maladies/",views.maladies,name="maladies"),
	path("maladies/<int:maladie_id>/",views.maladies,name="maladies_detail"),
]