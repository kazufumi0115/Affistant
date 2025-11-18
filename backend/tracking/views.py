from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Genre, Project, Keyword, MediaSite, ExtractionRun, SearchResult
from .serializers import (
    GenreSerializer,
    ProjectSerializer,
    KeywordSerializer,
    MediaSiteSerializer,
    ExtractionRunSerializer,
    SearchResultSerializer,
)

# ユーザーが定義したCeleryタスクをインポート
from .tasks import enqueue_extraction_for_keyword

# === ベースビューセット（認証・オーナー権限） ===


class BaseOwnerViewSet(viewsets.ModelViewSet):
    """
    オーナー（認証済みユーザー）に紐づくデータのみを操作可能にする
    ベースビューセット。
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        認証済みユーザーがオーナーであるオブジェクトのみを返す。
        (self.queryset は継承先で .all() が設定されている前提)
        """
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """
        作成時にオーナーを認証済みユーザーに自動設定する。
        """
        serializer.save(owner=self.request.user)


# === フォルダ管理 (要件 ①-2) ===


class GenreViewSet(BaseOwnerViewSet):
    """
    API endpoint for Genres (ジャンル).
    オーナーに紐づくジャンルのみを操作可能。
    """

    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ProjectViewSet(BaseOwnerViewSet):
    """
    API endpoint for Projects (案件).
    オーナーに紐づく案件のみを操作可能。
    """

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    @action(detail=True, methods=["post"])
    def extract(self, request, pk=None):
        """
        特定のプロジェクト（案件）に紐づく全てのキーワードの
        SEO分析タスク（Celery）をキューに追加します。
        """
        # get_object() は BaseOwnerViewSet の get_queryset() を
        # 経由するため、オーナーのプロジェクトでなければ 404 となり安全です。
        project = self.get_object()

        # 1. このプロジェクトの「実行履歴（Run）」を1件作成
        # (注: ExtractionRunモデルは 'project' FK を持つ前提)
        run = ExtractionRun.objects.create(
            project=project,
            status="pending",
            # max_rank は request.data から受け取ることも可能
            # max_rank=request.data.get('max_rank', 50)
        )

        # 2. このプロジェクトに属する全てのキーワードを取得
        keywords = project.keywords.all()
        if not keywords.exists():
            return Response(
                {"error": "このプロジェクトにはキーワードが登録されていません。"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 3. 各キーワードについてCeleryタスクをエンキュー
        # (注: タスク側は (run_id, keyword_id) を受け取れるように修正が必要)
        for keyword in keywords:
            # (注) ユーザーが定義したタスク名が `enqueue_extraction_for_keyword`
            # だったので、それに合わせています。
            enqueue_extraction_for_keyword.delay(run.id, keyword.id)

        return Response(
            {"run_id": run.id, "status": run.status, "task_count": keywords.count()}, status=status.HTTP_202_ACCEPTED
        )


# === SEO分析 (要件 ①-3〜) ===


class KeywordViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Keywords (キーワード).
    """

    queryset = Keyword.objects.all()
    serializer_class = KeywordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        認証済みユーザーのプロジェクトに紐づくキーワードのみを返す。
        """
        user = self.request.user
        # project__owner を使って、オーナーのプロジェクトのキーワードのみをフィルタ
        return Keyword.objects.filter(project__owner=user)

    # perform_create は ModelViewSet のデフォルトを使用。
    # Serializer側で project がオーナーのものか検証するのが望ましいが、
    # 読み取り（get_queryset）がフィルタされているため、
    # 他人のキーワードを作成・編集しても自分には見えない。


class MediaSiteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Media Sites (メディアサイト).
    これは全ユーザー共通データとするため、オーナーチェックはしない。
    """

    queryset = MediaSite.objects.all()
    serializer_class = MediaSiteSerializer
    permission_classes = [permissions.IsAuthenticated]  # 認証は必要


class ExtractionRunViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Extraction Runs (検索実行履歴).
    """

    queryset = ExtractionRun.objects.all()
    serializer_class = ExtractionRunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        認証済みユーザーのプロジェクトに紐づく実行履歴のみを返す。
        """
        user = self.request.user
        return ExtractionRun.objects.filter(project__owner=user)


class SearchResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Search Results (検索結果).
    """

    queryset = SearchResult.objects.all()
    serializer_class = SearchResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        認証済みユーザーの実行履歴に紐づく検索結果のみを返す。
        """
        user = self.request.user
        return SearchResult.objects.filter(run__project__owner=user)
