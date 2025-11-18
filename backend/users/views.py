from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny  # 認証不要でアクセス許可
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import traceback  # デバッグ用
from .models import User


class RegisterView(views.APIView):
    """
    メールアドレスとパスワードで新しいユーザーアカウントを登録するAPIエンドポイント。
    """

    permission_classes = [AllowAny]  # ★ 修正: 認証不要

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": _("メールアドレスとパスワードは必須です。")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # UserManagerのcreate_userメソッドを使用してユーザーを作成
            user = User.objects.create_user(email=email, password=password)

            # 登録成功後、自動的にログイン（トークン発行）
            token, created = Token.objects.get_or_create(user=user)

            return Response(
                {"token": token.key, "detail": _("アカウントが正常に作成されました。")}, status=status.HTTP_201_CREATED
            )

        except IntegrityError:
            # データベースのUnique制約違反（メールアドレス重複）
            return Response(
                {"error": _("ユーザー登録に失敗しました。メールアドレスが既に使用されています。")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            # Djangoモデルのバリデーションエラー
            return Response({"error": e.message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # その他の予期せぬエラー
            print("--- UNEXPECTED ERROR IN REGISTER VIEW ---")
            traceback.print_exc()  # コンソールに完全なエラーを出力
            print("------------------------------------------")
            return Response(
                {"error": _("ユーザー登録中に予期せぬエラーが発生しました。")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LoginView(views.APIView):
    """
    メールアドレスとパスワードを使用して認証し、
    認証成功時にトークンを返すAPIエンドポイント。
    """

    permission_classes = [AllowAny]  # ★ 修正: 認証不要

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        password = request.data.get("password")

        # 組み込みのauthenticate関数を使用してユーザーを認証
        user = authenticate(request, email=email, password=password)

        if user:
            # 認証成功
            if not user.is_active:
                return Response({"error": _("アカウントは無効です。")}, status=status.HTTP_401_UNAUTHORIZED)

            # 既存のトークンがあれば削除し、新しいトークンを作成して返す
            Token.objects.filter(user=user).delete()
            token, created = Token.objects.get_or_create(user=user)

            return Response({"token": token.key})
        else:
            # 認証失敗
            return Response(
                {"error": _("無効な認証情報です。メールアドレスまたはパスワードを確認してください。")},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(views.APIView):
    """
    ログアウト時に認証トークンを削除するAPIエンドポイント。
    （デフォルトの IsAuthenticated 権限を使用）
    """

    def post(self, request):
        if request.auth:
            request.auth.delete()
            return Response({"detail": _("正常にログアウトしました。")}, status=status.HTTP_200_OK)
        return Response({"detail": _("認証されていません。")}, status=status.HTTP_401_UNAUTHORIZED)
