from django.urls import path
from .views import create_question,getQuestions, post_answer

urlpatterns = [
    path('create_questions/', create_question),
    path('questions/', getQuestions),
    path('post_answer/', post_answer, name='post_answer'),
]
