from django.shortcuts import render
from course.models import UserCourseProgress
from django.db.models import Avg

# Render the dashboard page
def report_dashboard(request):
    return render(request, 'report_dashboard.html')

# Individual Progress Report
def individual_progress_report(request):
    user_progress = UserCourseProgress.objects.filter(user_id=1)  # Example
    return render(request, 'reports/individual_progress_report.html', {'user_progress': user_progress})

# Course Progress Report
def course_progress_report(request):
    course_progress = UserCourseProgress.objects.filter(course_id=1).order_by('-progress_percentage')  # Example
    return render(request, 'reports/course_progress_report.html', {'course_progress': course_progress})

# Overall Progress Report
def overall_progress_report(request):
    overall_progress = UserCourseProgress.objects.values('user__username', 'course__name').annotate(
        avg_progress=Avg('progress_percentage')
    ).order_by('course__name')
    return render(request, 'reports/overall_progress_report.html', {'overall_progress': overall_progress})

# Top Performers Report
def top_performers_report(request):
    top_performers = UserCourseProgress.objects.order_by('-progress_percentage')[:10]
    return render(request, 'reports/top_performers_report.html', {'top_performers': top_performers})

# At-Risk Students Report
def at_risk_students_report(request):
    at_risk_students = UserCourseProgress.objects.filter(progress_percentage__lt=50).order_by('progress_percentage')
    return render(request, 'reports/at_risk_students_report.html', {'at_risk_students': at_risk_students})

# Last Accessed Report
def last_accessed_report(request):
    last_accessed = UserCourseProgress.objects.order_by('-last_accessed')
    return render(request, 'reports/last_accessed_report.html', {'last_accessed': last_accessed})
