from django.urls import path
from . import views

app_name ="activity"

urlpatterns = [
    path('', views.activity_view, name = "activity_view")
]