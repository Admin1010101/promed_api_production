from .models import User, Profile
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

#Auth Serializers
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Don't set username_field here, we'll handle it manually
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the username field entirely
        if 'username' in self.fields:
            del self.fields['username']
        # Add email field explicitly
        self.fields['email'] = serializers.EmailField(required=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['full_name'] = user.full_name
        token['email'] = user.email
        token['username'] = user.username
        token['phone_number'] = str(user.phone_number) if user.phone_number else None
        token['country_code'] = user.country_code
        token['role'] = user.role
        return token

    def validate(self, attrs):
        # Get credentials from attrs
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError({
                "detail": "Email and password are required."
            })
        
        # Try to get the user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "detail": "No active account found with the given credentials."
            })
        
        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError({
                "detail": "No active account found with the given credentials."
            })
        
        # Check if user can authenticate (is_active check)
        if not user.is_active:
            raise serializers.ValidationError({
                "detail": "User account is disabled."
            })
        
        # Check if email is verified
        if not user.is_verified:
            raise serializers.ValidationError({
                "detail": "Email not verified. Please check your inbox for a verification link."
            })
        
        # Check if user is approved
        if not user.is_approved:
            raise serializers.ValidationError({
                "detail": "Your account is pending administrator approval. We will contact you once it is active."
            })
        
        # Generate tokens
        refresh = self.get_token(user)
        
        # Store user for access in the view
        self.user = user
        
        # Return token data
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    country_code = serializers.CharField(required=True)
    city = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    facility = serializers.CharField(required=False)
    facility_phone_number = serializers.CharField(required=False)
    npi_number = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'full_name', 'email', 'phone_number', 'password', 'password2', 
            'npi_number', 'country_code', 'city', 'state', 'country', 
            'facility', 'facility_phone_number'
        )
        extra_kwargs = {
            'email': {'required': True},
            'phone_number': {'required': True},
            'full_name': {'required': True},
            'npi_number': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        npi_number = attrs.get('npi_number')
        if npi_number and len(npi_number) != 10:
            raise serializers.ValidationError({"npi_number": "NPI number must be 10 digits."})
            
        return attrs

    def create(self, validated_data):
        # Remove password2 from validated data as it is not a model field
        validated_data.pop('password2', None)
        
        # Manually extract fields that are not part of the create_user method
        npi_number = validated_data.pop('npi_number', None)
        country_code = validated_data.pop('country_code', None)
        city = validated_data.pop('city', None)
        state = validated_data.pop('state', None)
        country = validated_data.pop('country', None)
        facility = validated_data.pop('facility', None)
        facility_phone_number = validated_data.pop('facility_phone_number', None)

        try:
            user = User.objects.create_user(
                username=validated_data['email'],
                email=validated_data['email'],
                full_name=validated_data['full_name'],
                phone_number=validated_data['phone_number'],
                npi_number=npi_number,
                password=validated_data['password'],
                country_code=country_code,
                city=city,
                state=state,
                country=country,
                facility=facility,
                facility_phone_number=facility_phone_number,
            )
            return user
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)

class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    class Meta:
        model = User
        fields = (
            'id', 'email', 'full_name', 'username', 'phone_number', 'country_code','role',
        )


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = '__all__'

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None

class SendCodeSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=['email', 'sms'])

class VerifyCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)
    method = serializers.ChoiceField(choices=['email', 'sms'])

class ContactRepSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    message = serializers.CharField(required=True)
    
class PublicContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    facility = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=2)
    zip = serializers.CharField(max_length=10)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    question = serializers.CharField()
    
class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    
# Dummy serializer to prevent crashing during swagger/schema generation
class EmptySerializer(serializers.Serializer):
    """Used for views that don't take body data (like token verification)."""
    pass