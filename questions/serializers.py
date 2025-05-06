from .models import Question, Response
from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ['id', 'user', 'question', 'answer']
