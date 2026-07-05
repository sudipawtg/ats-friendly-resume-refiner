import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.services.latex_compile_service import LatexCompileError, LatexCompileService


@pytest.fixture
def compiler(tmp_path):
    return LatexCompileService(Settings(storage_dir=tmp_path))


class TestCollectSearchPaths:
    def test_includes_output_dir_and_main_tex_parent(self, compiler, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        main_tex = output_dir / "Resume" / "resume.tex"
        main_tex.parent.mkdir(parents=True)
        main_tex.touch()

        paths = compiler._collect_search_paths(output_dir, main_tex)
        assert output_dir.resolve() in paths
        assert main_tex.parent.resolve() in paths

    def test_deduplicates_paths(self, compiler, tmp_path):
        main_tex = tmp_path / "resume.tex"
        main_tex.touch()
        paths = compiler._collect_search_paths(tmp_path, main_tex)
        assert len(paths) == 1


class TestBuildTexinputs:
    def test_builds_path_prefix(self, compiler, tmp_path):
        paths = [tmp_path / "a", tmp_path / "b"]
        result = compiler._build_texinputs(paths)
        assert f"{paths[0]}//" in result
        assert f"{paths[1]}//" in result

    def test_appends_existing_texinputs(self, compiler, tmp_path, monkeypatch):
        monkeypatch.setenv("TEXINPUTS", "/existing//")
        result = compiler._build_texinputs([tmp_path])
        assert "/existing//" in result


class TestResolvePdfPath:
    def test_finds_pdf_in_output_dir(self, compiler, tmp_path):
        main_tex = tmp_path / "resume.tex"
        main_tex.touch()
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        found = compiler._resolve_pdf_path(tmp_path, main_tex)
        assert found == pdf

    def test_finds_pdf_next_to_main_tex(self, compiler, tmp_path):
        sub = tmp_path / "Resume"
        sub.mkdir()
        main_tex = sub / "resume.tex"
        main_tex.touch()
        pdf = sub / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        found = compiler._resolve_pdf_path(tmp_path, main_tex)
        assert found == pdf

    def test_returns_none_when_no_pdf(self, compiler, tmp_path):
        main_tex = tmp_path / "resume.tex"
        main_tex.touch()
        assert compiler._resolve_pdf_path(tmp_path, main_tex) is None


class TestFindCompiler:
    def test_prefers_tectonic(self, compiler, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/tectonic" if name == "tectonic" else None)
        assert compiler._find_compiler() == "tectonic"

    def test_falls_back_to_pdflatex(self, compiler, monkeypatch):
        def which(name):
            return "/usr/bin/pdflatex" if name == "pdflatex" else None

        monkeypatch.setattr(shutil, "which", which)
        assert compiler._find_compiler() == "pdflatex"

    def test_returns_none_when_no_compiler(self, compiler, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda _: None)
        assert compiler._find_compiler() is None


class TestCompileOutputToPdf:
    def test_raises_when_main_tex_missing(self, compiler, tmp_path):
        with pytest.raises(FileNotFoundError, match="Main TeX file not found"):
            compiler.compile_output_to_pdf(tmp_path, "missing.tex")

    def test_raises_when_no_compiler(self, compiler, tmp_path, monkeypatch):
        main_tex = tmp_path / "resume.tex"
        main_tex.write_text("\\documentclass{article}", encoding="utf-8")
        monkeypatch.setattr(compiler, "_find_compiler", lambda: None)

        with pytest.raises(LatexCompileError, match="No LaTeX compiler found"):
            compiler.compile_output_to_pdf(tmp_path, "resume.tex")

    @pytest.mark.skipif(not shutil.which("tectonic") and not shutil.which("pdflatex"), reason="No LaTeX compiler")
    def test_compiles_minimal_tex(self, compiler, tmp_path):
        main_tex = tmp_path / "resume.tex"
        main_tex.write_text(
            "\\documentclass{article}\\begin{document}Hello\\end{document}",
            encoding="utf-8",
        )
        pdf_path = compiler.compile_output_to_pdf(tmp_path, "resume.tex")
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 100
