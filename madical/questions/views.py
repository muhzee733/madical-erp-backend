from django.contrib.auth import get_user_model
User = get_user_model()
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import QuestionSerializer, ResponseSerializer
from .models import Question
from users.permissions import IsAdmin

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def create_question(request):
    serializer = QuestionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Question added successfully.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        "message": "Validation failed.",
        "errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def getQuestions(request):
    questions = Question.objects.all()
    serializer = QuestionSerializer(questions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def post_answer(request):
    user_id = request.data.get('user_id')
    responses = request.data.get('responses')

    for response in responses:
        data = {
            "user": user_id,
            "question": response["question_id"],
            "answer": response["answer"]
        }
        serializer = ResponseSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "All responses submitted successfully."}, status=status.HTTP_201_CREATED)