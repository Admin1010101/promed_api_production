# Standard Library
import logging
import os
import random
import uuid
from datetime import datetime
from io import BytesIO

# Third-Party Libraries
from dotenv import load_dotenv
from twilio.rest import Client

# Django
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

# Django REST Framework
from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

# Local Application Imports
from patients.models import Patient
from promed_backend_api.settings import BASE_CLIENT_URL, DEFAULT_FROM_EMAIL
from promed_backend_api.storage_backends import AzureMediaStorage
from utils.pdf_generator import generate_baa_pdf

from . import models as api_models
from . import serializers as api_serializers
from .models import EmailVerificationToken, Profile, User, Verification_Code
from .serializers import EmptySerializer, MyTokenObtainPairSerializer, UserSerializer


load_dotenv()

logger = logging.getLogger(__name__)

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        logger.info("=" * 50)
        logger.info("LOGIN ATTEMPT STARTED")

        serializer = self.get_serializer(data=request.data)

        try:
            # This step performs authentication and all pre-checks (is_active, is_verified, is_approved)
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.error(f"Serializer validation FAILED: {str(e)}")
            return Response(
                getattr(serializer, 'errors', {'detail': str(e)}),
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.user

        # =========================================================
        # 🆕 BAA AGREEMENT ENFORCEMENT CHECK
        # =========================================================
        if not user.has_signed_baa:
            user_data = UserSerializer(user).data
            logger.warning(f"BAA required for user: {user.email}. Denying access and prompting for BAA signing.")
            
            # ✅ Generate temporary access token (needed to sign BAA)
            refresh = serializer.validated_data['refresh']
            access = serializer.validated_data['access']
            
            # Return a 403 response with temporary access token
            return Response({
                'baa_required': True,
                'access': str(access),  # ✅ CRITICAL: Include temporary access token
                'detail': 'Provider must sign the Business Associate Agreement to continue.',
                'user': user_data
            }, status=status.HTTP_403_FORBIDDEN)

        refresh = serializer.validated_data['refresh']
        access = serializer.validated_data['access']

        # MFA code setup
        method = request.data.get('method', 'email')
        session_id = str(uuid.uuid4())
        
        logger.info(f"Creating NEW verification with method: {method}")
        logger.info(f"New Session ID: {session_id}")
        
        # Delete ALL old verification codes for this user
        deleted_count = api_models.Verification_Code.objects.filter(user=user).delete()[0]
        logger.info(f"Deleted {deleted_count} old verification codes for user: {user.email}")
        
        if method == 'sms' and user.phone_number:
            try:
                account_sid = os.getenv('ACCOUNT_SID')
                auth_token = os.getenv('AUTH_TOKEN')
                verify_service_sid = os.getenv('VERIFY_SERVICE_SID')
                
                if not all([account_sid, auth_token, verify_service_sid]):
                    return Response(
                        {"error": "SMS service not configured"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                client = Client(account_sid, auth_token)
                
                # Cancel any pending Twilio verifications first
                try:
                    verifications = client.verify.v2.services(verify_service_sid).verifications.list(
                        to=str(user.phone_number),
                        status='pending'
                    )
                    for v in verifications:
                        try:
                            client.verify.v2.services(verify_service_sid).verifications(v.sid).update(status='canceled')
                            logger.info(f"Canceled old Twilio verification: {v.sid}")
                        except:
                            pass
                except Exception as e:
                    logger.warning(f"Could not cancel old verifications: {e}")
                
                # NOW create new verification
                verification = client.verify.v2.services(verify_service_sid).verifications.create(
                    to=str(user.phone_number),
                    channel='sms'
                )
                
                # Store session_id with method for verification
                api_models.Verification_Code.objects.create(
                    user=user,
                    code='',
                    method=method,
                    session_id=session_id
                )
                
                logger.info(f"✅ NEW SMS verification sent to {user.phone_number}")
                logger.info(f"Twilio SID: {verification.sid}, Status: {verification.status}")
                
            except Exception as e:
                logger.error(f"SMS sending failed: {str(e)}")
                return Response(
                    {"error": f"Failed to send SMS: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        elif method == 'email':
            try:
                # Generate NEW random code
                code = str(random.randint(100000, 999999))
                
                api_models.Verification_Code.objects.create(
                    user=user,
                    code=code,
                    method=method,
                    session_id=session_id
                )
                
                send_mail(
                    subject='Login Verification Code',
                    message=f'Your login verification code is {code}. This code will expire in 10 minutes.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email]
                )
                logger.info(f"✅ NEW email verification sent to {user.email} with code: {code}")
                
            except Exception as e:
                logger.error(f"Email sending failed: {str(e)}")
                return Response(
                    {"error": f"Failed to send email: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {"error": "Invalid MFA method or missing phone number for SMS"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # ----------------------------------------------------
        
        user_data = UserSerializer(user).data
        
        logger.info("✅ LOGIN SUCCESSFUL - Returning NEW MFA session")
        logger.info("=" * 50)
        
        return Response({
            'access': str(access),
            'refresh': str(refresh),
            'mfa_required': True,
            'session_id': session_id,
            'user': user_data,
            'detail': f'Verification code sent via {method}.'
        }, status=status.HTTP_200_OK)

class RegisterUser(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = api_serializers.RegisterSerializer
    
    def perform_create(self, serializer):
        user = serializer.save()

        # Ensure profile exists (if not created in serializer)
        profile = getattr(user, 'profile', None)
        if profile and not profile.image:
            profile.image = 'defaults/default_user.jpg'
            profile.save()

        # 1️⃣ Send verification email to the NEW USER
        token, created = EmailVerificationToken.objects.get_or_create(user=user)
        verification_link = f"{BASE_CLIENT_URL}/#/verify-email/{token.token}"

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

        # 2️⃣ Send notification email to ADMIN about new registration
        try:
            admin_subject = f"New Provider Registration: {user.full_name}"
            admin_message = render_to_string(
                'provider_auth/new_registration_admin_notification.html',
                {
                    'user': user,
                    'profile': profile,
                    'registration_date': timezone.now(),
                    'year': datetime.now().year
                }
            )

            admin_recipients = [
                'portal@promedhealthplus.com',
                'harold@promedhealthplus.com',
                'william.dev@promedhealthplus.com'
            ]

            send_mail(
                subject=admin_subject,
                message=f"New provider registration:\n\nName: {user.full_name}\nEmail: {user.email}\nPhone: {user.phone_number or 'Not provided'}\n\nPlease contact them to verify their NPI number and approve their account in the admin section.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_recipients,
                html_message=admin_message,
                fail_silently=False
            )
            
            logger.info(f"✅ Admin notification sent for new registration: {user.email}")

        except Exception as e:
            logger.error(f"❌ Failed to send admin notification email: {e}")
            # Don't fail the registration if admin email fails


class VerifyEmailView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = EmptySerializer 

    def get(self, request, token):
        if getattr(self, 'swagger_fake_view', False):
            return Response(status=status.HTTP_200_OK)

        try:
            if isinstance(token, str):
                token = uuid.UUID(token)
            
            verification_token = api_models.EmailVerificationToken.objects.get(token=token)
            user = verification_token.user

            if user.is_verified:
                return Response(
                    {"message": "Email already verified."}, 
                    status=status.HTTP_200_OK
                )

            user.is_verified = True
            user.save()
            verification_token.delete()

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

            admin_subject = f"New Provider Awaiting Approval: {user.full_name}"
            admin_message = render_to_string('provider_auth/new_provider_admin_notification.html', {
                'user': user,
                'profile': user.profile,
                'verification_date': datetime.now()
            })

            admin_recipients = [
                'portal@promedhealthplus.com',
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

        except (api_models.EmailVerificationToken.DoesNotExist, ValueError) as e:
            print(f"Token verification error: {e}")
            print(f"Token received: {token}")
            return Response(
                {"error": "Invalid or expired token."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class VerifyCodeView(generics.CreateAPIView):
    serializer_class = api_serializers.VerifyCodeSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # ✅ FIX: Explicitly disable authentication

    def create(self, request, *args, **kwargs):
        session_id = request.data.get('session_id')
        code = request.data.get('code')

        logger.info(f"MFA verification attempt - Session ID: {session_id}")

        if not session_id or not code:
            return Response(
                {'verified': False, 'error': 'Missing session_id or code'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find the verification code record
        verification_record = api_models.Verification_Code.objects.filter(
            session_id=session_id,
        ).order_by('-created_at').first()
        
        if not verification_record:
            logger.error(f"No verification record found for session: {session_id}")
            return Response(
                {'verified': False, 'error': 'Invalid or expired session'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the code has expired (10 minutes)
        from django.utils import timezone
        from datetime import timedelta
        if timezone.now() - verification_record.created_at > timedelta(minutes=10):
            verification_record.delete()
            return Response(
                {'verified': False, 'error': 'Verification code has expired'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = verification_record.user
        method = verification_record.method
        
        # Verify based on method
        if method == 'sms':
            # Use Twilio to verify
            try:
                account_sid = os.getenv('ACCOUNT_SID')
                auth_token = os.getenv('AUTH_TOKEN')
                verify_service_sid = os.getenv('VERIFY_SERVICE_SID')
                
                if not user.phone_number:
                    return Response(
                        {'verified': False, 'error': 'No phone number on file'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                client = Client(account_sid, auth_token)
                verification_check = client.verify.v2.services(verify_service_sid).verification_checks.create(
                    to=str(user.phone_number),
                    code=code
                )
                
                logger.info(f"Twilio verification status: {verification_check.status}")
                
                if verification_check.status != 'approved':
                    return Response(
                        {'verified': False, 'error': 'Invalid verification code'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
            except Exception as e:
                logger.error(f"Twilio verification error: {str(e)}")
                return Response(
                    {'verified': False, 'error': 'Verification failed'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        elif method == 'email':
            # Compare with our stored code
            if verification_record.code != code:
                logger.error(f"Code mismatch. Expected: {verification_record.code}, Got: {code}")
                return Response(
                    {'verified': False, 'error': 'Invalid verification code'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # ✅ FIX: Generate new refresh token after successful MFA verification
        refresh = RefreshToken.for_user(user)
        
        # Verification successful - clean up
        verification_record.delete()
        logger.info(f"MFA verification successful for user: {user.email}")
        
        # ✅ FIX: Return both refresh and access tokens
        return Response({
            'verified': True,
            'message': 'Verification successful',
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }, status=status.HTTP_200_OK)

class ProviderProfileView(generics.RetrieveAPIView, generics.UpdateAPIView):
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
        if getattr(self, 'swagger_fake_view', False):
            return Response(status=status.HTTP_200_OK)

        user = request.user

        profile = getattr(user, 'profile', None)
        if not profile or not profile.sales_rep:
            return Response(
                {'error': 'No sales representative assigned to this provider.'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
            'portal@promedhealthplus.com',
        ]))

        try:
            send_mail(
                subject=subject,
                message=message_body,
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

        if 'user' in locals():
            token = api_models.PasswordResetToken.objects.create(user=user)
            reset_link = f"{BASE_CLIENT_URL}/#/reset-password/{token.token}/"

            html_message = render_to_string('provider_auth/passwordresetemail.html',
                                            {'reset_link': reset_link,
                                             'user': user,
                                             'year': datetime.now().year})
            send_mail(
                subject='Password Reset Request',
                message=f'Click the link to reset your password: {reset_link}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

        return Response(response_message, status=200)

class SignBAAView(generics.UpdateAPIView):
    """
    Allows an authenticated user to submit the signed BAA agreement.
    Processes BAA, updates user status, and initiates MFA.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = api_serializers.BAASignatureSerializer

    def update(self, request, *args, **kwargs):
        user = request.user

        if user.has_signed_baa:
            return Response(
                {"detail": "BAA already signed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            # ============================================
            # STEP 1, 2, 4: Process PDF, Azure, and Emails (Delegated)
            # ============================================
            # Calling the utility function we just defined
            pdf_url = process_signed_baa(user, data, generate_baa_pdf) 
            
            # ============================================
            # STEP 3: Update User Model
            # ============================================
            user.has_signed_baa = True
            user.baa_signed_at = timezone.now()
            user.save()

            logger.info(f"✅ BAA successfully signed for user: {user.email}")

            # ============================================
            # STEP 5: Initiate MFA
            # ============================================
            method = 'email'
            session_id = str(uuid.uuid4())

            # Clear old codes
            deleted_count = api_models.Verification_Code.objects.filter(user=user).delete()[0]
            logger.info(f"Deleted {deleted_count} old verification codes")

            # Generate tokens and code
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            code = str(random.randint(100000, 999999))

            # Store new code
            api_models.Verification_Code.objects.create(
                user=user,
                code=code,
                method=method,
                session_id=session_id
            )

            # Send MFA email
            send_mail(
                subject='Login Verification Code',
                message=f'Your login verification code is {code}. This code will expire in 10 minutes.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email]
            )
            logger.info(f"✅ MFA initiated for {user.email}")

            # ============================================
            # STEP 6: Final Response
            # ============================================
            return Response({
                'success': True,
                'access': access_token,
                'session_id': session_id,
                'mfa_required': True,
                'method': method,
                'pdf_url': pdf_url,
                'detail': 'BAA signed successfully. Verification code sent to your email.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # Catching exceptions from PDF generation, Azure storage, etc.
            logger.error(f"❌ Error during BAA signing process for {user.email}: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to process BAA signature. Check logs for details."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SignBAAView(generics.UpdateAPIView):
    """
    Allows an authenticated user to submit the signed BAA agreement.
    Generates PDF, emails it, stores in Azure, and initiates MFA.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = api_serializers.BAASignatureSerializer
    
    def update(self, request, *args, **kwargs):
        user = request.user
        
        if user.has_signed_baa:
            return Response(
                {"detail": "BAA already signed."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            # ============================================
            # STEP 1: Generate PDF
            # ============================================
            pdf_buffer = generate_baa_pdf(user, data)
            pdf_filename = f"BAA_{user.email}_{data['signature_date']}.pdf"
            
            # ============================================
            # STEP 2: Store PDF in Azure Blob Storage
            # ============================================
            storage = AzureMediaStorage()
            pdf_path = f"baa_agreements/{user.id}/{pdf_filename}"
            pdf_file = ContentFile(pdf_buffer.read())
            saved_path = storage.save(pdf_path, pdf_file)
            pdf_url = storage.url(saved_path)
            
            logger.info(f"✅ BAA PDF stored at: {pdf_url}")
            
            # ============================================
            # STEP 3: Update User Model
            # ============================================
            user.has_signed_baa = True
            user.baa_signed_at = timezone.now()
            user.save()
            
            logger.info(f"✅ BAA successfully signed for user: {user.email}")
            
            # ============================================
            # STEP 4: Email PDF to Admin and Provider
            # ============================================
            admin_recipients = [
                'portal@promedhealthplus.com',
                'harold@promedhealthplus.com',
            ]
            
            # Reset buffer for email attachment
            pdf_buffer.seek(0)
            
            # Email to Admin
            admin_subject = f"New BAA Signed: {user.full_name}"
            admin_message = render_to_string(
                'provider_auth/baa_signed_admin_notification.html',
                {
                    'user': user,
                    'baa_data': data,
                    'pdf_url': pdf_url,
                    'signed_date': timezone.now(),
                    'year': datetime.now().year
                }
            )
            
            admin_email = EmailMessage(
                subject=admin_subject,
                body=admin_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_recipients,
            )
            admin_email.content_subtype = "html"
            admin_email.attach(pdf_filename, pdf_buffer.read(), 'application/pdf')
            admin_email.send(fail_silently=False)
            
            logger.info(f"✅ BAA PDF emailed to admins")
            
            # Email to Provider
            pdf_buffer.seek(0)  # Reset buffer again
            
            provider_subject = "Your Signed BAA Agreement - ProMed Health Plus"
            provider_message = render_to_string(
                'provider_auth/baa_signed_provider_confirmation.html',
                {
                    'user': user,
                    'baa_data': data,
                    'signed_date': timezone.now(),
                    'year': datetime.now().year
                }
            )
            
            provider_email = EmailMessage(
                subject=provider_subject,
                body=provider_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            provider_email.content_subtype = "html"
            provider_email.attach(pdf_filename, pdf_buffer.read(), 'application/pdf')
            provider_email.send(fail_silently=False)
            
            logger.info(f"✅ BAA PDF emailed to provider: {user.email}")
            
            # ============================================
            # STEP 5: Initiate MFA
            # ============================================
            method = 'email'
            session_id = str(uuid.uuid4())
            
            deleted_count = api_models.Verification_Code.objects.filter(user=user).delete()[0]
            logger.info(f"Deleted {deleted_count} old verification codes")
            
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            
            code = str(random.randint(100000, 999999))
            
            api_models.Verification_Code.objects.create(
                user=user,
                code=code,
                method=method,
                session_id=session_id
            )
            
            send_mail(
                subject='Login Verification Code',
                message=f'Your login verification code is {code}. This code will expire in 10 minutes.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email]
            )
            
            logger.info(f"✅ MFA initiated for {user.email}")
            
            return Response({
                'success': True,
                'access': access_token,
                'session_id': session_id,
                'mfa_required': True,
                'method': method,
                'pdf_url': pdf_url,
                'detail': 'BAA signed successfully. Verification code sent to your email.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"❌ Error during BAA signing process for {user.email}: {str(e)}")
            return Response(
                {"error": "Failed to process BAA signature."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

def process_signed_baa(user, baa_data, generate_baa_pdf_func):
    """
    Handles PDF generation, Azure storage, and email distribution for a signed BAA.
    
    Returns:
        str: The public URL of the saved PDF on Azure.
    """
    
    # 1. Generate PDF
    pdf_buffer = generate_baa_pdf_func(user, baa_data)
    
    # Define Azure Path and PDF Filename for consistency
    provider_slug = slugify(user.full_name or user.email.split('@')[0])
    pdf_filename = f"baa_form_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = f"provider_forms/{provider_slug}/BAA_form/{pdf_filename}" 

    # 2. Store PDF in Azure Blob Storage
    try:
        storage = AzureMediaStorage() 
        pdf_buffer.seek(0)
        pdf_file = ContentFile(pdf_buffer.read())
        saved_path = storage.save(pdf_path, pdf_file)
        pdf_url = storage.url(saved_path)
        logger.info(f"✅ BAA PDF stored at: {pdf_url}")
    except Exception as e:
        logger.error(f"❌ Azure storage failed for BAA for {user.email}: {str(e)}", exc_info=True)
        raise e 

    # 3. Email PDF to Admin and Provider (Two Emails)
    
    admin_recipients = [
        'portal@promedhealthplus.com',
        'harold@promedhealthplus.com',
    ]
    
    message_context = {
        'user': user,
        'baa_data': baa_data,
        'pdf_url': pdf_url,
        'signed_date': timezone.now(),
        'year': datetime.now().year
    }
    
    try:
        # --- EMAIL 1: TO ADMINS (using baa_signed_admin_notification.html) ---
        pdf_buffer.seek(0) # Reset buffer
        
        admin_subject = f"New BAA Signed: {user.full_name or user.email}"
        admin_body = render_to_string(
            'provider_auth/baa_signed_admin_notification.html', 
            message_context
        )
        
        admin_email = EmailMessage(
            subject=admin_subject,
            body=admin_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_recipients,
        )
        admin_email.content_subtype = "html"
        admin_email.attach(pdf_filename, pdf_buffer.read(), 'application/pdf')
        admin_email.send(fail_silently=False)
        logger.info(f"✅ BAA PDF emailed to admins.")

        # --- EMAIL 2: TO PROVIDER (using baa_signed_provider_confirmation.html) ---
        pdf_buffer.seek(0) # Reset buffer again
        
        provider_subject = "Your Signed BAA Agreement - ProMed Health Plus"
        provider_body = render_to_string(
            'provider_auth/baa_signed_provider_confirmation.html', 
            message_context
        )
        
        provider_email = EmailMessage(
            subject=provider_subject,
            body=provider_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        provider_email.content_subtype = "html"
        provider_email.attach(pdf_filename, pdf_buffer.read(), 'application/pdf')
        provider_email.send(fail_silently=False)
        logger.info(f"✅ BAA PDF emailed to provider: {user.email}.")
        
    except Exception as e:
        logger.warning(f"⚠️ Email failed for BAA for {user.email}: {str(e)}", exc_info=True)
        # Non-critical failure, transaction continues
        
    return pdf_url