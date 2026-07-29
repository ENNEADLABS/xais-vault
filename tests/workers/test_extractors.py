"""
Tests for apps/worker/app/extractors/

Couvre le router d'extraction + chaque format (PDF, DOCX, XLSX/CSV, PPTX, TXT/MD).
Les dépendances externes (fitz, docx, pptx, pandas) sont mockées.
Les tests TXT/MD utilisent de vrais fichiers temporaires.
"""

import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.worker.app.extractors import ExtractionResult, extract
from apps.worker.app.extractors.text import extract_text
from apps.worker.app.extractors.xlsx import _dataframe_to_text

# ─── Router extract() ──────────────────────────────────────────


@pytest.mark.asyncio
class TestExtractRouter:
    async def test_routes_to_pdf(self):
        """extract('pdf') appelle extract_pdf."""
        mock_result = ExtractionResult(text="pdf text", page_count=2, word_count=2)
        with patch(
            "apps.worker.app.extractors.pdf.extract_pdf",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await extract("/tmp/test.pdf", "pdf")
        assert result.text == "pdf text"
        assert result.page_count == 2

    async def test_routes_to_docx(self):
        """extract('docx') appelle extract_docx."""
        mock_result = ExtractionResult(text="docx text", page_count=1, word_count=2)
        with patch(
            "apps.worker.app.extractors.docx.extract_docx",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await extract("/tmp/test.docx", "docx")
        assert result.text == "docx text"

    async def test_routes_to_xlsx(self):
        """extract('xlsx') appelle extract_xlsx."""
        mock_result = ExtractionResult(text="xlsx text", page_count=1, word_count=2)
        with patch(
            "apps.worker.app.extractors.xlsx.extract_xlsx",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await extract("/tmp/test.xlsx", "xlsx")
        assert result.text == "xlsx text"

    async def test_routes_csv_to_xlsx(self):
        """extract('csv') appelle extract_xlsx (même extracteur)."""
        mock_result = ExtractionResult(text="csv text", page_count=1, word_count=2)
        with patch(
            "apps.worker.app.extractors.xlsx.extract_xlsx",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await extract("/tmp/test.csv", "csv")
        assert result.text == "csv text"

    async def test_routes_to_pptx(self):
        """extract('pptx') appelle extract_pptx."""
        mock_result = ExtractionResult(text="pptx text", page_count=3, word_count=3)
        with patch(
            "apps.worker.app.extractors.pptx.extract_pptx",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await extract("/tmp/test.pptx", "pptx")
        assert result.page_count == 3

    async def test_routes_txt(self):
        """extract('txt') appelle extract_text."""
        mock_result = ExtractionResult(text="hello world", page_count=1, word_count=2)
        with patch(
            "apps.worker.app.extractors.text.extract_text",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await extract("/tmp/test.txt", "txt")
        assert result.word_count == 2

    async def test_routes_md(self):
        """extract('md') appelle extract_text (même extracteur que txt)."""
        mock_result = ExtractionResult(text="# Title", page_count=1, word_count=1)
        with patch(
            "apps.worker.app.extractors.text.extract_text",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await extract("/tmp/test.md", "md")
        assert result.text == "# Title"

    async def test_unsupported_type_raises(self):
        """Type non supporté → ValueError."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            await extract("/tmp/test.xyz", "xyz")


# ─── TXT / MD extractor ────────────────────────────────────────


@pytest.mark.asyncio
class TestExtractText:
    async def test_extract_utf8_file(self):
        """Fichier UTF-8 → texte extrait, word_count correct."""
        content = "Hello world this is a test"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            path = f.name

        result = await extract_text(path)

        assert result.text == content
        assert result.word_count == 6
        assert result.metadata["extractor"] == "direct_read"

    async def test_extract_latin1_fallback(self):
        """Fichier latin-1 → fallback encoding, texte extrait."""
        content = "Café et résumé"
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write(content.encode("latin-1"))
            path = f.name

        result = await extract_text(path)

        assert "Caf" in result.text  # Caractères présents (encodage OK)

    async def test_page_count_small_file(self):
        """Fichier < 500 mots → page_count = 1."""
        content = "Short file with few words"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            path = f.name

        result = await extract_text(path)
        assert result.page_count == 1

    async def test_page_count_large_file(self):
        """Fichier > 1000 mots → page_count >= 2."""
        content = " ".join(["word"] * 1100)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            path = f.name

        result = await extract_text(path)
        assert result.page_count >= 2

    async def test_empty_file(self):
        """Fichier vide → word_count=0, page_count=1."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            path = f.name

        result = await extract_text(path)
        assert result.word_count == 0
        assert result.page_count == 1


# ─── PDF extractor ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestExtractPdf:
    async def test_extract_multipage_pdf(self):
        """PDF 3 pages → ExtractionResult avec PAGE BREAK markers."""
        from apps.worker.app.extractors.pdf import extract_pdf

        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "Contenu page 1"
        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "Contenu page 2"
        mock_page3 = MagicMock()
        mock_page3.get_text.return_value = "  "  # page blanche

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(
            return_value=iter([mock_page1, mock_page2, mock_page3])
        )

        with patch("fitz.open", return_value=mock_doc):
            result = await extract_pdf("/tmp/test.pdf")

        assert result.page_count == 2  # page blanche exclue
        assert "PAGE BREAK" in result.text
        assert "Contenu page 1" in result.text
        assert result.metadata["extractor"] == "pymupdf"

    async def test_extract_pdf_word_count(self):
        """Word count calculé correctement sur le texte assemblé."""
        from apps.worker.app.extractors.pdf import extract_pdf

        mock_page = MagicMock()
        mock_page.get_text.return_value = "alpha beta gamma"
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

        with patch("fitz.open", return_value=mock_doc):
            result = await extract_pdf("/tmp/test.pdf")

        assert result.word_count == 3

    async def test_extract_pdf_close_called(self):
        """doc.close() est toujours appelé (finally block)."""
        from apps.worker.app.extractors.pdf import extract_pdf

        mock_page = MagicMock()
        mock_page.get_text.return_value = "text"
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

        with patch("fitz.open", return_value=mock_doc):
            await extract_pdf("/tmp/test.pdf")

        mock_doc.close.assert_called_once()

    async def test_extract_pdf_all_blank_pages(self):
        """PDF avec uniquement des pages blanches → texte vide, 0 pages."""
        from apps.worker.app.extractors.pdf import extract_pdf

        mock_page = MagicMock()
        mock_page.get_text.return_value = "   "
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

        with patch("fitz.open", return_value=mock_doc):
            result = await extract_pdf("/tmp/test.pdf")

        assert result.page_count == 0
        assert result.text == ""


# ─── DOCX extractor ────────────────────────────────────────────


@pytest.mark.asyncio
class TestExtractDocx:
    def _make_para(self, text: str, style_name: str = "Normal") -> MagicMock:
        para = MagicMock()
        para.text = text
        para.style = MagicMock()
        para.style.name = style_name
        return para

    def _make_table(self, rows: list[list[str]]) -> MagicMock:
        table = MagicMock()
        table.rows = []
        for row_cells in rows:
            row = MagicMock()
            row.cells = [MagicMock(text=c) for c in row_cells]
            table.rows.append(row)
        return table

    async def test_extract_paragraphs(self):
        """Paragraphes normaux → extraits sans préfixe."""
        from apps.worker.app.extractors.docx import extract_docx

        para = self._make_para("Bonjour le monde")

        # Élément XML mock
        elem = MagicMock()
        elem.tag = "ns}p"

        mock_doc = MagicMock()
        mock_doc.element.body.__iter__ = MagicMock(return_value=iter([elem]))
        mock_doc.paragraphs = [para]
        para._element = elem
        mock_doc.tables = []

        with patch("apps.worker.app.extractors.docx.Document", return_value=mock_doc):
            result = await extract_docx("/tmp/test.docx")

        assert "Bonjour le monde" in result.text
        assert result.metadata["extractor"] == "python-docx"

    async def test_extract_heading(self):
        """Paragraphe Heading 2 → préfixé avec ##."""
        from apps.worker.app.extractors.docx import extract_docx

        para = self._make_para("Mon titre", style_name="Heading 2")

        elem = MagicMock()
        elem.tag = "ns}p"

        mock_doc = MagicMock()
        mock_doc.element.body.__iter__ = MagicMock(return_value=iter([elem]))
        mock_doc.paragraphs = [para]
        para._element = elem
        mock_doc.tables = []

        with patch("apps.worker.app.extractors.docx.Document", return_value=mock_doc):
            result = await extract_docx("/tmp/test.docx")

        assert "## Mon titre" in result.text

    async def test_extract_table(self):
        """Table DOCX → formatée avec | et encadrée [TABLE][/TABLE]."""
        from apps.worker.app.extractors.docx import extract_docx

        table = self._make_table([["Nom", "Valeur"], ["Alpha", "1"]])
        table_elem = MagicMock()
        table_elem.tag = "ns}tbl"
        table._element = table_elem

        mock_doc = MagicMock()
        mock_doc.element.body.__iter__ = MagicMock(return_value=iter([table_elem]))
        mock_doc.paragraphs = []
        mock_doc.tables = [table]

        with patch("apps.worker.app.extractors.docx.Document", return_value=mock_doc):
            result = await extract_docx("/tmp/test.docx")

        assert "[TABLE]" in result.text
        assert "Nom | Valeur" in result.text


# ─── PPTX extractor ────────────────────────────────────────────


@pytest.mark.asyncio
class TestExtractPptx:
    def _make_slide(self, texts: list[str], has_table: bool = False) -> MagicMock:
        shapes = []
        for text in texts:
            shape = MagicMock()
            shape.has_text_frame = True
            shape.has_table = False

            para = MagicMock()
            para.text = text

            shape.text_frame = MagicMock()
            shape.text_frame.paragraphs = [para]
            shapes.append(shape)

        if has_table:
            table_shape = MagicMock()
            table_shape.has_text_frame = False
            table_shape.has_table = True
            row = MagicMock()
            row.cells = [MagicMock(text="A"), MagicMock(text="B")]
            table_shape.table = MagicMock()
            table_shape.table.rows = [row]
            shapes.append(table_shape)

        slide = MagicMock()
        slide.shapes = shapes
        return slide

    async def test_extract_slides_with_text(self):
        """Slides avec texte → extraites avec numéro de slide."""
        from apps.worker.app.extractors.pptx import extract_pptx

        slide1 = self._make_slide(["Titre principal", "Sous-titre"])
        slide2 = self._make_slide(["Slide 2 content"])

        mock_prs = MagicMock()
        mock_prs.slides = [slide1, slide2]

        with patch(
            "apps.worker.app.extractors.pptx.Presentation", return_value=mock_prs
        ):
            result = await extract_pptx("/tmp/test.pptx")

        assert result.page_count == 2
        assert "Slide 1" in result.text
        assert "Titre principal" in result.text
        assert result.metadata["extractor"] == "python-pptx"

    async def test_extract_skips_empty_slides(self):
        """Slide sans contenu → non incluse dans le résultat."""
        from apps.worker.app.extractors.pptx import extract_pptx

        empty_slide = self._make_slide([])  # pas de texte → non inclus

        mock_prs = MagicMock()
        mock_prs.slides = [empty_slide]

        with patch(
            "apps.worker.app.extractors.pptx.Presentation", return_value=mock_prs
        ):
            result = await extract_pptx("/tmp/test.pptx")

        assert result.page_count == 0
        assert result.text == ""

    async def test_extract_slide_with_table(self):
        """Slide avec table → cellules extraites avec | séparateur."""
        from apps.worker.app.extractors.pptx import extract_pptx

        slide = self._make_slide(["Titre"], has_table=True)

        mock_prs = MagicMock()
        mock_prs.slides = [slide]

        with patch(
            "apps.worker.app.extractors.pptx.Presentation", return_value=mock_prs
        ):
            result = await extract_pptx("/tmp/test.pptx")

        assert "A | B" in result.text

    async def test_slide_count_metadata(self):
        """slide_count dans metadata = nombre de slides avec contenu."""
        from apps.worker.app.extractors.pptx import extract_pptx

        slides = [self._make_slide([f"Contenu {i}"]) for i in range(4)]
        mock_prs = MagicMock()
        mock_prs.slides = slides

        with patch(
            "apps.worker.app.extractors.pptx.Presentation", return_value=mock_prs
        ):
            result = await extract_pptx("/tmp/test.pptx")

        assert result.metadata["slide_count"] == 4


# ─── XLSX / CSV extractor ──────────────────────────────────────


@pytest.mark.asyncio
class TestExtractXlsx:
    async def test_extract_csv(self):
        """CSV → extrait via pandas.read_csv, une feuille."""
        import pandas as pd

        from apps.worker.app.extractors.xlsx import extract_xlsx

        df = pd.DataFrame({"Name": ["Alice", "Bob"], "Age": [30, 25]})

        with patch("pandas.read_csv", return_value=df):
            result = await extract_xlsx("/tmp/data.csv", "csv")

        assert result.page_count == 1
        assert "Name" in result.text
        assert result.metadata["extractor"] == "pandas"

    async def test_extract_xlsx_multi_sheet(self):
        """XLSX 2 feuilles → 2 sections dans le texte."""
        import pandas as pd

        from apps.worker.app.extractors.xlsx import extract_xlsx

        df1 = pd.DataFrame({"Revenue": [100, 200]})
        df2 = pd.DataFrame({"Cost": [50, 80]})

        mock_xls = MagicMock()
        mock_xls.sheet_names = ["Sheet1", "Sheet2"]

        with (
            patch("pandas.ExcelFile", return_value=mock_xls),
            patch("pandas.read_excel", side_effect=[df1, df2]),
        ):
            result = await extract_xlsx("/tmp/data.xlsx", "xlsx")

        assert result.page_count == 2
        assert "Sheet1" in result.text
        assert "Sheet2" in result.text

    async def test_extract_xlsx_skips_empty_sheets(self):
        """Feuille vide (DataFrame vide) → ignorée."""
        import pandas as pd

        from apps.worker.app.extractors.xlsx import extract_xlsx

        df_filled = pd.DataFrame({"A": [1, 2]})
        df_empty = pd.DataFrame()

        mock_xls = MagicMock()
        mock_xls.sheet_names = ["Data", "Empty"]

        with (
            patch("pandas.ExcelFile", return_value=mock_xls),
            patch("pandas.read_excel", side_effect=[df_filled, df_empty]),
        ):
            result = await extract_xlsx("/tmp/data.xlsx", "xlsx")

        assert result.page_count == 1
        assert "Data" in result.text
        assert "Empty" not in result.text

    def test_dataframe_to_text_format(self):
        """_dataframe_to_text génère le header, séparateur et lignes."""
        import pandas as pd

        df = pd.DataFrame({"Col1": ["a", "b"], "Col2": [1, 2]})
        text = _dataframe_to_text(df, "TestSheet")

        assert "## Sheet: TestSheet" in text
        assert "Col1 | Col2" in text
        assert "--- | ---" in text
        assert "a | 1" in text
