# material/serializers.py
from rest_framework import serializers
from .models import InstitutionV2

class InstitutionV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = InstitutionV2
        fields = '__all__'