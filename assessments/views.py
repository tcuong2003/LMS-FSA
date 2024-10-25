from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from course.models import Course
from quiz.models import Question
from .models import Assessment,  StudentAssessmentAttempt, AnswerOption, UserAnswer, UserSubmission, StudentAssessmentAttempt, InvitedCandidate
from .forms import AssessmentForm, AssessmentAttemptForm, InviteCandidatesForm
from exercises.models import Exercise

from django.urls import reverse
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from .tokens import invite_token_generator  # Adjust the import path as necessary
from django.utils.encoding import force_str
from django.db import transaction
from django.core.exceptions import ValidationError
from exercises.libs.submission import grade_submission, precheck
from exercises.models import Submission

#Working
def submit_code(request, exercise_id):
    exercise = get_object_or_404(Exercise, id=exercise_id)
    if request.method == "POST":
        form = Submission(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.student = request.user
            submission.exercise = exercise
            submission.save()
            result = grade_submission(submission)
            submission.score = result['score']
            submission.save()
            return redirect('exercises:result_detail', submission_id=submission.id)
        else:
            print(form.errors)  # Print form errors to debug
            print(request.POST)  # Print form data for debugging
    return redirect('exercises:exercise_list')

@login_required
def take_assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    questions = assessment.questions.all()  # Get all questions in the assessment
    exercises = assessment.exercises.all()  # Assuming you have a related exercise model
    total_marks = assessment.total_score
    total_questions = questions.count()  # Count all questions 
    attempt_id = None  # Initialize as None

    if not request.user.is_authenticated:
        if request.method == 'POST':
            # User isn't logged in, so we expect an email to be provided
            email = request.POST.get('email')
            if not email:
                return render(request, 'assessment/take_assessment.html', {
                    'assessment': assessment,
                    'questions': questions,
                    'exercises': exercises,
                    'error': 'Email is required for taking this assessment.',
                })
            
            # Validate email format (simple validation)
            try:
                from django.core.validators import validate_email
                validate_email(email)
            except ValidationError:
                return render(request, 'assessment/take_assessment.html', {
                    'assessment': assessment,
                    'questions': questions,
                    'exercises': exercises,
                    'error': 'Please provide a valid email address.',
                })
        else:
            # Display form with email input if not POST
            return render(request, 'assessment/take_assessment.html', {
                'assessment': assessment,
                'questions': questions,
                'exercises': exercises,
                'anonymous': True  # Indicator for showing the email field in the template
            })

    if request.method == 'POST':
        with transaction.atomic():
            # If the user is authenticated, use the logged-in user, otherwise use the email for tracking
            user = request.user if request.user.is_authenticated else None
            email = request.POST.get('email') if not request.user.is_authenticated else None

            attempt = StudentAssessmentAttempt.objects.create(
                user=user,
                email=email,  # Track by email if not logged in
                assessment=assessment,
                score_quiz=0.0,
                score_ass=0.0
            )

            correct_answers = 0

            # Process questions
            for question in questions:
                selected_option_id = request.POST.get(f'question_{question.id}')
                text_response = request.POST.get(f'text_response_{question.id}')
                selected_option = None

                if selected_option_id and selected_option_id.isdigit():
                    selected_option = AnswerOption.objects.get(id=int(selected_option_id))

                # Save the student's answer
                UserAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_option=selected_option,
                    text_response=text_response
                )

                if selected_option and selected_option.is_correct:
                    correct_answers += 1

            total_exercise_score = 0
            # Process exercises
            for exercise in exercises:
                exercise_response = request.POST.get(f'exercise_{exercise.id}')
                
                # Create a UserSubmission object for each exercise response
                if exercise_response:  # Check if there is a response for the exercise
                    UserSubmission.objects.create(
                        exercise=exercise,
                        user=user,  # Use the logged-in user or None for anonymous
                        email=email,  # Use the email for tracking if anonymous
                        code=exercise_response  # Store the response in the code field
                    )
                total_exercise_score +=1

            attempt.score_quiz = (total_marks / total_questions) * correct_answers
            attempt.score_ass = total_exercise_score
            attempt.save()
            attempt_id = attempt.id  # Store the attempt_id after saving the attempt

            return redirect('assessment:assessment_result', assessment_id=assessment.id, attempt_id=attempt_id)

    # Render the assessment page with questions and exercises
    return render(request, 'assessment/take_assessment.html', {
        'assessment': assessment,
        'questions': questions,
        'exercises': exercises,
        'attempt_id': attempt_id,  # This will be None for GET request
        'anonymous': not request.user.is_authenticated  # Pass a flag to show email input in the template
    })

@login_required
def take_assessment_bk(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    questions = assessment.questions.all()  # Get all questions in the assessment
    exercises = assessment.exercises.all()  # Assuming you have a related exercise model
    total_marks = assessment.total_score
    total_questions = questions.count()   # Count all questions 
    attempt_id = None  # Initialize as None
    
    if request.method == 'POST':
        with transaction.atomic():
            attempt = StudentAssessmentAttempt.objects.create(user=request.user, assessment=assessment, score_quiz=0.0, score_ass=0.0)

            correct_answers = 0
            
            # Process questions
            for question in questions:
                selected_option_id = request.POST.get(f'question_{question.id}')
                text_response = request.POST.get(f'text_response_{question.id}')
                selected_option = None

                if selected_option_id and selected_option_id.isdigit():
                    selected_option = AnswerOption.objects.get(id=int(selected_option_id))

                # Save the student's answer
                UserAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_option=selected_option,
                    text_response=text_response 
                )

                if selected_option and selected_option.is_correct:
                    correct_answers += 1

            # Process exercises
            for exercise in exercises:
                exercise_response = request.POST.get(f'exercise_{exercise.id}')
                
                # Create a UserSubmission object for each exercise response
                if exercise_response:  # Check if there is a response for the exercise
                    UserSubmission.objects.create(
                        exercise=exercise,
                        user=request.user,  # Assuming you're getting the logged-in user from the request
                        code=exercise_response  # Store the response in the code field
                    )

            final_score = (total_marks / total_questions) * correct_answers

            attempt.score_quiz = final_score
            attempt.score_ass = final_score
            attempt.save()
            attempt_id = attempt.id  # Store the attempt_id after saving the attempt

            return redirect('assessment:assessment_result', assessment_id=assessment.id, attempt_id=attempt_id)

    # Render the assessment page with questions and exercises
    return render(request, 'assessment/take_assessment.html', {
        'assessment': assessment,
        'questions': questions,
        'exercises': exercises,
        'attempt_id': attempt_id  # This will be None for GET request
    })



@login_required
def assessment_result(request, assessment_id, attempt_id):
    # Get the assessment object and the user's attempt
    assessment = get_object_or_404(Assessment, id=assessment_id)
    attempt = get_object_or_404(StudentAssessmentAttempt, id=attempt_id, user=request.user)

    # Get all user answers for this attempt
    user_answers = UserAnswer.objects.filter(attempt=attempt)

    # Get all user submissions for exercises related to this assessment
    user_submissions = UserSubmission.objects.filter(exercise__assessments=assessment, user=request.user)


    # Calculate the total score (already stored in the attempt object)
    score_ass = attempt.score_ass
    score_quiz = attempt.score_quiz

    context = {
        'assessment': assessment,
        'attempt': attempt,
        'user_answers': user_answers,
        'user_submissions': user_submissions,
        'score_ass': score_ass,
        'score_quiz': score_quiz,
    }

    # Render the result page
    return render(request, 'assessment/assessment_result.html', context)

def assessment_invite_accept(request, uidb64, token):
    try:
        # Decode the uidb64 to get the InvitedCandidate ID
        uid = force_str(urlsafe_base64_decode(uidb64))
        invited_candidate = InvitedCandidate.objects.get(pk=uid)

        # Check if the token is valid
        if invite_token_generator.check_token(invited_candidate, token):
            # Check if the invitation is expired
            if invited_candidate.expiration_date >= timezone.now():
                # Invitation is valid, redirect to assessment
                assessment = invited_candidate.assessment
                return render(request, 'assessment/take_assessment.html', {'assessment': assessment})
            else:
                messages.error(request, "This invitation link has expired.")
                return redirect('assessment:assessment_list')  # Redirect as appropriate
        else:
            messages.error(request, "This invitation link is invalid.")
            return redirect('assessment:assessment_list')  # Redirect as appropriate
    except (TypeError, ValueError, OverflowError, InvitedCandidate.DoesNotExist):
        messages.error(request, "This invitation link is invalid.")
        return redirect('assessment:assessment_list')  # Redirect as appropriate


@login_required
def invite_candidates(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)

    if request.method == 'POST':
        form = InviteCandidatesForm(request.POST)
        if form.is_valid():
            emails = form.cleaned_data['emails'].split(',')
            emails = [email.strip() for email in emails if email.strip()]

            # Track invited candidates to avoid duplicates
            invited_candidates = []

            for email in emails:
                # Check if the email is already invited
                if not InvitedCandidate.objects.filter(assessment=assessment, email=email).exists():
                    invited_candidate = InvitedCandidate.objects.create(
                        assessment=assessment,
                        email=email
                    )
                    invited_candidate.set_expiration_date(days=7)  # Set expiration to 7 days
                    invited_candidate.save()

                    # Generate a token with an expiration time
                    token = invite_token_generator.make_token(invited_candidate)
                    uid = urlsafe_base64_encode(force_bytes(invited_candidate.pk))

                    # Create the invite URL with the token
                    invite_link = request.build_absolute_uri(
                        reverse('assessment:assessment_invite_accept', kwargs={'uidb64': uid, 'token': token})
                    )

                    # Send the invite email with the token link
                    send_mail(
                        subject=f"You're invited to complete an assessment: {assessment.title}",
                        message=f"Please click the link below to access the assessment. This link will expire in 7 days.\n\n{invite_link}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                    )

                    # Track the invited candidate
                    invited_candidates.append(invited_candidate)

            # Update invited_count based on the number of unique invited candidates
            assessment.invited_count += len(invited_candidates)
            assessment.save()

            return redirect('assessment:assessment_list')

    else:
        form = InviteCandidatesForm()

    return render(request, 'assessment/invite_candidates.html', {
        'form': form,
        'assessment': assessment,
    })



@login_required
def assessment_detail(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)
    
    # Query invited candidates for this assessment
    invited_candidates = InvitedCandidate.objects.filter(assessment=assessment)
   
    # Query attempts from registered users
    registered_attempts = StudentAssessmentAttempt.objects.filter(assessment=assessment)
    
    # Query attempts from non-registered candidates
    non_registered_attempts = NonRegisteredCandidateAttempt.objects.filter(assessment=assessment)

    return render(request, 'assessment/assessment_detail.html', {
        'assessment': assessment,
        'invited_candidates': invited_candidates,
        'registered_attempts': registered_attempts,
        'non_registered_attempts': non_registered_attempts,
    })


@login_required
def assessment_create(request):
    query = request.GET.get('search', '')
    exercises = Exercise.objects.filter(title__icontains=query)  # Filter exercises based on search query
    questions = Question.objects.filter(question_text__icontains=query)  # Filter questions based on search query
  
    paginator = Paginator(exercises, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        form = AssessmentForm(request.POST)
        selected_exercises = request.POST.getlist('exercises')  # Get selected exercises from form
        selected_questions = request.POST.getlist('questions')  # Get selected questions from the form

        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.created_by = request.user
            assessment.save()
            form.save_m2m()  # Save ManyToMany relationships

            # Add selected exercises to the assessment
            for exercise_id in selected_exercises:
                exercise = get_object_or_404(Exercise, id=exercise_id)
                assessment.exercises.add(exercise)  # Add the exercises to assessment

            # Add selected questions to the assessment
            for question_id in selected_questions:
                question = get_object_or_404(Question, id=question_id)
                assessment.questions.add(question)  # Add questions to the assessment

            messages.success(request, 'Assessment created successfully with exercises!')
            return redirect('assessment:assessment_list')

    else:
        form = AssessmentForm()

    return render(request, 'assessment/assessment_form.html', {
        'form': form,
        'exercises': exercises,
        'questions': questions,
        'page_obj': page_obj,
        'selected_exercises': [],  # Initially no exercises selected
        'selected_questions': [],  # Initially no questions selected
        'search': query
    })


@login_required
def assessment_edit(request, pk):
    assessment = get_object_or_404(Assessment, id=pk)
    
    # Fetch all available exercises and questions
    exercises = Exercise.objects.all()
    questions = Question.objects.all()
    
    # Fetch selected exercises and questions for the assessment
    selected_exercises = assessment.exercises.values_list('id', flat=True)
    # selected_questions = assessment.questions.values_list('id', flat=True)
    selected_question_ids = assessment.questions.values_list('id', flat=True)
    selected_questions = Question.objects.filter(id__in=selected_question_ids)  # Fetching the actual Question objects
    
    # selected_questions = assessment.questions.all()  # Fetching selected Question objects
    if request.method == "POST":
        form = AssessmentForm(request.POST, instance=assessment)
        
        if form.is_valid():
            form.save()

            # Update associated exercises
            selected_exercise_ids = request.POST.getlist('exercises')
            assessment.exercises.set(selected_exercise_ids)  # Update the associated exercises
            
            # Update associated questions from the selected questions in the HTML
            selected_question_ids = request.POST.get('selected_questions', '').split(',')
            selected_question_ids = [q_id for q_id in selected_question_ids if q_id]  # Filter out empty strings
            
            assessment.questions.set(selected_question_ids)  # Update the associated questions
            
            assessment.save()

            messages.success(request, 'The assessment has been successfully saved.')
            return redirect('assessment:assessment_edit', pk=pk)  # Redirect to the same edit page to see the message

    else:
        form = AssessmentForm(instance=assessment)

    return render(request, 'assessment/assessment_form.html', {
        'form': form,
        'assessment': assessment,
        'exercises': exercises,
        'questions': questions,
        'selected_exercises': selected_exercises,
        'selected_questions': selected_questions, 
    })

@login_required
def assessment_list(request):
    #quizzes = Quiz.objects.select_related('course').annotate(question_count=Count('questions')).all().order_by('-created_at')
    courses = Course.objects.all().order_by('course_name')
    assessments = Assessment.objects.all().order_by('created_at')

    # Lọc quiz dựa trên subject được chọn
    selected_course = request.GET.get('course', '')
    if selected_course:
        assessments = assessments.filter(course__id=selected_course)
  
    
    # Dynamically calculate exercise and question counts for each assessment
    assessments_with_counts = []
    for assessment in assessments:
        # Assuming you have related models for exercises and questions
        exercise_count = assessment.exercises.count()  # Assuming 'exercises' is a related field
        question_count = assessment.questions.count()  # Assuming 'questions' is a related field in exercises
        assessments_with_counts.append({
            'selected_course': selected_course,
            'assessment': assessment,
            'exercise_count': exercise_count,
            'question_count': question_count,
        })

    # Pass the assessments with their exercise and question counts to the template
    return render(request, 'assessment/assessment_list.html', {
        'courses': courses,
        'assessments_with_counts': assessments_with_counts,
    })


def get_exercise_content(request, exercise_id):
    exercise = Exercise.objects.get(id=exercise_id)
    return JsonResponse({
        'title': exercise.title,
        'content': exercise.description  
    })






@login_required
def student_assessment_attempt(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    if request.method == 'POST':
        form = AssessmentAttemptForm(request.POST)
        if form.is_valid():
            attempt = form.save(commit=False)
            attempt.user = request.user
            attempt.assessment = assessment
            attempt.save()
            messages.success(request, 'Your attempt has been recorded.')
            return redirect('assessment:assessment_detail', pk=assessment.id)
    else:
        form = AssessmentAttemptForm()
    return render(request, 'assessment/assessment_attempt_form.html', {'form': form, 'assessment': assessment})
