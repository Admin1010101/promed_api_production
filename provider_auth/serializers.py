from .models import User, Profile
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

#Auth Serializers
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['full_name'] = user.full_name
        token['email'] = user.email
        token['username'] = user.username
        token['phone_number'] = str(user.phone_number) if user.phone_number else None
        token['country_code'] = user.country_code
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = authenticate(
            request=self.context.get('request'),
            email=attrs['email'],
            password=attrs['password']
        )
        if user and not user.is_verified:
            raise serializers.ValidationError({"detail": "Email not verified. Please check your inbox for a verification link."})
        return data

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    # New fields to match the updated User model
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
    role = serializers.CharField(read_only=True)  # ADD THIS LINE
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
