# accounts/views.py
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, UserSerializer
from .permissions import IsAdmin

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

class MeView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

class UserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserSerializer
    queryset = User.objects.all()

# add to accounts/views.py
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.password_validation import validate_password

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Expects: {old_password, new_password, new_password2}
    """
    user = request.user
    old = request.data.get("old_password")
    new = request.data.get("new_password")
    new2 = request.data.get("new_password2")
    if not user.check_password(old):
        return Response({"old_password": "Wrong password."}, status=status.HTTP_400_BAD_REQUEST)
    if new != new2:
        return Response({"new_password": "New passwords don't match."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(new, user)
    except Exception as e:
        return Response({"new_password": e.messages}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(new)
    user.save()
    return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
