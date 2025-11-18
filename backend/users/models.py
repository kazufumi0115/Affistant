from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    カスタムユーザーモデルのマネージャー。
    メールアドレスをユニークな識別子として使用します。
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("ユーザーはメールアドレスを持っている必要があります"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """スーパーユーザーを作成します"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("スーパーユーザーは is_staff=True である必要があります。"))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("スーパーユーザーは is_superuser=True である必要があります。"))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    メールアドレスをユーザー名として使用するカスタムユーザーモデル。
    """

    email = models.EmailField(
        verbose_name=_("メールアドレス"),
        max_length=255,
        unique=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # is_superuser は PermissionsMixin が提供

    # ユーザーを識別するためのフィールドをメールアドレスに設定
    USERNAME_FIELD = "email"
    # 必須フィールドのリスト (スーパーユーザー作成時に聞かれる)
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _("ユーザー")
        verbose_name_plural = _("ユーザー")
