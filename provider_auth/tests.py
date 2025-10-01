from django.test import TestCase
from django.urls import reverse 
from rest_framework.test import APITestCase
from provider_auth.models import User, Patient

# Create your tests here.
class PatientTests(APITestCase):
    def setUp(self):
        self.provider1 = User.objects.create_user(email='one@email.com', username='one', password='123', full_name='Provider One')
        self.provider2 = User.objects.create_user(email='two@email.com', username='two', password='123', full_name='Provider Two')

        Patient.objects.create(provider=self.provider1, first_name='Patient One', last_name='Test')
        Patient.objects.create(provider=self.provider2, first_name='Patient Two', last_name='Test')

    def test_provider_can_view_own_patients(self):
        self.client.force_login(user=self.provider1)
        response = self.client.get(reverse('patient-list'))
        print(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['first_name'], 'Patient One') 



        self.client.force_login(user=self.provider2)
        response = self.client.get(reverse('patient-list'))
        print(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['first_name'], 'Patient Two') 


    