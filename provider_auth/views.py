# provider_auth/views.py
import os
import uuid
import random
from io import BytesIO
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.contrib.auth.password_validation import validate_password
from django.template.loader import render_to_string
from django.utils import timezone

from rest_framework import generics, status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from twilio.rest import Client
from dotenv import load_dotenv
from weasyprint import HTML

from .models import User, Profile, EmailVerificationToken
from . import models as api_models
from . import serializers as api_serializers

from promed_backend_api.settings import LOCAL_HOST, DEFAULT_FROM_EMAIL

load_dotenv()

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from .models import Verification_Code
from .serializers import MyTokenObtainPairSerializer, UserSerializer
import os, random, uuid
from twilio.rest import Client
from django.conf import settings

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.user

        # Check if user is verified
        if not user.is_verified:
            return Response(
                {'detail': 'Your account is not verified. Please check your email to complete the verification.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check if user is approved
        if not user.is_approved:
            return Response(
                {'detail': 'Your account is pending administrator approval. We will contact you once it is active.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Generate tokens
        refresh = serializer.validated_data['refresh']
        access = serializer.validated_data['access']

        # MFA code setup
        method = request.data.get('method', 'email')
        code = str(random.randint(100000, 999999))
        session_id = str(uuid.uuid4())

        api_models.Verification_Code.objects.create(
            user=user,
            code=code,
            method=method,
            session_id=session_id
        )

        if method == 'sms' and user.phone_number:
            twilio_api_key = os.getenv('TWILIO_API_KEY')
            twilio_secret_key = os.getenv('TWILIO_SECRET_KEY')
            client = Client(twilio_api_key, twilio_secret_key)
            client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
                to=str(user.phone_number),
                channel='sms'
            )

        if method == 'email':
            send_mail(
                subject='Login Verification Code',
                message=f'Your login verification code is {code}. This code will expire shortly.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email]
            )

        request.session['mfa'] = False

        user_data = UserSerializer(user).data

        return Response({
            'access': str(access),
            'refresh': str(refresh),
            'mfa_required': True,
            'session_id': session_id,
            'user': user_data,
            'detail': 'Verification code sent.'
        }, status=status.HTTP_200_OK)
class RegisterUser(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = api_serializers.RegisterSerializer
    def perform_create(self, serializer):
        user = serializer.save()
        token, created = EmailVerificationToken.objects.get_or_create(user=user)

        # verification_link = f"https://wchandler2020.github.io/promedhealthplus_portal_client/#/verify-email/{token.token}"
        verification_link = f"{LOCAL_HOST}/#/verify-email/{token.token}"
        
        email_html_message = render_to_string(
            'provider_auth/email_verification.html',
            {
                'user': user,
                'verification_link': verification_link
            }
        )
        send_mail(
            subject='Verify Your Email Address',
            message=f"Click the link to verify your email: {verification_link}",
            html_message=email_html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )

class VerifyEmailView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    
    def get(self, request, token):
        # ⬅️ FIX: Add this line to prevent the drf_yasg error during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response(status=status.HTTP_200_OK)
            
        try:
            verification_token = api_models.EmailVerificationToken.objects.get(token=token)
            user = verification_token.user

            if user.is_verified:
                return Response({"message": "Email already verified."}, status=status.HTTP_200_OK)

            # Mark the user's email as verified
            user.is_verified = True
            user.save()
            verification_token.delete()

            # Send the new 'awaiting approval' email to the user
            approval_email_html = render_to_string(
                'provider_auth/awaiting_approval_email.html',
                {'user': user}
            )

            send_mail(
                subject='Your ProMed Health Plus Account is Pending Review',
                message='Thank you for registering. Your account is currently under review by our administrators.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=approval_email_html,
                fail_silently=False
            )

            # Notify admin about the newly verified user
            admin_subject = f"New Provider Awaiting Approval: {user.full_name}"
            admin_message = render_to_string('provider_auth/new_provider_admin_notification.html', {
                'user': user,
                'profile': user.profile,
                'verification_date': datetime.now()
            })

            admin_recipients = [
                'admin@yourdomain.com',
                'william.d.chandler1@gmail.com',
                'kayvoncrenshaw@gmail.com'
                'harold@promedhealthplus.com'
            ]

            send_mail(
                subject=admin_subject,
                message='A new provider has verified their email and is awaiting admin approval.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_recipients,
                html_message=admin_message,
                fail_silently=False
            )

            return Response(
                {"message": "Email successfully verified. Your account is now awaiting admin approval."}, 
                status=status.HTTP_200_OK
            )

        except api_models.EmailVerificationToken.DoesNotExist:
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)


class VerifyCodeView(generics.CreateAPIView):
    serializer_class = api_serializers.VerifyCodeSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        # Require JWT authentication
        user = request.user
        session_id = request.data.get('session_id')
        code = request.data.get('code')
        twilio_api_key = os.getenv('TWILIO_API_KEY')
        twilio_secret_key = os.getenv('TWILIO_SECRET_KEY')
        if not user or not session_id or not code:
            return Response({'error': 'Missing data'}, status=status.HTTP_400_BAD_REQUEST)
        # Check code
        valid_code = api_models.Verification_Code.objects.filter(
            session_id=session_id,
        ).order_by('-created_at').first()
        if not valid_code:
            return Response({'verified': False, 'error': 'Invalid code'}, status=status.HTTP_400_BAD_REQUEST)
        # Mark user as verified
        phone_number = str(user.phone_number)
        client = Client(twilio_api_key, twilio_secret_key)
        verification_check = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
        to=phone_number,
        code=code)
        if not verification_check.valid:
            return Response({'verified': False, 'error': 'Invalid code'}, status=status.HTTP_400_BAD_REQUEST)
        request.session['mfa'] = True  # Mark session as verified
        return Response({'verified': True}, status=status.HTTP_200_OK)

class ProviderProfileView(generics.RetrieveAPIView, generics.UpdateAPIView): # Add generics.UpdateAPIView
    serializer_class = api_serializers.ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
        
    def patch(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

class ContactRepView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = api_serializers.ContactRepSerializer

    def create(self, request, *args, **kwargs):
        if getattr(self, 'swagger_fake_view', False):  # Prevent drf_yasg crash
            return Response(status=status.HTTP_200_OK)

        user = request.user

        profile = getattr(user, 'profile', None)
        if not profile or not profile.sales_rep:
            return Response(
                {'error': 'No sales representative assigned to this provider.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract data
        sales_rep = profile.sales_rep
        rep_email = sales_rep.email
        rep_name = sales_rep.name

        sender_name = request.data.get('name', user.full_name)
        sender_phone = request.data.get('phone', user.phone_number)
        sender_email = request.data.get('email', user.email)
        message_body = request.data.get('message')

        if not message_body:
            return Response(
                {'error': 'Message body is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subject = f"New Message from Provider: {sender_name}"

        # Render HTML email template
        html_message = render_to_string('provider_auth/provider_inquiry.html', {
            'rep_name': rep_name,
            'sender_name': sender_name,
            'sender_email': sender_email,
            'sender_phone': sender_phone,
            'message_body': message_body,
            'year': datetime.now().year
        })

        recipient_list = list(set([
            rep_email,
            'william.d.chandler1@gmail.com',
            'harold@promedhealthplus.com',
            'kayvoncrenshaw@gmail.com',
            'william.dev@promedhealthplus.com'
        ]))

        try:
            send_mail(
                subject=subject,
                message=message_body,  # plain-text fallback
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            return Response({'success': 'Message sent successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error sending provider inquiry email: {e}")
            return Response(
                {'error': 'Failed to send message via email.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class ResetPasswordView(generics.GenericAPIView):
    serializer_class = api_serializers.ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, token):
        try:
            reset_token = api_models.PasswordResetToken.objects.get(token=token)
        except api_models.PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid or expired token.'}, status=400)

        if reset_token.is_expired():
            reset_token.delete()
            return Response({'error': 'Token has expired.'}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        password = serializer.validated_data['password']

        # Validate password strength
        user = reset_token.user
        try:
            validate_password(password, user=user)
        except DjangoValidationError as e:
            return Response({'error': e.messages}, status=400)

        user.set_password(password)
        user.save()
        reset_token.delete()

        return Response({'success': 'Password has been reset successfully.'}, status=200)
    
    
class RequestPasswordResetView(generics.GenericAPIView):
    serializer_class = api_serializers.RequestPasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try: 
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            pass

        response_message = {'message': 'If the email is registered, a reset link has been sent.'}

        # Send email password reset if user exists
        if 'user' in locals():
            token = api_models.PasswordResetToken.objects.create(user=user)
            # reset_link = f"{LOCAL_HOST}/reset-password/{token.token}/"
            reset_link = f"{LOCAL_HOST}/#/reset-password/{token.token}/"

            html_message = render_to_string('provider_auth/passwordresetemail.html', 
                                            {'reset_link': reset_link,
                                             'user': user,
                                             'year': datetime.now().year})
            # Send email with reset link
            send_mail(
                subject='Password Reset Request',
                message=f'Click the link to reset your password: {reset_link}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

        return Response(response_message, status=200)
    
class PublicContactView(generics.CreateAPIView):
    serializer_class = api_serializers.PublicContactSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        subject = f"New Public Inquiry from: {data['name']}"
        
        html_message = render_to_string('provider_auth/public_inquiry.html', {
            'name': data['name'],
            'facility': data['facility'],
            'city': data['city'],
            'state': data['state'],
            'zip': data['zip'],
            'phone': data['phone'],
            'email': data['email'],
            'question': data['question'],
            'year': datetime.now().year
        })
        
        recipient_list = list(set([
            'william.d.chandler1@gmail.com',
            'harold@promedhealthplus.com',
            'kayvoncrenshaw@gmail.com',
            'william.dev@promedhealthplus.com'
        ]))
        
        try:
            send_mail(
                subject=subject,
                message=f"Name: {data['name']}\Facility: {data['facility']}\nEmail: {data['email']}\nPhone: {data['phone']}\nCity: {data['city']}, {data['state']} {data['zip']}\n\nQuestion:\n{data['question']}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            return Response({'success': 'Message sent successfully.'}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error sending public inquiry email: {e}")
            return Response(
                {'error': 'Failed to send message.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )