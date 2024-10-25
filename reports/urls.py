from django.urls import path
from . import views

app_name = 'reports'
urlpatterns = [
    # URL to load the report dashboard
    path('dashboard/', views.report_dashboard, name='report_dashboard'),
    
    path('individual/', views.individual_progress_report, name='individual_report'),
    path('course/', views.course_progress_report, name='course_report'),
    path('overall/', views.overall_progress_report, name='overall_report'),
    path('top/', views.top_performers_report, name='top_performers_report'),
    path('risk/', views.at_risk_students_report, name='at_risk_students_report'),
    path('last/', views.last_accessed_report, name='last_accessed_report'),
]
