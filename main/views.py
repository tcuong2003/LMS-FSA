from django.shortcuts import render, redirect
from .forms import RegistrationForm, CustomLoginForm, EmailForm, ConfirmationCodeForm
from django.contrib.auth import authenticate, login
from user.models import User, Profile, Role
from module_group.models import Module, ModuleGroup
from django.db.models import Q
from module_group.forms import ExcelImportForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from .forms import PasswordResetRequestForm, PasswordResetCodeForm, PasswordResetForm
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import random
from django.core.cache import cache
from django.conf import settings

def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                random_code = get_random_string(length=6)

                request.session['reset_code'] = random_code
                request.session['user_id'] = user.id
                request.session['email'] = email
                request.session['code_created_at'] = timezone.now().isoformat()

                send_mail(
                    'Password Reset Code',
                    f'Your code is: {random_code}',
                    'from@example.com',
                    [email],
                    fail_silently=False,
                )
                return redirect('main:password_reset_code')
            except User.DoesNotExist:
                messages.error(request, 'Email does not exist.')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'password_reset.html', {'form': form, 'current_step': 'request'})

def get_remaining_time(created_at, expiration_duration_minutes):
    if created_at:
        created_at = timezone.datetime.fromisoformat(created_at)
        if created_at.tzinfo is None:
            created_at = timezone.make_aware(created_at)

        expiration_time = created_at + timedelta(minutes=expiration_duration_minutes)
        remaining_time = expiration_time - timezone.now()

        if remaining_time.total_seconds() >= 0:
            minutes = remaining_time.seconds // 60
            seconds = remaining_time.seconds % 60  
            return remaining_time, minutes, seconds

    return None, 0, 0

def password_reset_code(request):
    created_at = request.session.get('code_created_at')
    expiration_duration_minutes = 0.5  

    
    remaining_time, minutes, seconds = get_remaining_time(created_at, expiration_duration_minutes)

    if request.method == 'POST':
        form = PasswordResetCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            session_code = request.session.get('reset_code')

            if session_code and created_at:
                if code == session_code and remaining_time and remaining_time.total_seconds() > 0:
                    messages.success(request, 'The verification code is valid. Please enter a new password.')
                    return redirect('main:password_reset_form')
                else:
                    messages.error(request, 'The code has expired or is invalid.')
            else:
                messages.error(request, 'The code is invalid.')
        else:
            messages.error(request, 'An error occurred. Please check your code.')
    else:
        form = PasswordResetCodeForm()


    return render(request, 'password_reset.html', {
        'form': form,
        'current_step': 'code',
        'remaining_time': remaining_time,
        'minutes': minutes,
        'seconds': seconds  # Gửi seconds dưới dạng số nguyên
    })

def resend_code_auto(request):
    email = request.session.get('email')

    if email:
        user = User.objects.filter(email=email).first()
        
        if user:
            random_code = get_random_string(length=6)

            request.session['reset_code'] = random_code
            request.session['code_created_at'] = timezone.now().isoformat()

            try:
                send_mail(
                    'Password Reset Verification Code',
                    f'Your verification code is: {random_code}',
                    'no-reply@yourdomain.com',
                    [email],
                    fail_silently=False,
                )

                messages.success(request, 'The verification code has been resent to your email.')
            except Exception as e:
                messages.error(request, f'Failed to send email: {str(e)}')
        else:
            messages.error(request, 'User with this email does not exist.')
    else:
        messages.error(request, 'Email not found. Please try again.')

    return redirect('main:password_reset_code')

def password_reset_form(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user_id = request.session.get('user_id')
            if user_id:
                user = User.objects.get(id=user_id)
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Password updated successfully.')
                del request.session['reset_code']
                del request.session['user_id']
                return redirect('main:home')
    else:
        form = PasswordResetForm()
    
    return render(request, 'password_reset.html', {'form': form, 'current_step': 'reset'})


def register_email(request):
    if request.method == 'POST':
        email_form = EmailForm(request.POST)
        if email_form.is_valid():
            email = email_form.cleaned_data['email']
            confirmation_code = random.randint(1000, 9999)  # Tạo mã xác thực
            request.session['confirmation_code'] = confirmation_code
            request.session['email'] = email
            
            # Gửi mã xác thực qua email
            send_mail(
                'Account Registration Successful',
                f'Hello,\n\n'
                f'You have successfully registered an account on the system.\n\n'
                f'Your confirmation code is: {confirmation_code}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return redirect('main:register_confirmation_code')
    else:
        email_form = EmailForm()
    
    return render(request, 'register_email.html', {'form': email_form})

def user_exists(email):
    return User.objects.filter(email=email).exists()

def register_confirmation_code(request):
    if request.method == 'POST':
        confirmation_code_form = ConfirmationCodeForm(request.POST)
        if confirmation_code_form.is_valid():
            code = confirmation_code_form.cleaned_data['confirmation_code']
            if code == str(request.session.get('confirmation_code')):
                # Lấy email từ session
                email = request.session.get('email')

                # Kiểm tra xem người dùng đã tồn tại chưa
                if user_exists(email):
                    messages.error(request, "Email này đã được sử dụng. Vui lòng đăng nhập hoặc sử dụng email khác!")
                    return redirect('main:register_email')

                # Lưu email vào session để sử dụng sau
                request.session['email_verified'] = email

                messages.success(request, "Xác thực email thành công! Vui lòng điền thông tin đăng ký.")
                return redirect('main:register_user_info')  # Chuyển hướng đến thông tin người dùng
            else:
                messages.error(request, "Mã xác thực không hợp lệ.")
    else:
        confirmation_code_form = ConfirmationCodeForm()
    
    return render(request, 'register_confirmation_code.html', {'form': confirmation_code_form})

def register_user_info(request):
    if request.method == 'POST':
        user_form = RegistrationForm(request.POST)
        if user_form.is_valid():
            email = request.session.get('email_verified')
            
            # Kiểm tra xem người dùng đã tồn tại chưa
            if user_exists(email):
                messages.error(request, "Người dùng đã tồn tại với email này!")
                return redirect('main:register_email')

            user = user_form.save(commit=False)  # Không lưu ngay
            user.email = email  # Lưu email vào user
            user.set_password(user_form.cleaned_data.get('password1'))  # Lưu mật khẩu đã mã hóa
            user.save()  # Lưu user
            
            # Tạo Profile cho user
            profile = Profile.objects.create(user=user)  # Chỉ tạo Profile
            
            # Gán vai trò mặc định là User
            default_role = Role.objects.get(role_name='User')  # Thay 'User' bằng tên vai trò đúng nếu cần
            profile.role = default_role
            profile.email_verified = True  # Đánh dấu email là đã xác thực
            profile.save()  # Lưu Profile với vai trò mặc định

            # Lưu user_id vào session
            request.session['user_id'] = user.id  # Lưu ID người dùng vào session
            
            messages.success(request, "Đăng ký thành công!")
            return redirect('main:login')
    else:
        user_form = RegistrationForm()
    
    return render(request, 'register_user_info.html', {'form': user_form})




def login_view(request):
    selected_role = request.POST.get('role', '')

    if request.method == 'POST':
        form = CustomLoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Đăng nhập người dùng
                login(request, user)

                if user.is_superuser:
                    return redirect('/admin/')  # Chuyển hướng đến admin nếu là superuser

                user_role = user.profile.role.role_name

                # Kiểm tra xem role đã chọn có khớp với role của người dùng không
                if user_role == selected_role:
                    messages.success(request, "Đăng nhập thành công!")
                    next_url = request.GET.get('next', 'main:home')
                    return redirect(next_url)
                else:
                    messages.error(request, "Vai trò không khớp với vai trò tài khoản của bạn.")
            else:
                messages.error(request, "Tên đăng nhập hoặc mật khẩu không hợp lệ.")
        else:
            messages.error(request, "Mẫu không hợp lệ.")
    else:
        form = CustomLoginForm()

    roles = Role.objects.all()
    return render(request, 'login.html', {
        'form': form,
        'roles': roles,
        'selected_role': selected_role if not request.user.is_superuser else ''
    })



def home(request):
    query = request.GET.get('q')
    all_modules = Module.objects.all()

    if request.user.is_authenticated:
        try:
            user_profile = getattr(request.user, 'profile', None)
            user_role = getattr(user_profile, 'role', None)

            if request.user.is_superuser:
                modules = all_modules
            elif user_role:
                modules = all_modules.filter(role_modules=user_role).distinct()
            else:
                messages.error(request, "Invalid role or no modules available for this role.")
                modules = Module.objects.none()
        except AttributeError:
            messages.error(request, "User profile not found.")
            modules = Module.objects.none()
    else:
        modules = all_modules

    if query:
        modules = modules.filter(
            Q(module_name__icontains=query) |
            Q(module_group__group_name__icontains=query)
        )

    module_groups = ModuleGroup.objects.all()
    form = ExcelImportForm()

    return render(request, 'home.html', {
        'module_groups': module_groups,
        'modules': modules,
        'form': form,
    })
