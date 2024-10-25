from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from .models import Chat, User
from django.contrib.auth.forms import UserCreationForm

def user_list_view(request):
    current_user = request.user  # Get the current logged-in user
    
    # Get the search query from the request
    search_query = request.GET.get('q', '').strip()
    
    if search_query:
        # Filter users based on the search query, excluding the current user
        users = User.objects.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query) | 
            Q(full_name__icontains=search_query)  # Changed to full_name
        ).exclude(id=current_user.id)
    else:
        # If no search query, list all users except the current user
        users = User.objects.exclude(id=current_user.id)
    
    return render(request, 'chat/user_list.html', {'users': users, 'search_query': search_query})

def chat_view(request, username):
    other_user = get_object_or_404(User, username=username)  # The receiver (other participant in the chat)
    current_user = request.user  # The logged-in user (sender)
    
    if current_user.username == username:
        # Prevent a user from chatting with themselves
        return redirect('some_error_page')  # Redirect to an error page or a relevant message

    # Get the list of users that have sent messages to the receiver
    users_sent_to_receiver = User.objects.filter(
        id__in=Chat.objects.filter(receiver=other_user).values('sender')
    )

    # Get the sender from the URL, if provided, else it's the logged-in user
    sender_name = request.GET.get('sender', None)
    sender = get_object_or_404(User, username=sender_name) if sender_name else current_user

    # Filter messages between the logged-in user and the selected receiver
    if sender:
        messages = Chat.objects.filter(
            (Q(sender=current_user) & Q(receiver=other_user)) |
            (Q(sender=other_user) & Q(receiver=current_user))
        ).order_by('timestamp')
    else:
        messages = Chat.objects.filter(
            (Q(receiver=current_user) & Q(sender=other_user)) |
            (Q(sender=current_user) & Q(receiver=other_user))
        ).order_by('timestamp')

    if request.method == "POST":
        message_text = request.POST.get('message', '').strip()
        selected_receiver_username = request.POST.get('receiver', other_user.username)
        receiver = get_object_or_404(User, username=selected_receiver_username)
        
        if message_text and receiver:
            Chat.objects.create(sender=current_user, receiver=receiver, message=message_text)
            return redirect('chat:chat_view', username=other_user.username)

    users = User.objects.exclude(username=current_user.username)

    context = {
        'other_user': other_user,
        'users_sent_to_receiver': users_sent_to_receiver,
        'messages': messages,
        'users': users,
        'user': current_user  # Pass the current logged-in user
    }

    return render(request, 'chat/chat_view.html', context)

def send_message_form(request):
    if request.method == "POST":
        recipient_username = request.POST.get('recipient')
        message_text = request.POST.get('message')
        sender_username = request.POST.get('sender')  # Assume sender is passed from the form
        recipient = get_object_or_404(User, username=recipient_username)
        sender = get_object_or_404(User, username=sender_username)
        if recipient and sender and message_text:
            Chat.objects.create(sender=sender, receiver=recipient, message=message_text)
            return redirect('chat:chat_view', username=recipient_username)  # Corrected redirect
    users = User.objects.all()
    context = {
        'users': users
    }
    return render(request, 'chat/send_message_form.html', context)

