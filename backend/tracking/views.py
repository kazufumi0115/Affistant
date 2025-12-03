import csv
import openpyxl
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from urllib.parse import urlparse
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
        raw_keywords = request.data.get("keywords", "")
        max_rank = request.data.get("max_rank", 10)

        if raw_keywords:
            keyword_list = [k.strip() for k in raw_keywords.split("\n") if k.strip()]
            for k_text in keyword_list:
                Keyword.objects.get_or_create(project=project, text=k_text)

        keywords = project.keywords.all()
        if not keywords.exists():
            return Response({"error": "キーワードが登録されていません。"}, status=status.HTTP_400_BAD_REQUEST)

        run = ExtractionRun.objects.create(project=project, status="pending", max_rank=max_rank)
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

    # --- 共通のデータ行生成ロジック ---
    def _generate_rows(self, project):
        results = (
            SearchResult.objects.filter(run__project=project)
            .select_related("keyword", "run", "media_site")
            .prefetch_related("affiliate_links")
            .order_by("-run__executed_at", "keyword__text", "rank")
        )

        rows = []
        for result in results:
            display_rank = result.rank if result.rank > 0 else "取得失敗"

            # メディア名: トップドメインのみ抽出
            domain = result.media_site.domain
            # "www." などを除去してきれいにする場合
            if domain.startswith("www."):
                domain = domain[4:]

            # アフィリエイトリンク情報の整理
            aff_links = result.affiliate_links.all()
            has_affiliate = aff_links.exists()
            media_type = "アフィリエイトメディア" if has_affiliate else "その他"

            # 提携ASP一覧 (重複排除)
            asp_set = set(link.asp_name for link in aff_links if link.asp_name)
            asp_list_str = ", ".join(asp_set) if asp_set else ""

            local_executed_at = timezone.localtime(result.run.executed_at)

            # --- 修正: 月間検索ボリュームのカラムを削除 ---
            row = [
                local_executed_at.strftime("%Y-%m-%d %H:%M"),  # A: 検索日時
                result.keyword.text,  # B: キーワード
                # result.keyword.search_volume or 0,  # C: 月間検索ボリューム (削除)
                domain,  # D: メディア名(トップドメイン)
                display_rank,  # E: SEO順位
                result.title,  # F: 記事名
                result.page_url,  # G: 掲載記事リンク
                media_type,  # H: メディア種類
                asp_list_str,  # I: 提携ASP
            ]

            # リンク列 (トップ10まで)
            for i in range(10):
                if i < len(aff_links):
                    row.append(aff_links[i].link_url)
                else:
                    row.append("")  # 空埋め

            rows.append(row)
        return rows

    # --- CSV出力 ---
    @action(detail=True, methods=["get"])
    def export_csv(self, request, pk=None):
        project = self.get_object()

        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        filename = f"{project.name}_seo_results.csv"
        response["Content-Disposition"] = f"attachment; filename=\"{filename}\"; filename*=UTF-8''{filename}"

        writer = csv.writer(response)
        # ヘッダー作成
        # --- 修正: 月間検索ボリュームを削除 ---
        header = [
            "検索日時",
            "キーワード",
            # "月間検索ボリューム", (削除)
            "メディア名",
            "SEO順位",
            "記事名",
            "掲載記事リンク",
            "メディア種類",
            "提携ASP",
        ]
        # リンク1〜リンク10を追加
        header.extend([f"リンク{i+1}" for i in range(10)])
        writer.writerow(header)

        rows = self._generate_rows(project)
        for row in rows:
            writer.writerow(row)

        return response

    # --- Excel出力 ---
    @action(detail=True, methods=["get"])
    def export_excel(self, request, pk=None):
        project = self.get_object()

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        filename = f"{project.name}_seo_results.xlsx"
        response["Content-Disposition"] = f"attachment; filename=\"{filename}\"; filename*=UTF-8''{filename}"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "SEO Results"

        # --- 修正: 月間検索ボリュームを削除 ---
        header = [
            "検索日時",
            "キーワード",
            # "月間検索ボリューム", (削除)
            "メディア名",
            "SEO順位",
            "記事名",
            "掲載記事リンク",
            "メディア種類",
            "提携ASP",
        ]
        header.extend([f"リンク{i+1}" for i in range(10)])
        ws.append(header)

        rows = self._generate_rows(project)
        for row in rows:
            ws.append(row)

        wb.save(response)
        return response

    @action(detail=True, methods=["post"])
    def clear_data(self, request, pk=None):
        project = self.get_object()
        run_count = project.runs.count()
        project.runs.all().delete()
        return Response({"message": f"{run_count}件の検索履歴を削除しました。"}, status=status.HTTP_200_OK)


# ... (以下、他のViewSetは変更なし) ...
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
