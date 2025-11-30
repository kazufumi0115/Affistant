import csv
import openpyxl  # Excel生成用
from django.http import HttpResponse
from django.utils import timezone
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
from .tasks import enqueue_extraction_for_keyword


class BaseOwnerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class GenreViewSet(BaseOwnerViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ProjectViewSet(BaseOwnerViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    @action(detail=True, methods=["post"])
    def extract(self, request, pk=None):
        project = self.get_object()

        # 1. キーワード登録
        raw_keywords = request.data.get("keywords", "")
        max_rank = request.data.get("max_rank", 10)

        if raw_keywords:
            keyword_list = [k.strip() for k in raw_keywords.split("\n") if k.strip()]
            for k_text in keyword_list:
                Keyword.objects.get_or_create(project=project, text=k_text)

        # 2. キーワード取得
        keywords = project.keywords.all()

        if not keywords.exists():
            return Response({"error": "キーワードが登録されていません。"}, status=status.HTTP_400_BAD_REQUEST)

        # 3. 実行履歴作成
        run = ExtractionRun.objects.create(project=project, status="pending", max_rank=max_rank)

        # 4. タスク実行
        for keyword in keywords:
            enqueue_extraction_for_keyword.delay(run.id, keyword.id)

        return Response(
            {
                "run_id": run.id,
                "status": run.status,
                "task_count": keywords.count(),
                "message": f"{keywords.count()}件のキーワードで検索を開始しました。",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"])
    def export_csv(self, request, pk=None):
        project = self.get_object()

        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        filename = f"{project.name}_seo_results.csv"
        response["Content-Disposition"] = f"attachment; filename=\"{filename}\"; filename*=UTF-8''{filename}"

        writer = csv.writer(response)
        header = [
            "キーワード",
            "月間検索ボリューム",
            "検索日時",
            "メディア名",
            "SEO順位",
            "掲載記事リンク",
            "アフィリエイトリンク詳細",
        ]
        writer.writerow(header)

        results = (
            SearchResult.objects.filter(run__project=project, rank__gt=0)
            .select_related("keyword", "run", "media_site")
            .prefetch_related("affiliate_links")
            .order_by("-run__executed_at", "keyword__text", "rank")
        )

        for result in results:
            aff_links_list = []
            for link in result.affiliate_links.all():
                asp = link.asp_name or "不明"
                product = link.product_name or "不明"
                aff_links_list.append(f"[{asp}: {product}] {link.link_url}")

            aff_links_text = "\n".join(aff_links_list) if aff_links_list else "なし"

            local_executed_at = timezone.localtime(result.run.executed_at)

            row = [
                result.keyword.text,
                result.keyword.search_volume or 0,
                local_executed_at.strftime("%Y-%m-%d %H:%M"),
                result.media_site.name or result.media_site.domain,
                result.rank,
                result.page_url,
                aff_links_text,
            ]
            writer.writerow(row)

        return response

    # === Excel出力機能 ===
    @action(detail=True, methods=["get"])
    def export_excel(self, request, pk=None):
        project = self.get_object()

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        filename = f"{project.name}_seo_results.xlsx"
        response["Content-Disposition"] = f"attachment; filename=\"{filename}\"; filename*=UTF-8''{filename}"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "SEO Results"

        header = [
            "キーワード",
            "月間検索ボリューム",
            "検索日時",
            "メディア名",
            "SEO順位",
            "掲載記事リンク",
            "アフィリエイトリンク詳細",
        ]
        ws.append(header)

        results = (
            SearchResult.objects.filter(run__project=project, rank__gt=0)
            .select_related("keyword", "run", "media_site")
            .prefetch_related("affiliate_links")
            .order_by("-run__executed_at", "keyword__text", "rank")
        )

        for result in results:
            aff_links_list = []
            for link in result.affiliate_links.all():
                asp = link.asp_name or "不明"
                product = link.product_name or "不明"
                aff_links_list.append(f"[{asp}: {product}] {link.link_url}")

            aff_links_text = "\n".join(aff_links_list) if aff_links_list else "なし"

            local_executed_at = timezone.localtime(result.run.executed_at)

            row = [
                result.keyword.text,
                result.keyword.search_volume or 0,
                local_executed_at.strftime("%Y-%m-%d %H:%M"),
                result.media_site.name or result.media_site.domain,
                result.rank,
                result.page_url,
                aff_links_text,
            ]
            ws.append(row)

        wb.save(response)
        return response

    @action(detail=True, methods=["post"])
    def clear_data(self, request, pk=None):
        project = self.get_object()
        run_count = project.runs.count()
        project.runs.all().delete()

        return Response({"message": f"{run_count}件の検索履歴を削除しました。"}, status=status.HTTP_200_OK)


# ... (KeywordViewSet等は変更なし) ...
class KeywordViewSet(viewsets.ModelViewSet):
    queryset = Keyword.objects.all()
    serializer_class = KeywordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Keyword.objects.filter(project__owner=user)


class MediaSiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MediaSite.objects.all()
    serializer_class = MediaSiteSerializer
    permission_classes = [permissions.IsAuthenticated]


class ExtractionRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExtractionRun.objects.all()
    serializer_class = ExtractionRunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ExtractionRun.objects.filter(project__owner=user)


class SearchResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SearchResult.objects.all()
    serializer_class = SearchResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return SearchResult.objects.filter(run__project__owner=user)
